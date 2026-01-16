# Tracks for Kart-IRL Demo and AR

## Content

Each directory contains the following files:

**Raw data files** (contain data before and after sync point):
- `movie.MOV` : the track recording (used to build track map)
- `accel.csv` : accelerometer data (columns: time, seconds_elapsed, z, y, x in g)
- `gyro.csv` : gyroscope data (columns: time, seconds_elapsed, z, y, x in rad/s)
- `calib.csv` : synchronization data between sensors and video
  - `sensor_second_start`: timestamp (in seconds_elapsed) marking the sync point in sensor files
  - `video_frame_start`: frame number marking the same sync point in the video

**Generated files** (start at sync point, t=0):
- `motor.csv` : simulated motor data generated from IMU (see `convert_to_motor.py`)
  - `seconds_elapsed`: time starting at 0 (sync point)
  - `speed_ms`: estimated speed in m/s
  - `speed_percent`: normalized speed (0-100%)
  - `direction_percent`: steering direction (-100=left, 0=straight, +100=right)
  - `direction_enum`: LEFT, STRAIGHT, or RIGHT
  - `direction_angle_deg`: estimated steering angle (-45° to +45°)
- `map.png` : 2D map of the track generated from video and sensors (see `generate_map.py`)

## Synchronization

All data sources (video, accelerometer, gyroscope) are synchronized using `calib.csv`. A physical "tap" gesture was used to create a detectable event in both the video (motion blur) and sensors (gyroscope peak).

## Phone Orientation & Sensor Axes

The phone is mounted **vertically (portrait mode)** with the camera facing forward.

```
        ┌─────────┐
        │    o    │  ← Camera (facing forward)
        │         │
        │    Y    │
        │    ↑    │
        │    │    │
        │    └──→ X
        │      Z  │  (Z points out of screen, toward front)
        │   (•)   │
        └─────────┘
```

### Accelerometer axes (in g)
| Axis | Direction | Usage |
|------|-----------|-------|
| X | Left/Right (lateral) | Lateral acceleration |
| Y | Up/Down (vertical) | Contains gravity (~1g) |
| Z | Forward/Backward | **Speed calculation** |

### Gyroscope axes (in rad/s)
| Axis | Rotation | Usage |
|------|----------|-------|
| X | Pitch (tilt forward/backward) | Pitch |
| Y | Yaw (turn left/right) | **Steering direction** |
| Z | Roll (tilt left/right) | Roll |

## ArUco Tags Setup

The track uses **ArUco 4x4 markers** (dictionary: `DICT_4X4_50`) with the following configuration:

### Gates
There are **4 gates** that the kart passes through. Each gate consists of two ArUco tags:
- **Left tag**: ID ends with `0` (e.g., 10, 20, 30, 40)
- **Right tag**: ID ends with `1` (e.g., 11, 21, 31, 41)

| Gate | Left Tag ID | Right Tag ID |
|------|-------------|--------------|
| 1    | 10          | 11           |
| 2    | 20          | 21           |
| 3    | 30          | 31           |
| 4    | 40          | 41           |

### Physical Dimensions
- **Tag size**: 10 cm x 10 cm
- **Distance between tags** (inner edge to inner edge): 17.5 cm
- **Tag height from ground** (bottom of tag): 7.5 cm

## Scripts

### calib_track.py

Génère le fichier `calib.csv` en détectant automatiquement le point de synchronisation entre la vidéo et les capteurs (via un "tap" physique).

```bash
uv run python tracks/calib_track.py tracks/track1
```

### ar_viewer.py

Affiche la vidéo avec overlay AR des tags ArUco détectés et les données IMU synchronisées.

```bash
uv run python tracks/ar_viewer.py tracks/track1
```

**Fonctionnalités:**
- Détection des tags ArUco avec contour et ID
- Identification des portes (1-4) avec indication gauche/droite
- Ligne entre les deux tags quand une porte complète est visible
- Overlay des données IMU (vitesse, orientation, données brutes)
- Correction automatique de l'orientation vidéo (portrait/paysage)

**Contrôles:**
- `Espace` : Pause/Play
- `Q` / `Échap` : Quitter
- `R` : Reset vitesse et orientation
- `←` / `→` : Reculer/Avancer d'1 frame
- `,` / `.` : Reculer/Avancer d'1 seconde

### convert_to_motor.py

Convertit les données IMU (accel.csv, gyro.csv) en données moteur simulées pour tester sans ESP32.

```bash
uv run python tracks/convert_to_motor.py tracks/track1
```

**Sortie:** `motor.csv` avec les colonnes:
| Colonne | Description |
|---------|-------------|
| `seconds_elapsed` | Temps relatif au point de sync |
| `speed_ms` | Vitesse estimée en m/s |
| `speed_percent` | Vitesse normalisée (0-100%) |
| `direction_percent` | Direction (-100=gauche, 0=droit, +100=droite) |
| `direction_enum` | LEFT, STRAIGHT, ou RIGHT |
| `direction_angle_deg` | Angle de braquage estimé (-45° à +45°) |

### generate_map.py

Génère une carte 2D du circuit à partir de la vidéo et des données capteurs.

```bash
uv run python tracks/generate_map.py tracks/track1
uv run python tracks/generate_map.py tracks/track1 --output custom_map.png
uv run python tracks/generate_map.py tracks/track1 --no-show
```

**Fonctionnalités:**
- Calcule la trajectoire du kart par intégration (vitesse + gyroscope)
- Détecte les portes ArUco dans la vidéo
- Estime la position des portes sur la carte
- Génère une image PNG avec la trajectoire et les portes

**Sortie:** `map.png` dans le dossier du track

### utils.py

Module utilitaire contenant les fonctions partagées entre les scripts :
- Chargement des données (calibration, sensors, motor)
- Synchronisation video/sensors
- Filtres (passe-bas, passe-haut)
- Gestion vidéo (rotation, ouverture)
- Détection ArUco
- Calcul de trajectoire
