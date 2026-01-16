# Server

Serveur Python pour le traitement vidéo et la gestion du moteur de jeu.

## Fonctionnalités

- Réception du flux vidéo des karts via WiFi
- Détection et tracking des éléments sur le circuit (marqueurs ArUco)
- Injection d'overlays en temps réel (items, effets visuels, UI)
- Moteur de jeu (gestion des collisions, items, scores)
- Streaming du flux augmenté vers la webapp

## Prérequis

- Python 3.14+
- uv (gestionnaire de dépendances)
- Webcam (pour les tests)

## Installation

```bash
# Installer uv si nécessaire
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installer les dépendances
cd server
uv sync
```

