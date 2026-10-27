# Site Web - Église Saint-Martin de Villar-d'Arène

Site web de l'association des Amis de l'Église Saint-Martin de Villar-d'Arène (Hautes-Alpes).

## Technologie

- HTML statique avec Pico CSS
- Build Python (injection header/footer + placeholders)
- Docker multi-stage (Python build → nginx)
- Formulaire : Formspree
- Stats : Simple Analytics
- Monitoring : UptimeRobot

## Démarrage rapide

```bash
# Configuration
cp docker/.env.example docker/.env
# Éditer docker/.env avec vos valeurs

# Build local
python build.py              # staging
python build.py --production # production
python build.py --watch      # watch mode

# Servir localement
cd dist && python -m http.server 8000
```

## Déploiement Docker

```bash
cd docker
docker compose up -d --build
```

## Structure

```
src/                    # Sources HTML/CSS/JS
├── index.html          # Accueil
├── actualites/         # Pages par année
├── association/        # Qui sommes-nous, adhésion, contact
├── eglise/             # Historique, galerie, travaux...
├── components/         # header.html, footer.html
└── assets/
    ├── css/, js/
    ├── images/
    └── documents/
```

## Licence

MIT - Voir [LICENSE](LICENSE).
