import sys
import pandas as pd
import numpy as np
from scipy.signal import find_peaks, butter, filtfilt
import cv2
import os

def build_sensor_start_time(file: str):
    df = pd.read_csv(file)

    # ---------- 2️⃣ Calculer la magnitude ----------
    df['gyro_mag'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)

    # ---------- 3️⃣ Filtrer pour lisser le signal ----------
    def butter_lowpass(cutoff, fs, order=4):
        from scipy.signal import butter
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return b, a

    fs = 100  # fréquence approx en Hz
    cutoff = 5  # Hz
    b, a = butter_lowpass(cutoff, fs)
    df['gyro_filt'] = filtfilt(b, a, df['gyro_mag'])

    # ---------- 4️⃣ Dérivée pour détecter les mouvements brusques ----------
    df['gyro_diff'] = np.abs(np.diff(df['gyro_filt'], prepend=df['gyro_filt'][0]))

    # ---------- 5️⃣ Détecter tous les pics ----------
    peaks, properties = find_peaks(df['gyro_diff'], height=0.1, distance=20)  # height > 0.1

    if len(peaks) == 0:
        raise Exception("Aucun pic significatif détecté")
    else:
        first_peak_idx = peaks[0]
        start_time = df['seconds_elapsed'].iloc[first_peak_idx]
        return start_time

def build_video_start_frame(file: str):
    gyro_peak_time = 0.14529      # temps du pic détecté dans le gyro (en secondes)
    fps = None                    # on récupérera automatiquement

    # --- INITIALISATION ---
    cap = cv2.VideoCapture(file)
    if not cap.isOpened():
        raise Exception("Impossible d'ouvrir la vidéo")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    prev_frame_gray = None
    motion_values = []

    # --- ANALYSE FRAME PAR FRAME ---
    for i in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if prev_frame_gray is not None:
            # delta absolu moyen entre frames consécutives
            diff = cv2.absdiff(gray, prev_frame_gray)
            motion = np.mean(diff)
            motion_values.append((i, motion))
        prev_frame_gray = gray

    cap.release()

    # --- DETECTION DU PIC DE MOUVEMENT ---
    motion_array = np.array([m[1] for m in motion_values])
    frame_array = np.array([m[0] for m in motion_values])

    # seuil de détection du tap (à ajuster si nécessaire)
    motion_threshold = 10  # valeur moyenne des pixels qui correspond au tap

    # détecte toutes les frames où le mouvement dépasse le seuil
    motion_peaks = frame_array[motion_array > motion_threshold]
    motion_values_over = motion_array[motion_array > motion_threshold]

    # On prend la première frame après le temps du pic gyro
    frame_start = None
    for f, m in zip(motion_peaks, motion_values_over):
        frame_time = f / fps
        if frame_time >= gyro_peak_time:
            frame_start = f
            return frame_start

    if frame_start is None:
        raise Exception("Aucune frame correspondante au pic gyro n'a été trouvée. Ajuste le seuil.")
    
    
def main() -> None:
    """Main entry point."""
    folder = sys.argv[1]
    gyro_file = os.path.join(folder, "gyro.csv")
    video_file = os.path.join(folder, "movie.MOV")
    calib_file = os.path.join(folder, "calib.csv")

    sensor_start_time = build_sensor_start_time(gyro_file)
    video_start_frame = build_video_start_frame(video_file)

    print(f"Sensor start time: {sensor_start_time}")
    print(f"Video start frame: {video_start_frame}")

    calib_df = pd.DataFrame({
        'sensor_second_start': [sensor_start_time],
        'video_frame_start': [video_start_frame]
    })
    calib_df.to_csv(calib_file, index=False)
    print(f"calib.csv généré dans {calib_file}")

if __name__ == "__main__":
    main()
