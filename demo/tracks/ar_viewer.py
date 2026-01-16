"""
AR Viewer - Affiche une vidéo de track avec overlay ArUco et données IMU synchronisées.

Usage:
    python ar_viewer.py <track_folder>

Exemple:
    python ar_viewer.py track1
"""

import sys
import os
import subprocess
import numpy as np
import pandas as pd
import cv2


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


# Configuration ArUco
ARUCO_DICT = cv2.aruco.DICT_4X4_50
TAG_SIZE_CM = 10.0

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


def detect_aruco_markers(frame, detector) -> tuple:
    """Détecte les markers ArUco dans une frame."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, rejected = detector.detectMarkers(gray)
    return corners, ids


def draw_aruco_overlay(frame, corners, ids) -> np.ndarray:
    """Dessine les markers détectés avec ID, cadre et info de porte."""
    if ids is None or len(ids) == 0:
        return frame

    frame = frame.copy()
    detected_gates = {}

    for i, (corner, marker_id) in enumerate(zip(corners, ids.flatten())):
        pts = corner[0].astype(int)
        cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
        center = pts.mean(axis=0).astype(int)

        cv2.putText(
            frame, f"ID:{marker_id}",
            (center[0] - 20, center[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2,
        )

        if marker_id in TAG_TO_GATE:
            gate_num, side = TAG_TO_GATE[marker_id]
            if gate_num not in detected_gates:
                detected_gates[gate_num] = {}
            detected_gates[gate_num][side] = center

            cv2.putText(
                frame, f"P{gate_num}-{side}",
                (center[0] - 20, center[1] + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2,
            )

    for gate_num, sides in detected_gates.items():
        if "L" in sides and "R" in sides:
            left_center = sides["L"]
            right_center = sides["R"]
            cv2.line(frame, tuple(left_center), tuple(right_center), (0, 255, 255), 3)
            mid = ((left_center + right_center) / 2).astype(int)
            cv2.putText(
                frame, f"PORTE {gate_num}",
                (mid[0] - 40, mid[1] - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2,
            )
        elif len(sides) == 1:
            side = list(sides.keys())[0]
            center = sides[side]
            side_text = "Gauche" if side == "L" else "Droite"
            cv2.putText(
                frame, f"Porte {gate_num} ({side_text})",
                (center[0] - 50, center[1] + 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 2,
            )

    return frame


def draw_motor_overlay(frame, motor_data: pd.Series | None) -> np.ndarray:
    """Affiche les données moteur sur la frame (coin supérieur droit)."""
    frame = frame.copy()
    w = frame.shape[1]

    box_width = 220
    box_x = w - box_width - 10

    overlay = frame.copy()
    cv2.rectangle(overlay, (box_x, 10), (w - 10, 180), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    title_color = (255, 255, 255)
    value_color = (0, 255, 150)
    bar_bg_color = (60, 60, 60)
    bar_speed_color = (0, 200, 100)
    bar_left_color = (255, 100, 100)
    bar_right_color = (100, 100, 255)

    y = 35
    line_height = 22

    cv2.putText(frame, "MOTOR DATA", (box_x + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, title_color, 2)
    y += line_height + 5

    if motor_data is None:
        cv2.putText(frame, "No data", (box_x + 20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
        return frame

    speed_ms = motor_data["speed_ms"]
    speed_pct = motor_data["speed_percent"]
    cv2.putText(frame, f"Speed: {speed_ms:.2f} m/s ({speed_pct:.0f}%)", (box_x + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, value_color, 1)
    y += line_height

    bar_x = box_x + 10
    bar_w = box_width - 30
    bar_h = 12
    cv2.rectangle(frame, (bar_x, y), (bar_x + bar_w, y + bar_h), bar_bg_color, -1)
    fill_w = int(bar_w * speed_pct / 100)
    cv2.rectangle(frame, (bar_x, y), (bar_x + fill_w, y + bar_h), bar_speed_color, -1)
    cv2.rectangle(frame, (bar_x, y), (bar_x + bar_w, y + bar_h), (100, 100, 100), 1)
    y += bar_h + 10

    dir_pct = motor_data["direction_percent"]
    dir_enum = motor_data["direction_enum"]
    dir_angle = motor_data["direction_angle_deg"]
    cv2.putText(frame, f"Dir: {dir_enum} ({dir_pct:+.0f}%)", (box_x + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, value_color, 1)
    y += line_height
    cv2.putText(frame, f"Angle: {dir_angle:+.1f} deg", (box_x + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, value_color, 1)
    y += line_height

    bar_center = bar_x + bar_w // 2
    cv2.rectangle(frame, (bar_x, y), (bar_x + bar_w, y + bar_h), bar_bg_color, -1)
    cv2.line(frame, (bar_center, y), (bar_center, y + bar_h), (150, 150, 150), 1)
    fill_offset = int((bar_w // 2) * dir_pct / 100)
    if fill_offset > 0:
        cv2.rectangle(frame, (bar_center, y), (bar_center + fill_offset, y + bar_h), bar_right_color, -1)
    elif fill_offset < 0:
        cv2.rectangle(frame, (bar_center + fill_offset, y), (bar_center, y + bar_h), bar_left_color, -1)
    cv2.rectangle(frame, (bar_x, y), (bar_x + bar_w, y + bar_h), (100, 100, 100), 1)

    return frame


def draw_imu_overlay(
    frame,
    velocity: tuple[float, float, float],
    orientation: tuple[float, float, float],
    accel: tuple[float, float, float] | None,
    gyro: tuple[float, float, float] | None,
) -> np.ndarray:
    """Affiche les données IMU sur la frame."""
    frame = frame.copy()

    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (280, 280), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    title_color = (255, 255, 255)
    value_color = (0, 255, 255)
    raw_color = (180, 180, 180)

    y = 35
    line_height = 22

    cv2.putText(frame, "VITESSE (IMU)", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, title_color, 2)
    y += line_height
    cv2.putText(frame, f"Vx: {velocity[0]:+.2f} m/s", (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, value_color, 1)
    y += line_height
    cv2.putText(frame, f"Vy: {velocity[1]:+.2f} m/s", (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, value_color, 1)
    y += line_height
    cv2.putText(frame, f"Vz: {velocity[2]:+.2f} m/s", (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, value_color, 1)
    y += line_height + 5

    cv2.putText(frame, "ORIENTATION", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, title_color, 2)
    y += line_height
    cv2.putText(frame, f"Roll:  {np.degrees(orientation[0]):+.1f} deg", (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, value_color, 1)
    y += line_height
    cv2.putText(frame, f"Pitch: {np.degrees(orientation[1]):+.1f} deg", (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, value_color, 1)
    y += line_height
    cv2.putText(frame, f"Yaw:   {np.degrees(orientation[2]):+.1f} deg", (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, value_color, 1)
    y += line_height + 5

    if accel is not None:
        cv2.putText(frame, "ACCEL (raw)", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, raw_color, 1)
        y += line_height
        cv2.putText(frame, f"X:{accel[0]:+.2f}g Y:{accel[1]:+.2f}g Z:{accel[2]:+.2f}g", (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, raw_color, 1)
        y += line_height

    if gyro is not None:
        cv2.putText(frame, "GYRO (raw)", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, raw_color, 1)
        y += line_height
        cv2.putText(frame, f"X:{gyro[0]:+.2f} Y:{gyro[1]:+.2f} Z:{gyro[2]:+.2f} rad/s", (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, raw_color, 1)

    return frame


def draw_controls_help(frame) -> np.ndarray:
    """Affiche l'aide des contrôles en bas de l'écran."""
    frame = frame.copy()
    h = frame.shape[0]
    help_text = "ESPACE:Pause | Q:Quitter | R:Reset | Fleches:-/+1 frame | </>:-/+1s"
    cv2.putText(frame, help_text, (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    return frame


def main() -> None:
    """Boucle principale: lecture vidéo + overlay + display."""
    if len(sys.argv) < 2:
        print("Usage: python ar_viewer.py <track_folder>")
        print("Exemple: python ar_viewer.py track1")
        sys.exit(1)

    folder = sys.argv[1]

    if not os.path.isdir(folder):
        print(f"Erreur: le dossier '{folder}' n'existe pas")
        sys.exit(1)

    video_path = os.path.join(folder, "movie.MOV")
    if not os.path.exists(video_path):
        print(f"Erreur: la vidéo '{video_path}' n'existe pas")
        sys.exit(1)

    print("Chargement des données...")
    sensor_start, video_start_frame = load_calibration(folder)
    accel_df, gyro_df = load_sensor_data(folder)
    motor_df = load_motor_data(folder)
    print(f"  - Calibration: sensor_start={sensor_start:.4f}s, video_start_frame={video_start_frame}")
    print(f"  - Accel: {len(accel_df)} lignes")
    print(f"  - Gyro: {len(gyro_df)} lignes")
    if motor_df is not None:
        print(f"  - Motor: {len(motor_df)} lignes")
    else:
        print("  - Motor: non disponible (run convert_to_motor.py pour générer)")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Erreur: impossible d'ouvrir la vidéo '{video_path}'")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    rotation = get_video_rotation(video_path)
    if rotation in (-90, 90, 270, -270):
        width, height = height, width
    print(f"  - Vidéo: {width}x{height}, {fps:.2f} fps, {total_frames} frames, rotation={rotation}°")

    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    aruco_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

    velocity = np.array([0.0, 0.0, 0.0])
    orientation = np.array([0.0, 0.0, 0.0])
    last_sensor_time = None
    g = 9.81

    paused = False
    frame_idx = 0

    print("\nDémarrage de la lecture...")
    print("Contrôles: ESPACE=Pause, Q=Quitter, R=Reset, Fleches=-/+1 frame, </>=-/+1s")

    cv2.namedWindow("AR Viewer", cv2.WINDOW_NORMAL)

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("Fin de la vidéo")
                break
            frame = rotate_frame(frame, rotation)
            frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

        accel_row = sync_sensor_to_frame(frame_idx, fps, accel_df, sensor_start, video_start_frame)
        gyro_row = sync_sensor_to_frame(frame_idx, fps, gyro_df, sensor_start, video_start_frame)

        motor_row = None
        if motor_df is not None:
            motor_row = sync_motor_to_frame(frame_idx, fps, motor_df, video_start_frame)

        accel = None
        gyro = None

        if accel_row is not None:
            accel = (accel_row["x"], accel_row["y"], accel_row["z"])

        if gyro_row is not None:
            gyro = (gyro_row["x"], gyro_row["y"], gyro_row["z"])

        # Intégration IMU
        # Téléphone VERTICAL: Accel Z=avant, Y=gravité, X=latéral
        # Gyro: Y=yaw, X=pitch, Z=roll
        if accel_row is not None and gyro_row is not None:
            current_time = gyro_row["seconds_elapsed"]
            if last_sensor_time is not None:
                dt = current_time - last_sensor_time
                if dt > 0 and dt < 0.1:
                    accel_corrected = np.array([
                        accel_row["x"] * g,
                        (accel_row["y"] + 1) * g,
                        accel_row["z"] * g,
                    ])
                    velocity += accel_corrected * dt
                    velocity *= 0.98

                    orientation[0] += gyro_row["z"] * dt  # roll
                    orientation[1] += gyro_row["x"] * dt  # pitch
                    orientation[2] += gyro_row["y"] * dt  # yaw

            last_sensor_time = current_time

        corners, ids = detect_aruco_markers(frame, detector)

        frame = draw_aruco_overlay(frame, corners, ids)
        frame = draw_imu_overlay(frame, tuple(velocity), tuple(orientation), accel, gyro)
        frame = draw_motor_overlay(frame, motor_row)
        frame = draw_controls_help(frame)

        cv2.putText(frame, f"Frame: {frame_idx}/{total_frames}", (width - 180, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        if paused:
            cv2.putText(frame, "PAUSE", (width // 2 - 50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

        cv2.imshow("AR Viewer", frame)

        key = cv2.waitKey(1 if not paused else 50) & 0xFF

        if key == ord("q") or key == 27:
            break
        elif key == ord(" "):
            paused = not paused
        elif key == ord("r"):
            velocity = np.array([0.0, 0.0, 0.0])
            orientation = np.array([0.0, 0.0, 0.0])
            last_sensor_time = None
            print("Reset de la vitesse et de l'orientation")
        elif key == ord(","):
            new_frame = max(0, frame_idx - int(fps))
            cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
            ret, frame = cap.read()
            if ret:
                frame = rotate_frame(frame, rotation)
            frame_idx = new_frame
        elif key == ord("."):
            new_frame = min(total_frames - 1, frame_idx + int(fps))
            cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
            ret, frame = cap.read()
            if ret:
                frame = rotate_frame(frame, rotation)
            frame_idx = new_frame
        elif key == 81 or key == 2:  # Flèche gauche
            new_frame = max(0, frame_idx - 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
            ret, frame = cap.read()
            if ret:
                frame = rotate_frame(frame, rotation)
            frame_idx = new_frame
        elif key == 83 or key == 3:  # Flèche droite
            new_frame = min(total_frames - 1, frame_idx + 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
            ret, frame = cap.read()
            if ret:
                frame = rotate_frame(frame, rotation)
            frame_idx = new_frame

    cap.release()
    cv2.destroyAllWindows()
    print("Terminé.")


if __name__ == "__main__":
    main()
