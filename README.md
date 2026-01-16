# Kart IRL

Projet de kart en réalité augmentée inspiré de Mario Kart Live.

## Structure du projet

```
kart-irl/
├── server/      # Serveur Python (traitement vidéo, overlay, moteur de jeu)
├── esp32/       # Code du microcontrôleur ESP-32 pour le kart
├── webapp/      # Application web pour la diffusion vidéo
└── docs/        # Documentation technique (schémas, spécifications)
```

## Modules

### Server
Serveur Python responsable de :
- Réception et traitement du flux vidéo des karts
- Injection d'éléments en superposition (items, UI, effets)
- Gestion du moteur de jeu (collisions, items, scores)

### ESP-32
Code embarqué pour le kart :
- Contrôle des moteurs
- Streaming vidéo via caméra
- Communication WiFi avec le serveur

### Webapp
Application web permettant :
- Visualisation du flux vidéo augmenté
- Interface de contrôle du kart
- Affichage des informations de course

### Docs
Documentation technique incluant :
- Schémas électroniques du kart
- Diagrammes de câblage ESP-32
- Spécifications du protocole de communication

## Installation

Voir le README de chaque module pour les instructions d'installation spécifiques.

## Licence

À définir
