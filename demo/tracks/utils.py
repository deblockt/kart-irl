"""
Utilitaires partagés pour l'analyse des tracks.

Ce module contient les fonctions communes utilisées par:
- ar_viewer.py
- convert_to_motor.py
- generate_map.py
"""

import os
import subprocess
import numpy as np
import pandas as pd
import cv2
from scipy.signal import butter, filtfilt


# =============================================================================
# Constantes
# =============================================================================

G = 9.81  # m/s²
SENSOR_FREQ = 100  # Hz approximatif

# Configuration ArUco
ARUCO_DICT = cv2.aruco.DICT_4X4_50
TAG_SIZE_CM = 10.0
TAG_SIZE_M = TAG_SIZE_CM / 100.0

# Configuration des portes (left_id, right_id)
GATES = {
    1: (10, 11),
    2: (20, 21),
    3: (30, 31),
    4: (40, 41),
}

# Mapping ID -> (numéro de porte, côté)
TAG_TO_GATE = {}
for gate_num, (left_id, right_id) in GATES.items():
    TAG_TO_GATE[left_id] = (gate_num, "L")
    TAG_TO_GATE[right_id] = (gate_num, "R")

# Distance entre les tags d'une porte (bord intérieur à bord intérieur)
GATE_INNER_DISTANCE_CM = 17.5
GATE_WIDTH_M = (GATE_INNER_DISTANCE_CM + 2 * TAG_SIZE_CM) / 100.0  # Distance centre à centre


# =============================================================================
# Chargement des données
# =============================================================================

def load_calibration(folder: str) -> tuple[float, int]:
    """Charge calib.csv et retourne (sensor_start_time, video_start_frame)."""
    calib_path = os.path.join(folder, "calib.csv")
    df = pd.read_csv(calib_path)
    sensor_start = df["sensor_second_start"].iloc[0]
    video_start_frame = int(df["video_frame_start"].iloc[0])
    return sensor_start, video_start_frame


def load_sensor_data(folder: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Charge accel.csv et gyro.csv."""
    accel_path = os.path.join(folder, "accel.csv")
    gyro_path = os.path.join(folder, "gyro.csv")
    accel_df = pd.read_csv(accel_path)
    gyro_df = pd.read_csv(gyro_path)
    return accel_df, gyro_df


def load_motor_data(folder: str) -> pd.DataFrame | None:
    """Charge motor.csv s'il existe."""
    motor_path = os.path.join(folder, "motor.csv")
    if os.path.exists(motor_path):
        return pd.read_csv(motor_path)
    return None


# =============================================================================
# Synchronisation
# =============================================================================

def sync_sensor_to_frame(
    frame_idx: int,
    fps: float,
    sensor_df: pd.DataFrame,
    sensor_start: float,
    video_start_frame: int,
) -> pd.Series | None:
    """Retourne la ligne sensor la plus proche correspondant à la frame vidéo."""
    video_time = (frame_idx - video_start_frame) / fps
    sensor_time = sensor_start + video_time

    if sensor_time < 0:
        return None

    idx = (sensor_df["seconds_elapsed"] - sensor_time).abs().idxmin()
    return sensor_df.loc[idx]


def sync_motor_to_frame(
    frame_idx: int,
    fps: float,
    motor_df: pd.DataFrame,
    video_start_frame: int,
) -> pd.Series | None:
    """Retourne la ligne motor la plus proche correspondant à la frame vidéo."""
    video_time = (frame_idx - video_start_frame) / fps

    if video_time < 0:
        return None

    idx = (motor_df["seconds_elapsed"] - video_time).abs().idxmin()
    return motor_df.loc[idx]


def frame_to_motor_time(frame_idx: int, fps: float, video_start_frame: int) -> float:
    """Convertit un numéro de frame en temps motor (seconds_elapsed dans motor.csv)."""
    return (frame_idx - video_start_frame) / fps


# =============================================================================
# Filtrage
# =============================================================================

def butter_lowpass_filter(data: np.ndarray, cutoff: float, fs: float, order: int = 4) -> np.ndarray:
    """Applique un filtre passe-bas Butterworth."""
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)


def butter_highpass_filter(data: np.ndarray, cutoff: float, fs: float, order: int = 4) -> np.ndarray:
    """Applique un filtre passe-haut Butterworth."""
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='high', analog=False)
    return filtfilt(b, a, data)


# =============================================================================
# Vidéo
# =============================================================================

def get_video_rotation(video_path: str) -> int:
    """Récupère la rotation de la vidéo via ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "stream_side_data=rotation",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True,
            text=True,
        )
        rotation_str = result.stdout.strip()
        if rotation_str:
            return int(float(rotation_str))
    except Exception:
        pass
    return 0


def rotate_frame(frame, rotation: int):
    """Applique la rotation à une frame selon les métadonnées vidéo."""
    if rotation == -90 or rotation == 270:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 90 or rotation == -270:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif rotation == 180 or rotation == -180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    return frame


def open_video(video_path: str) -> tuple[cv2.VideoCapture, float, int, int, int, int]:
    """
    Ouvre une vidéo et retourne ses métadonnées.

    Returns:
        (cap, fps, total_frames, width, height, rotation)
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"Impossible d'ouvrir la vidéo '{video_path}'")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    rotation = get_video_rotation(video_path)
    if rotation in (-90, 90, 270, -270):
        width, height = height, width

    return cap, fps, total_frames, width, height, rotation


