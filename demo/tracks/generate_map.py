"""
Génère une carte 2D du circuit à partir de la vidéo et des données capteurs.

La carte affiche:
- Le chemin parcouru par le kart (trajectoire)
- La position des portes détectées

Usage:
    python generate_map.py <track_folder> [--output map.png]

Exemple:
    python generate_map.py track1
    python generate_map.py track1 --output track1_map.png
"""

import sys
import os
import argparse
import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.collections import LineCollection

from utils import (
    load_calibration,
    load_sensor_data,
    load_motor_data,
    open_video,
    rotate_frame,
    create_aruco_detector,
    detect_aruco_markers,
    estimate_marker_distance,
    estimate_marker_angle,
    compute_trajectory_from_gyro,
    frame_to_motor_time,
    TAG_TO_GATE,
    GATES,
    GATE_WIDTH_M,
)


def find_gates_in_video(
    video_path: str,
    motor_df,
    trajectory_x: np.ndarray,
    trajectory_y: np.ndarray,
    trajectory_yaw: np.ndarray,
    video_start_frame: int,
    fps: float,
    sample_every_n_frames: int = 5,
) -> dict:
    """
    Parcourt la vidéo pour détecter les portes et estimer leur position.

    Returns:
        Dict[gate_num] -> {'x': float, 'y': float, 'yaw': float, 'detections': int}
    """
    cap, fps_video, total_frames, width, height, rotation = open_video(video_path)
    detector = create_aruco_detector()

    gates_detected = {}  # gate_num -> list of (x, y, yaw)

    print(f"  Analyse de la vidéo ({total_frames} frames)...")

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1

        # Échantillonner pour accélérer
        if frame_idx % sample_every_n_frames != 0:
            continue

        frame = rotate_frame(frame, rotation)

        # Détecter les markers
        corners, ids = detect_aruco_markers(frame, detector)

        if ids is None or len(ids) == 0:
            continue

        # Calculer le temps et trouver la position correspondante
        motor_time = frame_to_motor_time(frame_idx, fps, video_start_frame)
        if motor_time < 0 or motor_time > motor_df["seconds_elapsed"].max():
            continue

        # Trouver l'index dans la trajectoire
        traj_idx = (motor_df["seconds_elapsed"] - motor_time).abs().idxmin()
        kart_x = trajectory_x[traj_idx]
        kart_y = trajectory_y[traj_idx]
        kart_yaw = trajectory_yaw[traj_idx]

        # Traiter chaque marker détecté
        for corner, marker_id in zip(corners, ids.flatten()):
            if marker_id not in TAG_TO_GATE:
                continue

            gate_num, side = TAG_TO_GATE[marker_id]

            # Estimer la distance et l'angle du marker
            distance = estimate_marker_distance(corner, width)
            angle = estimate_marker_angle(corner, width)

            # Position du marker dans le repère monde
            # Le marker est à (distance, angle) du kart
            marker_angle_world = kart_yaw + angle
            marker_x = kart_x + distance * np.cos(marker_angle_world)
            marker_y = kart_y + distance * np.sin(marker_angle_world)

            # Estimer l'orientation de la porte (perpendiculaire à la direction du kart)
            gate_yaw = kart_yaw + np.pi / 2  # La porte est perpendiculaire

            if gate_num not in gates_detected:
                gates_detected[gate_num] = []

            gates_detected[gate_num].append({
                'x': marker_x,
                'y': marker_y,
                'yaw': gate_yaw,
                'side': side,
                'distance': distance,
            })

        # Afficher la progression
        if frame_idx % 100 == 0:
            print(f"    Frame {frame_idx}/{total_frames}")

    cap.release()

    # Moyenner les détections pour chaque porte
    gates_final = {}
    for gate_num, detections in gates_detected.items():
        if len(detections) == 0:
            continue

        # Séparer les détections gauche et droite
        left_detections = [d for d in detections if d['side'] == 'L']
        right_detections = [d for d in detections if d['side'] == 'R']

        # Calculer le centre de la porte
        all_x = [d['x'] for d in detections]
        all_y = [d['y'] for d in detections]
        all_yaw = [d['yaw'] for d in detections]

        gates_final[gate_num] = {
            'x': np.median(all_x),
            'y': np.median(all_y),
            'yaw': np.median(all_yaw),
            'detections': len(detections),
            'left_count': len(left_detections),
            'right_count': len(right_detections),
        }

    return gates_final


