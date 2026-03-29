# utils/helpers.py

import secrets
from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv
from database import get_session, MotKabye
from sqlalchemy import or_, func
from flask_cors import CORS

# Configuration Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'dflbiu1hi'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

# Configuration
BASE_DIR = Path(__file__).resolve().parent


# Extensions autorisées pour les images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Configuration maintenance
MAINTENANCE_START = datetime(2024, 1, 1, 22, 0, 0)
MAINTENANCE_DURATION = timedelta(hours=2)
MAINTENANCE_MODE = False

def get_maintenance_info():
    """Obtenir les informations de maintenance"""
    now = datetime.now()
    time_until_maintenance = MAINTENANCE_START - now
    
    if MAINTENANCE_MODE:
        return {
            'active': True,
            'message': '🛠️ Maintenance en cours',
            'time_remaining': 'Maintenance en cours'
        }
    elif time_until_maintenance.total_seconds() > 0 and time_until_maintenance.total_seconds() <= 7200:
        hours = int(time_until_maintenance.total_seconds() // 3600)
        minutes = int((time_until_maintenance.total_seconds() % 3600) // 60)
        seconds = int(time_until_maintenance.total_seconds() % 60)
        
        return {
            'active': False,
            'upcoming': True,
            'message': f'⚠️ Maintenance prévue dans {hours:02d}:{minutes:02d}:{seconds:02d}',
            'time_remaining': f'{hours:02d}:{minutes:02d}:{seconds:02d}',
            'timestamp': MAINTENANCE_START.isoformat()
        }
    else:
        return {
            'active': False,
            'upcoming': False,
            'message': '',
            'time_remaining': ''
        }

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def json_to_list(data):
    """Convertir les données JSON stockées en liste"""
    if not data:
        return []
    try:
        # Si c'est déjà une liste, la retourner
        if isinstance(data, list):
            return data
        # Sinon essayer de parser le JSON
        return json.loads(data)
    except json.JSONDecodeError:
        # Si le JSON est invalide, essayer de le traiter comme une chaîne simple
        if isinstance(data, str):
            # Vérifier si c'est une chaîne avec des points-virgules
            if ';' in data:
                return [item.strip() for item in data.split(';') if item.strip()]
            # Ou si c'est une chaîne simple
            return [data.strip()] if data.strip() else []
        return []

def list_to_json(data_list):
    """Convertir une liste en JSON pour stockage"""
    return json.dumps(data_list, ensure_ascii=False) if data_list else None



def upload_image_cloudinary(image_file):
    """Uploader une image sur Cloudinary"""
    try:
        result = cloudinary.uploader.upload(
            image_file,
            folder="dictionnaire-kabye",
            use_filename=True,
            unique_filename=True,
            overwrite=False,
            resource_type="image"
        )
        return result['secure_url']
    except Exception as e:
        print(f"Erreur upload Cloudinary: {e}")
        return None

def supprimer_image_cloudinary(image_url):
    """Supprimer une image de Cloudinary"""
    try:
        if image_url:
            public_id = image_url.split('/')[-1].split('.')[0]
            result = cloudinary.uploader.destroy(public_id)
            return result.get('result') == 'ok'
    except Exception as e:
        print(f"Erreur suppression Cloudinary: {e}")
    return False