# =============================================================================
# ArUco
# =============================================================================

def create_aruco_detector():
    """Crée un détecteur ArUco configuré pour les tags 4x4."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    aruco_params = cv2.aruco.DetectorParameters()
    return cv2.aruco.ArucoDetector(aruco_dict, aruco_params)


def detect_aruco_markers(frame, detector) -> tuple:
    """Détecte les markers ArUco dans une frame."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, rejected = detector.detectMarkers(gray)
    return corners, ids


def estimate_marker_distance(corner, frame_width: int, fov_horizontal_deg: float = 70.0) -> float:
    """
    Estime la distance d'un marker à partir de sa taille apparente dans l'image.

    Utilise la taille connue du tag (10cm) et la géométrie de la caméra.
    """
    # Taille du marker en pixels (moyenne des côtés)
    pts = corner[0]
    side1 = np.linalg.norm(pts[0] - pts[1])
    side2 = np.linalg.norm(pts[1] - pts[2])
    marker_size_pixels = (side1 + side2) / 2

    # Calcul de la distance via la géométrie
    # focal_length (en pixels) ≈ (frame_width / 2) / tan(fov/2)
    fov_rad = np.radians(fov_horizontal_deg)
    focal_length = (frame_width / 2) / np.tan(fov_rad / 2)

    # distance = (taille_réelle * focal_length) / taille_pixels
    distance = (TAG_SIZE_M * focal_length) / marker_size_pixels

    return distance


def estimate_marker_angle(corner, frame_width: int, fov_horizontal_deg: float = 70.0) -> float:
    """
    Estime l'angle horizontal du marker par rapport au centre de l'image.

    Returns:
        Angle en radians (positif = droite, négatif = gauche)
    """
    pts = corner[0]
    center_x = np.mean(pts[:, 0])

    # Normaliser entre -1 et 1
    normalized_x = (center_x - frame_width / 2) / (frame_width / 2)

    # Convertir en angle
    fov_rad = np.radians(fov_horizontal_deg)
    angle = normalized_x * (fov_rad / 2)

    return angle


# =============================================================================
# Trajectoire
# =============================================================================

def compute_trajectory_from_motor(motor_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calcule la trajectoire (x, y, yaw) à partir des données motor.csv.

    Intègre la vitesse et la direction pour obtenir la position.

    Returns:
        (x_positions, y_positions, yaw_angles) - arrays de même taille que motor_df
    """
    n = len(motor_df)
    x = np.zeros(n)
    y = np.zeros(n)
    yaw = np.zeros(n)

    dt = np.diff(motor_df["seconds_elapsed"].values, prepend=0)
    dt[0] = dt[1] if n > 1 else 0.01

    speeds = motor_df["speed_ms"].values
    # Direction en rad/s (approximation depuis l'angle)
    # direction_angle_deg donne l'angle de braquage, on le convertit en taux de rotation
    # En supposant que l'angle de braquage est proportionnel au taux de rotation
    direction_rad = np.radians(motor_df["direction_angle_deg"].values)

    for i in range(1, n):
        # Mettre à jour le yaw (direction)
        # Le taux de rotation dépend de la vitesse et de l'angle de braquage
        # Approximation simplifiée: yaw_rate ≈ (speed / wheelbase) * tan(steering_angle)
        # On utilise une approximation plus simple: yaw_rate proportionnel à direction
        yaw_rate = direction_rad[i] * 0.5  # Facteur empirique
        yaw[i] = yaw[i-1] + yaw_rate * dt[i]

        # Mettre à jour la position
        speed = speeds[i]
        x[i] = x[i-1] + speed * np.cos(yaw[i]) * dt[i]
        y[i] = y[i-1] + speed * np.sin(yaw[i]) * dt[i]

    return x, y, yaw


def compute_trajectory_from_gyro(gyro_df: pd.DataFrame, motor_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calcule la trajectoire en utilisant le gyroscope pour l'orientation.

    Plus précis que compute_trajectory_from_motor car utilise directement
    le taux de rotation mesuré.

    Returns:
        (x_positions, y_positions, yaw_angles)
    """
    # Interpoler gyro sur les timestamps de motor
    gyro_y = np.interp(
        motor_df["seconds_elapsed"].values,
        gyro_df["seconds_elapsed"].values - gyro_df["seconds_elapsed"].values[0],  # Normaliser à 0
        gyro_df["y"].values  # Y = yaw en position verticale
    )

    n = len(motor_df)
    x = np.zeros(n)
    y = np.zeros(n)
    yaw = np.zeros(n)

    dt = np.diff(motor_df["seconds_elapsed"].values, prepend=0)
    dt[0] = dt[1] if n > 1 else 0.01

    speeds = motor_df["speed_ms"].values

    for i in range(1, n):
        # Intégrer le gyroscope pour le yaw
        yaw[i] = yaw[i-1] + gyro_y[i] * dt[i]

        # Mettre à jour la position
        speed = speeds[i]
        x[i] = x[i-1] + speed * np.cos(yaw[i]) * dt[i]
        y[i] = y[i-1] + speed * np.sin(yaw[i]) * dt[i]

    return x, y, yaw