def generate_map_image(
    trajectory_x: np.ndarray,
    trajectory_y: np.ndarray,
    gates: dict,
    output_path: str | None = None,
    show: bool = True,
):
    """
    Génère une image de la carte 2D.

    Args:
        trajectory_x, trajectory_y: Coordonnées de la trajectoire
        gates: Dict des portes détectées
        output_path: Chemin pour sauvegarder l'image (optionnel)
        show: Afficher la carte
    """
    fig, ax = plt.subplots(figsize=(12, 10))

    # Tracer la trajectoire avec un dégradé de couleur (temps)
    points = np.array([trajectory_x, trajectory_y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    # Créer un dégradé de couleur du bleu au rouge
    norm = plt.Normalize(0, len(trajectory_x))
    lc = LineCollection(segments, cmap='viridis', norm=norm, linewidth=2, alpha=0.8)
    lc.set_array(np.arange(len(trajectory_x)))
    ax.add_collection(lc)

    # Marquer le départ
    ax.plot(trajectory_x[0], trajectory_y[0], 'go', markersize=15, label='Départ', zorder=5)
    ax.annotate('START', (trajectory_x[0], trajectory_y[0]), fontsize=10, ha='center', va='bottom',
                xytext=(0, 10), textcoords='offset points')

    # Marquer l'arrivée
    ax.plot(trajectory_x[-1], trajectory_y[-1], 'ro', markersize=15, label='Arrivée', zorder=5)

    # Dessiner les portes
    gate_colors = {1: '#FF6B6B', 2: '#4ECDC4', 3: '#45B7D1', 4: '#96CEB4'}

    for gate_num, gate_info in sorted(gates.items()):
        x, y = gate_info['x'], gate_info['y']
        yaw = gate_info['yaw']

        color = gate_colors.get(gate_num, '#888888')

        # Dessiner la porte comme une ligne
        half_width = GATE_WIDTH_M / 2
        dx = half_width * np.cos(yaw)
        dy = half_width * np.sin(yaw)

        gate_x1, gate_y1 = x - dx, y - dy
        gate_x2, gate_y2 = x + dx, y + dy

        ax.plot([gate_x1, gate_x2], [gate_y1, gate_y2], color=color, linewidth=6, solid_capstyle='round')

        # Ajouter le numéro de porte
        ax.annotate(
            f'P{gate_num}',
            (x, y),
            fontsize=12,
            fontweight='bold',
            ha='center',
            va='center',
            color='white',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=color, edgecolor='none'),
        )

    # Configurer les axes
    ax.set_aspect('equal')
    ax.set_xlabel('X (mètres)', fontsize=12)
    ax.set_ylabel('Y (mètres)', fontsize=12)
    ax.set_title('Carte du Circuit', fontsize=16, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right')

    # Ajouter une barre de couleur pour le temps
    cbar = plt.colorbar(lc, ax=ax, label='Progression temporelle')

    # Ajuster les limites avec marge
    margin = 0.5
    ax.set_xlim(trajectory_x.min() - margin, trajectory_x.max() + margin)
    ax.set_ylim(trajectory_y.min() - margin, trajectory_y.max() + margin)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  Carte sauvegardée: {output_path}")

    if show:
        plt.show()

    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Génère une carte 2D du circuit')
    parser.add_argument('folder', help='Dossier du track (ex: track1)')
    parser.add_argument('--output', '-o', help='Fichier de sortie (ex: map.png)')
    parser.add_argument('--no-show', action='store_true', help="Ne pas afficher la carte")
    args = parser.parse_args()

    folder = args.folder

    if not os.path.isdir(folder):
        print(f"Erreur: le dossier '{folder}' n'existe pas")
        sys.exit(1)

    video_path = os.path.join(folder, "movie.MOV")
    if not os.path.exists(video_path):
        print(f"Erreur: la vidéo '{video_path}' n'existe pas")
        sys.exit(1)

    print(f"Génération de la carte pour '{folder}'...")

    # Charger les données
    print("Chargement des données...")
    sensor_start, video_start_frame = load_calibration(folder)
    accel_df, gyro_df = load_sensor_data(folder)
    motor_df = load_motor_data(folder)

    if motor_df is None:
        print("Erreur: motor.csv n'existe pas. Exécutez d'abord convert_to_motor.py")
        sys.exit(1)

    print(f"  - Motor: {len(motor_df)} points")
    print(f"  - Gyro: {len(gyro_df)} points")

    # Calculer la trajectoire
    print("Calcul de la trajectoire...")

    # Normaliser les timestamps du gyro pour commencer à 0 comme motor.csv
    gyro_df_normalized = gyro_df.copy()
    gyro_df_normalized["seconds_elapsed"] = gyro_df["seconds_elapsed"] - sensor_start

    trajectory_x, trajectory_y, trajectory_yaw = compute_trajectory_from_gyro(
        gyro_df_normalized, motor_df
    )

    print(f"  - Distance totale: {np.sum(np.sqrt(np.diff(trajectory_x)**2 + np.diff(trajectory_y)**2)):.2f} m")
    print(f"  - Étendue X: {trajectory_x.min():.2f} à {trajectory_x.max():.2f} m")
    print(f"  - Étendue Y: {trajectory_y.min():.2f} à {trajectory_y.max():.2f} m")

    # Détecter les portes dans la vidéo
    print("Détection des portes...")
    cap, fps, total_frames, width, height, rotation = open_video(video_path)
    cap.release()

    gates = find_gates_in_video(
        video_path,
        motor_df,
        trajectory_x,
        trajectory_y,
        trajectory_yaw,
        video_start_frame,
        fps,
        sample_every_n_frames=3,
    )

    print(f"  - Portes détectées: {len(gates)}")
    for gate_num, info in sorted(gates.items()):
        print(f"    Porte {gate_num}: ({info['x']:.2f}, {info['y']:.2f}) - {info['detections']} détections")

    # Générer la carte
    print("Génération de la carte...")
    output_path = args.output or os.path.join(folder, "map.png")

    generate_map_image(
        trajectory_x,
        trajectory_y,
        gates,
        output_path=output_path,
        show=not args.no_show,
    )

    print("Terminé!")


if __name__ == "__main__":
    main()
