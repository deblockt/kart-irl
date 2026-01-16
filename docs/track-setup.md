# Configuration du Parcours

Documentation technique pour la mise en place du parcours de course avec portiques ArUco.

## Vue d'ensemble

Le parcours est composé de **4 portiques** que le kart doit traverser dans l'ordre. Chaque portique est équipé de deux marqueurs ArUco pour permettre la détection et le suivi de position.

## Spécifications des marqueurs ArUco

| Paramètre | Valeur |
|-----------|--------|
| Dictionnaire | `cv2.aruco.DICT_4X4_50` |
| Taille du marqueur | 10 cm (100 mm) |
| Hauteur depuis le sol | 7.5 cm |
| Distance entre les deux tags d'un portique | 17.5 cm (bord intérieur à bord intérieur) |

## Attribution des IDs

Les marqueurs suivent une convention de numérotation :
- **Tags de droite** : IDs pairs
- **Tags de gauche** : IDs impairs

| Portique | Tag Droite (pair) | Tag Gauche (impair) |
|----------|-------------------|---------------------|
| Porte 1  | 10                | 11                  |
| Porte 2  | 20                | 21                  |
| Porte 3  | 30                | 31                  |
| Porte 4  | 40                | 41                  |

## Schéma d'un portique (vue de face)

```
        ┌───────────────────────────────────────────┐
        │            Structure portique              │
        │                                            │
   ┌────┴────┐                                 ┌────┴────┐
   │  Tag    │                                 │  Tag    │
   │ Gauche  │<─── 17.5 cm (bord à bord) ────>│ Droite  │
   │ (impair)│                                 │  (pair) │
   │  10 cm  │                                 │  10 cm  │
   └────┬────┘                                 └────┬────┘
        │              7.5 cm                       │
   ═════╧═══════════════════════════════════════════╧═════
                          Sol
```

## Disposition du parcours

```
    [DÉPART]
        │
        ▼
   ┌─────────┐
   │ Porte 1 │  (10 / 11)
   └─────────┘
        │
        ▼
   ┌─────────┐
   │ Porte 2 │  (20 / 21)
   └─────────┘
        │
        ▼
   ┌─────────┐
   │ Porte 3 │  (30 / 31)
   └─────────┘
        │
        ▼
   ┌─────────┐
   │ Porte 4 │  (40 / 41)
   └─────────┘
        │
        ▼
   [ARRIVÉE]
```

## Génération des marqueurs

Pour générer les marqueurs nécessaires au parcours :

```bash
cd server
uv run generate_gate_markers.py
```

Les fichiers PNG seront créés dans le dossier `markers/gates/`.

## Conseils d'installation

1. **Surface** : Imprimer les marqueurs sur du papier mat pour éviter les reflets
2. **Fixation** : Coller sur un support rigide (carton, bois)
3. **Alignement** : S'assurer que les deux tags d'un portique sont à la même hauteur
4. **Éclairage** : Éviter les contre-jours et ombres directes sur les marqueurs
5. **Contraste** : Le fond derrière les marqueurs doit être uniforme si possible

## Fichiers de référence

- Vidéo de test : `server/IMG_0876.MOV`
- Script de détection : `server/detect_gates.py`
