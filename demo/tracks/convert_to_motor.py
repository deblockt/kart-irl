"""
Convertit les données IMU (accel.csv, gyro.csv) en données moteur simulées.

Ce script simule les données qu'un ESP32 fournirait (vitesse moteur + direction)
à partir des données d'accéléromètre et gyroscope enregistrées.

Usage:
    python convert_to_motor.py <track_folder>

Exemple:
    python convert_to_motor.py track1

Sortie:
    motor.csv avec les colonnes:
    - seconds_elapsed: temps en secondes
    - speed_ms: vitesse estimée en m/s
    - speed_percent: vitesse normalisée (0-100%)
    - direction_percent: direction signée (-100=gauche, 0=droit, +100=droite)
    - direction_enum: LEFT, RIGHT ou STRAIGHT
    - direction_angle_deg: angle de braquage estimé en degrés
"""

import sys
import os
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt


# Constantes physiques
G = 9.81  # m/s²
SENSOR_FREQ = 100  # Hz approximatif

# Seuils pour la direction
STRAIGHT_THRESHOLD_DEG = 5.0  # En dessous de ce seuil, on considère "tout droit"
MAX_TURN_RATE = 2.0  # rad/s - taux de rotation max attendu pour normaliser à 100%

# Vitesse max attendue pour normaliser à 100%
MAX_SPEED_MS = 5.0  # m/s (environ 18 km/h, raisonnable pour un kart)


def butter_lowpass_filter(data: np.ndarray, cutoff: float, fs: float, order: int = 4) -> np.ndarray:
    """Applique un filtre passe-bas Butterworth."""
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)


def butter_highpass_filter(data: np.ndarray, cutoff: float, fs: float, order: int = 4) -> np.ndarray:
    """Applique un filtre passe-haut Butterworth pour retirer la dérive."""
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='high', analog=False)
    return filtfilt(b, a, data)


