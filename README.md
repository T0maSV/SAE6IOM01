# Simulateur de Parking Connecté — SAÉ6.IOM.01

> **Livrable final : [`VIALON_Thomas_rapport_final.pdf`](./VIALON_Thomas_rapport_final.pdf)** (Livrable 6)

## Présentation

Projet de fin d'études réalisé dans le cadre du BUT Réseaux & Télécommunications, parcours Internet des Objets et Mobilité (IOM), à l'IUT de Blois — Année universitaire 2025-2026.

Le projet consiste en la conception et la réalisation d'une maquette fonctionnelle de parking connecté intégrant :

- Détection de véhicules par trois technologies de capteurs (effet Hall, Reed/ILS, infrarouge)
- Communication longue portée LoRa 868 MHz entre les capteurs et le serveur
- Contrôle d'accès par badge RFID (13.56 MHz) avec barrière motorisée et sécurité anti-écrasement par capteur ultrason
- Serveur embarqué sur Raspberry Pi 3 (Flask, InfluxDB, SQLite)
- Interface Web de supervision accessible depuis le Raspberry Pi 4 commun

## Arborescence du dépôt
```
├── VIALON_Thomas_rapport_final.pdf   # Livrable 6 — Rapport final
├── VIALON_CdCT_V1.pdf               # Livrables 2 & 3 — Cahier des Charges Technique
├── VIALON_Thomas_Devis.pdf           # Livrable 4 — Devis
├── diagramme_gantt.png               # Livrable 1 — Diagramme de Gantt
│
├── Programme/                        # Intégralité des programmes du projet
│   └── Final/
│       ├── ESP_Parking/              # ESP32 LoRa — Nœud capteur (3 places)
│       ├── ESP_Passerelle/           # ESP32 LoRa — Gateway LoRa/Série
│       ├── ESP_Barrier/              # ESP32 — Contrôleur d'accès (RFID + barrière)
│       └── RPi3/                     # Raspberry Pi 3 — Serveur (app.py, index.html, reset_db.py)
│
├── 3D/                               # Modélisation et fichiers d'impression 3D
│   ├── Maquette Parking.shapr.step   # Projet complet (ensemble des pièces)
│
├── Fritzing/                         # Schémas électroniques (CAO)
│   └── *.fzz                         # Circuits réalisés et envisagés pour le projet
│
└── images/                           # Photos et captures du projet
```

## Technologies utilisées

| Domaine | Technologies |
|---|---|
| Communication sans fil | LoRa 868 MHz, Wi-Fi 2.4 GHz, RFID 13.56 MHz |
| Microcontrôleurs | ESP32 (Heltec LoRa V2), ESP32 DevKit |
| Serveur | Raspberry Pi 3, Python, Flask |
| Bases de données | InfluxDB (séries temporelles), SQLite (utilisateurs/badges) |
| Électronique | PCB gravés par CNC (Fritzing), soudure manuelle |
| Fabrication | Impression 3D PLA, modélisation Shapr3D |

## Auteur

**Thomas VIALON** — BUT R&T 3ᵉ année, parcours IOM — IUT de Blois

Encadrant : M. Xavier JEANNERET
