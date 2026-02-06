# Server

Python server for video processing and game engine management.

## Features

- Receiving the video stream from karts via WiFi
- Detection and tracking of circuit elements (ArUco markers)
- Real-time overlay injection (items, visual effects, UI)
- Game engine (collision management, items, scores)
- Streaming the augmented feed to the webapp

## Prerequisites

- Python 3.14+
- uv (dependency manager)
- Webcam (for testing)

## Installation

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
cd server
uv sync
```