def load_sensor_data(folder: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Charge accel.csv et gyro.csv."""
    accel_path = os.path.join(folder, "accel.csv")
    gyro_path = os.path.join(folder, "gyro.csv")
    accel_df = pd.read_csv(accel_path)
    gyro_df = pd.read_csv(gyro_path)
    return accel_df, gyro_df


def load_calibration(folder: str) -> tuple[float, int]:
    """Charge calib.csv."""
    calib_path = os.path.join(folder, "calib.csv")
    df = pd.read_csv(calib_path)
    sensor_start = df["sensor_second_start"].iloc[0]
    video_start_frame = int(df["video_frame_start"].iloc[0])
    return sensor_start, video_start_frame


def detect_stationary(accel_df: pd.DataFrame, gyro_df: pd.DataFrame, window: int = 50) -> np.ndarray:
    """
    Détecte les moments où le véhicule est à l'arrêt (ZUPT - Zero Velocity Update).

    On considère qu'on est à l'arrêt si:
    - La variance de l'accélération est faible (pas de mouvement)
    - La variance du gyroscope est faible (pas de rotation)
    """
    # Interpoler gyro sur les timestamps de accel
    gyro_y_interp = np.interp(
        accel_df["seconds_elapsed"].values,
        gyro_df["seconds_elapsed"].values,
        gyro_df["y"].values
    )

    accel_mag = np.sqrt(accel_df["x"]**2 + accel_df["y"]**2 + accel_df["z"]**2).values

    is_stationary = np.zeros(len(accel_df), dtype=bool)

    for i in range(window, len(accel_df)):
        # Variance sur une fenêtre glissante
        accel_var = np.var(accel_mag[i-window:i])
        gyro_var = np.var(gyro_y_interp[i-window:i])

        # Seuils empiriques pour détecter l'arrêt
        # Faible variance = pas de mouvement
        if accel_var < 0.002 and gyro_var < 0.01:
            is_stationary[i] = True

    return is_stationary


def compute_speed_from_accel(accel_df: pd.DataFrame, gyro_df: pd.DataFrame) -> np.ndarray:
    """
    Calcule la vitesse à partir de l'accélération avec correction gyroscopique.

    Avec le téléphone en position VERTICALE (portrait), face vers l'avant:
    - L'axe Z pointe vers l'avant (perpendiculaire à l'écran)
    - L'axe Y pointe vers le haut (contient la gravité ~1g)
    - L'axe X pointe vers la droite

    Améliorations:
    - Correction d'orientation via intégration du gyroscope
    - ZUPT (Zero Velocity Update) pour corriger la dérive aux arrêts
    """
    # Calculer dt pour chaque échantillon
    time_elapsed = accel_df["seconds_elapsed"].values
    dt = np.diff(time_elapsed, prepend=time_elapsed[0])
    dt[0] = dt[1] if len(dt) > 1 else 0.01

    # Interpoler gyro sur les timestamps de accel
    gyro_x = np.interp(time_elapsed, gyro_df["seconds_elapsed"].values, gyro_df["x"].values)
    gyro_y = np.interp(time_elapsed, gyro_df["seconds_elapsed"].values, gyro_df["y"].values)
    gyro_z = np.interp(time_elapsed, gyro_df["seconds_elapsed"].values, gyro_df["z"].values)

    # Accélération brute
    accel_x = accel_df["x"].values * G
    accel_y = accel_df["y"].values * G
    accel_z = accel_df["z"].values * G

    # Intégrer le gyroscope pour obtenir l'orientation (angles d'Euler simplifiés)
    # En position verticale: X=pitch, Y=yaw, Z=roll
    pitch = np.cumsum(gyro_x * dt)  # rotation avant/arrière

    # Corriger l'accélération Z en tenant compte du pitch
    # Si le téléphone penche vers l'avant, une partie de la gravité apparaît sur Z
    # accel_z_corrected = accel_z * cos(pitch) - accel_y * sin(pitch)
    accel_z_corrected = accel_z * np.cos(pitch) + accel_y * np.sin(pitch)

    # Filtrer le bruit
    accel_z_filtered = butter_lowpass_filter(accel_z_corrected, cutoff=3.0, fs=SENSOR_FREQ)

    # Retirer le biais (moyenne au repos)
    rest_samples = min(100, len(accel_z_filtered) // 10)
    bias = np.mean(accel_z_filtered[:rest_samples])
    accel_z_final = accel_z_filtered - bias

    # Détecter les moments d'arrêt (ZUPT)
    is_stationary = detect_stationary(accel_df, gyro_df)

    # Intégrer avec ZUPT
    velocity = np.zeros(len(accel_df))
    for i in range(1, len(accel_df)):
        if is_stationary[i]:
            # À l'arrêt: remettre la vitesse à zéro
            velocity[i] = 0
        else:
            # En mouvement: intégrer l'accélération
            velocity[i] = velocity[i-1] + accel_z_final[i] * dt[i]
            # Petit amortissement pour stabiliser
            velocity[i] *= 0.995

    # Filtrer le résultat pour lisser
    velocity_filtered = butter_lowpass_filter(velocity, cutoff=2.0, fs=SENSOR_FREQ)

    return velocity_filtered


def compute_direction_from_gyro(gyro_df: pd.DataFrame) -> np.ndarray:
    """
    Calcule la direction à partir du gyroscope.

    Avec le téléphone en position VERTICALE (portrait):
    - L'axe Y du gyroscope donne le taux de rotation (yaw rate) gauche/droite
    - Positif = tourne à droite, Négatif = tourne à gauche
    """
    # Taux de rotation sur l'axe Y (yaw en position verticale) en rad/s
    gyro_y = gyro_df["y"].values

    # Filtrer pour réduire le bruit
    gyro_y_filtered = butter_lowpass_filter(gyro_y, cutoff=5.0, fs=SENSOR_FREQ)

    return gyro_y_filtered


def direction_to_enum(direction_percent: float) -> str:
    """Convertit un pourcentage de direction en enum."""
    if abs(direction_percent) < (STRAIGHT_THRESHOLD_DEG / 45.0 * 100):
        return "STRAIGHT"
    elif direction_percent > 0:
        return "RIGHT"
    else:
        return "LEFT"


def main() -> None:
    """Point d'entrée principal."""
    if len(sys.argv) < 2:
        print("Usage: python convert_to_motor.py <track_folder>")
        print("Exemple: python convert_to_motor.py track1")
        sys.exit(1)

    folder = sys.argv[1]

    if not os.path.isdir(folder):
        print(f"Erreur: le dossier '{folder}' n'existe pas")
        sys.exit(1)

    print(f"Conversion des données IMU en données moteur pour '{folder}'...")

    # Charger les données
    accel_df, gyro_df = load_sensor_data(folder)
    sensor_start, _ = load_calibration(folder)
    print(f"  - Accel: {len(accel_df)} échantillons")
    print(f"  - Gyro: {len(gyro_df)} échantillons")
    print(f"  - Sync point: {sensor_start:.4f}s")

    # Fusionner les données sur le temps (interpolation au plus proche)
    # On utilise le temps du gyroscope comme référence
    merged_df = pd.DataFrame()
    merged_df["seconds_elapsed"] = gyro_df["seconds_elapsed"].values

    # Interpoler l'accélération sur les timestamps du gyro
    merged_df["accel_x"] = np.interp(
        gyro_df["seconds_elapsed"].values,
        accel_df["seconds_elapsed"].values,
        accel_df["x"].values
    )
    merged_df["accel_y"] = np.interp(
        gyro_df["seconds_elapsed"].values,
        accel_df["seconds_elapsed"].values,
        accel_df["y"].values
    )
    merged_df["accel_z"] = np.interp(
        gyro_df["seconds_elapsed"].values,
        accel_df["seconds_elapsed"].values,
        accel_df["z"].values
    )
    merged_df["gyro_z"] = gyro_df["z"].values

    # Calculer la vitesse
    print("  - Calcul de la vitesse...")
    speed_ms = compute_speed_from_accel(accel_df, gyro_df)
    # Interpoler sur les timestamps du gyro
    speed_ms_interp = np.interp(
        merged_df["seconds_elapsed"].values,
        accel_df["seconds_elapsed"].values,
        speed_ms
    )

    # Calculer la direction
    print("  - Calcul de la direction...")
    direction_rad_s = compute_direction_from_gyro(gyro_df)

    # Construire le DataFrame de sortie
    output_df = pd.DataFrame()
    output_df["seconds_elapsed"] = merged_df["seconds_elapsed"]

    # Vitesse
    output_df["speed_ms"] = np.abs(speed_ms_interp)  # Valeur absolue pour la vitesse
    max_observed_speed = max(output_df["speed_ms"].max(), 0.1)  # Éviter division par 0
    output_df["speed_percent"] = np.clip(
        output_df["speed_ms"] / MAX_SPEED_MS * 100, 0, 100
    ).round(1)

    # Direction
    # Convertir rad/s en pourcentage (-100 à +100)
    direction_percent = np.clip(
        direction_rad_s / MAX_TURN_RATE * 100, -100, 100
    )
    output_df["direction_percent"] = direction_percent.round(1)

    # Enum de direction
    output_df["direction_enum"] = [direction_to_enum(d) for d in direction_percent]

    # Angle en degrés (approximation: taux de rotation → angle de braquage)
    # On suppose que le taux de rotation max correspond à un angle de braquage de ~45°
    direction_angle = direction_rad_s / MAX_TURN_RATE * 45.0
    output_df["direction_angle_deg"] = np.clip(direction_angle, -45, 45).round(1)

    # Ajuster le temps pour commencer au point de synchronisation
    output_df["seconds_elapsed"] = (output_df["seconds_elapsed"] - sensor_start).round(6)

    # Filtrer pour ne garder que les données à partir du point de sync (t >= 0)
    output_df = output_df[output_df["seconds_elapsed"] >= 0].reset_index(drop=True)

    # Sauvegarder
    output_path = os.path.join(folder, "motor.csv")
    output_df.to_csv(output_path, index=False)
    print(f"\nFichier généré: {output_path}")
    print(f"  - {len(output_df)} lignes")
    print(f"  - Vitesse max observée: {max_observed_speed:.2f} m/s")
    print(f"  - Colonnes: {', '.join(output_df.columns)}")

    # Afficher un aperçu
    print("\nAperçu des données:")
    print(output_df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
