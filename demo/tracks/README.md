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

Generates the `calib.csv` file by automatically detecting the synchronization point between the video and sensors (via a physical "tap").

```bash
uv run python tracks/calib_track.py tracks/track1
```

### ar_viewer.py

Displays the video with AR overlay of detected ArUco tags and synchronized IMU data.

```bash
uv run python tracks/ar_viewer.py tracks/track1
```

**Features:**
- ArUco tag detection with contour and ID
- Gate identification (1-4) with left/right indication
- Line between the two tags when a complete gate is visible
- IMU data overlay (speed, orientation, raw data)
- Automatic video orientation correction (portrait/landscape)

**Controls:**
- `Space`: Pause/Play
- `Q` / `Esc`: Quit
- `R`: Reset speed and orientation
- `←` / `→`: Step back/forward 1 frame
- `,` / `.`: Step back/forward 1 second

### convert_to_motor.py

Converts IMU data (accel.csv, gyro.csv) into simulated motor data for testing without an ESP32.

```bash
uv run python tracks/convert_to_motor.py tracks/track1
```

**Output:** `motor.csv` with the following columns:
| Column | Description |
|--------|-------------|
| `seconds_elapsed` | Time relative to sync point |
| `speed_ms` | Estimated speed in m/s |
| `speed_percent` | Normalized speed (0-100%) |
| `direction_percent` | Direction (-100=left, 0=straight, +100=right) |
| `direction_enum` | LEFT, STRAIGHT, or RIGHT |
| `direction_angle_deg` | Estimated steering angle (-45° to +45°) |

### generate_map.py

Generates a 2D map of the track from video and sensor data.

```bash
uv run python tracks/generate_map.py tracks/track1
uv run python tracks/generate_map.py tracks/track1 --output custom_map.png
uv run python tracks/generate_map.py tracks/track1 --no-show
```

**Features:**
- Computes the kart trajectory by integration (speed + gyroscope)
- Detects ArUco gates in the video
- Estimates gate positions on the map
- Generates a PNG image with the trajectory and gates

**Output:** `map.png` in the track directory

### utils.py

Utility module containing shared functions across scripts:
- Data loading (calibration, sensors, motor)
- Video/sensor synchronization
- Filters (low-pass, high-pass)
- Video management (rotation, opening)
- ArUco detection
- Trajectory computation
