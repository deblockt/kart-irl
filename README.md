# Kart IRL

Augmented reality kart project inspired by Mario Kart Live.

## Project Structure

```
kart-irl/
├── server/      # Python server (video processing, overlay, game engine)
├── esp32/       # ESP-32 microcontroller code for the kart
├── webapp/      # Web application for video streaming
└── docs/        # Technical documentation (schematics, specifications)
```

## Modules

### Server
Python server responsible for:
- Receiving and processing the video stream from the karts
- Injecting overlay elements (items, UI, effects)
- Managing the game engine (collisions, items, scores)

### ESP-32
Embedded code for the kart:
- Motor control
- Video streaming via camera
- WiFi communication with the server

### Webapp
Web application providing:
- Real-time augmented video stream display
- Kart control interface
- Race information display

### Docs
Technical documentation including:
- Kart electronic schematics
- ESP-32 wiring diagrams
- Communication protocol specifications

## Installation

See each module's README for specific installation instructions.

## License

TBD
