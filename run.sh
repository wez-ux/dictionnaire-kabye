#!/bin/bash

# Aller dans le dossier de l'application
cd /home/ubuntu/dictionnaire-kabye

# Activer l'environnement virtuel (optionnel mais recommandé)
source venv/bin/activate

# Démarrer l'application avec Gunicorn
gunicorn --bind 0.0.0.0:5000 app:app --daemon

echo "✅ Application démarrée sur le port 5000"