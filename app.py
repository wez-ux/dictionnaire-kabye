from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# Configuration Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', 'dflbiu1hi'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

# Configuration
# DATA_DIR = Path('/home/ubuntu/dictionnaire-kabye/data')
# DATA_FILE = DATA_DIR / 'mots_kabye.json'

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "mots_kabye.json"


# Taille maximale pour les uploads (5MB)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# Extensions autorisées pour les images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Configuration maintenance
MAINTENANCE_START = datetime(2024, 1, 1, 22, 0, 0)  # À modifier selon vos besoins
MAINTENANCE_DURATION = timedelta(hours=2)
MAINTENANCE_MODE = False  # Mettre à True pour activer la maintenance manuellement

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
    elif time_until_maintenance.total_seconds() > 0 and time_until_maintenance.total_seconds() <= 7200:  # 2 heures
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

def initialiser_donnees():
    """Créer le dossier data et le fichier JSON s'ils n'existent pas"""
    DATA_DIR.mkdir(exist_ok=True)
    
    if not DATA_FILE.exists():
        donnees_initiales = {
            "mots": [
                {
                    "id": 1,
                    "mot_kabye": "aalayu",
                    "variantes_orthographiques": ["aaleyu", "aaleykatay", "akataleyu", "aakaytay"],
                    "api": "[âlâyú]",
                    "traduction_francaise": "qui sera le premier",
                    "sens_multiple": ["qui sera le premier (compétition)"],
                    "synonymes": ["aaleykatay"],
                    "categorie_grammaticale": "nom",
                    "sous_categorie": "nom propre",
                    "origine_mot": "",
                    "exemple_usage": "Aalayu tem qui sera le premier à finir",
                    "traduction_exemple": "Qui sera le premier à finir",
                    "expressions_associees": [
                        {
                            "expression": "aalayu tem",
                            "traduction": "qui sera le premier à finir"
                        }
                    ],
                    "notes_usage": "Utilisé dans un contexte de compétition",
                    "image_url": "",
                    "verifie_par": "Admin",
                    "date_ajout": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "date_modification": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            ],
            "prochain_id": 2
        }
        sauvegarder_donnees(donnees_initiales)
        return donnees_initiales
    
    return charger_donnees()

def charger_donnees():
    """Charger les données depuis le fichier JSON"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur chargement: {e}")
        return initialiser_donnees()

def sauvegarder_donnees(donnees):
    """Sauvegarder les données dans le fichier JSON"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(donnees, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Erreur sauvegarde: {e}")
        return False

def upload_image_cloudinary(image_file):
    """Uploader une image sur Cloudinary"""
    try:
        # Upload sur Cloudinary
        result = cloudinary.uploader.upload(
            image_file,
            folder="dictionnaire-kabye",
            use_filename=True,
            unique_filename=True,
            overwrite=False,
            resource_type="image"
        )
        return result['secure_url']  # Retourne l'URL sécurisée
    except Exception as e:
        print(f"Erreur upload Cloudinary: {e}")
        return None

def supprimer_image_cloudinary(image_url):
    """Supprimer une image de Cloudinary"""
    try:
        if image_url:
            # Extraire le public_id de l'URL
            public_id = image_url.split('/')[-1].split('.')[0]
            result = cloudinary.uploader.destroy(public_id)
            return result.get('result') == 'ok'
    except Exception as e:
        print(f"Erreur suppression Cloudinary: {e}")
    return False

@app.route('/')
def accueil():
    return render_template('formulaire.html')

@app.route('/editer/<int:mot_id>')
def editer_mot(mot_id):
    """Page d'édition d'un mot"""
    donnees = charger_donnees()
    mot = next((m for m in donnees['mots'] if m['id'] == mot_id), None)
    
    if not mot:
        return "Mot non trouvé", 404
    
    return render_template('formulaire.html', mot=mot, edition=True)

@app.route('/sauvegarder', methods=['POST'])
def sauvegarder_mot():
    try:
        # Gérer les données form-data (avec fichier)
        if request.content_type.startswith('multipart/form-data'):
            data = request.form
            image_file = request.files.get('image')
        else:
            # Gérer les données JSON (sans fichier)
            data = request.get_json()
            image_file = None
        
        # Validation
        if not data.get('mot_kabye') or not data.get('traduction_francaise'):
            return jsonify({'success': False, 'error': 'Mot kabyè et traduction française sont obligatoires'})
        
        # Charger les données existantes
        donnees = charger_donnees()
        
        # Vérifier si c'est une édition
        mot_id = data.get('mot_id')
        if mot_id:
            # MODE ÉDITION
            mot_id = int(mot_id)
            mot_index = next((i for i, m in enumerate(donnees['mots']) if m['id'] == mot_id), None)
            
            if mot_index is None:
                return jsonify({'success': False, 'error': 'Mot non trouvé'})
            
            # Vérifier si le nom a changé et s'il existe déjà
            ancien_mot = donnees['mots'][mot_index]
            if ancien_mot['mot_kabye'].lower() != data['mot_kabye'].lower():
                mot_existe = any(mot['mot_kabye'].lower() == data['mot_kabye'].lower() 
                                for mot in donnees['mots'] if mot['id'] != mot_id)
                if mot_existe:
                    return jsonify({'success': False, 'error': 'Ce mot existe déjà dans le dictionnaire'})
            
            # Gérer l'image
            image_url = ancien_mot.get('image_url', '')
            supprimer_ancienne_image = data.get('supprimer_image') == 'true'
            
            if supprimer_ancienne_image and image_url:
                supprimer_image_cloudinary(image_url)
                image_url = ""
            
            if image_file and image_file.filename != '':
                if allowed_file(image_file.filename):
                    # Supprimer l'ancienne image si elle existe
                    if image_url:
                        supprimer_image_cloudinary(image_url)
                    # Uploader la nouvelle image
                    image_url = upload_image_cloudinary(image_file)
                    if not image_url:
                        return jsonify({'success': False, 'error': 'Erreur lors du téléchargement de l\'image'})
                else:
                    return jsonify({'success': False, 'error': 'Type de fichier non autorisé'})
        else:
            # MODE CRÉATION
            # Vérifier si le mot existe déjà
            mot_existe = any(mot['mot_kabye'].lower() == data['mot_kabye'].lower() 
                            for mot in donnees['mots'])
            
            if mot_existe:
                return jsonify({'success': False, 'error': 'Ce mot existe déjà dans le dictionnaire'})
            
            # Upload de l'image
            image_url = ""
            if image_file and image_file.filename != '':
                if allowed_file(image_file.filename):
                    image_url = upload_image_cloudinary(image_file)
                    if not image_url:
                        return jsonify({'success': False, 'error': 'Erreur lors du téléchargement de l\'image'})
                else:
                    return jsonify({'success': False, 'error': 'Type de fichier non autorisé'})
        
        # Traiter les listes (variantes, sens multiples, synonymes)
        variantes = [v.strip() for v in data.get('variantes_orthographiques', '').split(',') if v.strip()]
        sens_multiple = [s.strip() for s in data.get('sens_multiple', '').split(';') if s.strip()]
        synonymes = [s.strip() for s in data.get('synonymes', '').split(',') if s.strip()]
        
        # Traiter les expressions associées
        expressions = []
        expressions_text = data.get('expressions_associees', '').strip()
        if expressions_text:
            for expr_line in expressions_text.split('\n'):
                if ':' in expr_line:
                    expr_parts = expr_line.split(':', 1)
                    expressions.append({
                        "expression": expr_parts[0].strip(),
                        "traduction": expr_parts[1].strip()
                    })
        
        # Préparer les données du mot
        mot_data = {
            "mot_kabye": data['mot_kabye'].strip(),
            "variantes_orthographiques": variantes,
            "api": data.get('api', '').strip(),
            "traduction_francaise": data['traduction_francaise'].strip(),
            "sens_multiple": sens_multiple,
            "synonymes": synonymes,
            "categorie_grammaticale": data.get('categorie_grammaticale', '').strip(),
            "sous_categorie": data.get('sous_categorie', '').strip(),
            "origine_mot": data.get('origine_mot', '').strip(),
            "exemple_usage": data.get('exemple_usage', '').strip(),
            "traduction_exemple": data.get('traduction_exemple', '').strip(),
            "expressions_associees": expressions,
            "notes_usage": data.get('notes_usage', '').strip(),
            "image_url": image_url,
            "verifie_par": data.get('verifie_par', 'Anonyme').strip(),
            "date_modification": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if mot_id:
            # Mettre à jour le mot existant
            donnees['mots'][mot_index].update(mot_data)
            message = f'✅ Mot "{data["mot_kabye"]}" modifié avec succès !'
        else:
            # Créer un nouveau mot
            nouveau_mot = {
                "id": donnees['prochain_id'],
                "date_ajout": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                **mot_data
            }
            donnees['mots'].append(nouveau_mot)
            donnees['prochain_id'] += 1
            message = f'✅ Mot "{data["mot_kabye"]}" sauvegardé avec succès !'
        
        # Sauvegarder
        if sauvegarder_donnees(donnees):
            return jsonify({
                'success': True, 
                'message': message,
                'image_url': image_url,
                'mot_id': mot_id if mot_id else donnees['prochain_id'] - 1
            })
        else:
            return jsonify({'success': False, 'error': 'Erreur lors de la sauvegarde'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def calculer_statistiques(mots):
    """Calculer les statistiques par personne"""
    stats_par_personne = {}
    
    for mot in mots:
        verifie_par = mot.get('verifie_par', 'Non spécifié')
        
        if verifie_par not in stats_par_personne:
            stats_par_personne[verifie_par] = {
                'total_mots': 0,
                'mots_par_mois': {},
                'derniere_activite': '',
                'categories': {},
                'evolution_temporelle': []
            }
        
        # Compter le mot
        stats_par_personne[verifie_par]['total_mots'] += 1
        
        # Compter par catégorie
        categorie = mot.get('categorie_grammaticale', 'Non spécifiée')
        stats_par_personne[verifie_par]['categories'][categorie] = \
            stats_par_personne[verifie_par]['categories'].get(categorie, 0) + 1
        
        # Traiter les dates
        date_ajout = mot.get('date_ajout', '')
        date_modification = mot.get('date_modification', '')
        
        if date_ajout:
            try:
                date_obj = datetime.strptime(date_ajout, "%Y-%m-%d %H:%M:%S")
                mois_annee = date_obj.strftime("%Y-%m")
                
                # Statistiques par mois
                stats_par_personne[verifie_par]['mots_par_mois'][mois_annee] = \
                    stats_par_personne[verifie_par]['mots_par_mois'].get(mois_annee, 0) + 1
                
                # Dernière activité
                if not stats_par_personne[verifie_par]['derniere_activite'] or \
                   date_obj > datetime.strptime(stats_par_personne[verifie_par]['derniere_activite'], "%Y-%m-%d %H:%M:%S"):
                    stats_par_personne[verifie_par]['derniere_activite'] = date_ajout
                    
            except ValueError:
                pass
    
    # Calculer l'évolution temporelle pour chaque personne
    for personne, data in stats_par_personne.items():
        evolution = []
        cumul = 0
        
        # Trier les mois chronologiquement
        mois_tries = sorted(data['mots_par_mois'].keys())
        for mois in mois_tries:
            cumul += data['mots_par_mois'][mois]
            evolution.append({
                'mois': mois,
                'nouveaux_mots': data['mots_par_mois'][mois],
                'total_cumule': cumul
            })
        
        data['evolution_temporelle'] = evolution
    
    # Statistiques globales
    stats_globales = {
        'total_mots': len(mots),
        'nombre_contributeurs': len(stats_par_personne),
        'moyenne_mots_par_contributeur': len(mots) / len(stats_par_personne) if stats_par_personne else 0,
        'contributeurs_actifs': len([p for p, d in stats_par_personne.items() if d['total_mots'] >= 5])
    }
    
    return {
        'par_personne': stats_par_personne,
        'globales': stats_globales
    }

@app.route('/supprimer/<int:mot_id>', methods=['POST'])
def supprimer_mot(mot_id):
    try:
        donnees = charger_donnees()
        
        # Trouver le mot à supprimer
        mot_index = next((i for i, m in enumerate(donnees['mots']) if m['id'] == mot_id), None)
        
        if mot_index is None:
            return jsonify({'success': False, 'error': 'Mot non trouvé'})
        
        mot = donnees['mots'][mot_index]
        
        # Supprimer l'image associée si elle existe
        if mot.get('image_url'):
            supprimer_image_cloudinary(mot['image_url'])
        
        # Supprimer le mot
        donnees['mots'].pop(mot_index)
        
        # Sauvegarder
        if sauvegarder_donnees(donnees):
            return jsonify({
                'success': True, 
                'message': f'✅ Mot "{mot["mot_kabye"]}" supprimé avec succès !'
            })
        else:
            return jsonify({'success': False, 'error': 'Erreur lors de la suppression'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mots')
def liste_mots():
    """Afficher tous les mots avec recherche multi-critères"""
    donnees = charger_donnees()
    mots = donnees['mots']

    # Récupérer les paramètres de recherche
    terme_recherche = request.args.get('q', '').strip().lower()
    champ_recherche = request.args.get('champ', 'tous')
    initiale = request.args.get('initiale', '').upper()  # Recherche par première lettre
    
    # Filtrer par initiale si spécifiée
    if initiale and len(initiale) == 1:
        mots = [mot for mot in mots if mot['mot_kabye'].upper().startswith(initiale)]
    
    # Filtrer par terme de recherche si spécifié
    if terme_recherche:
        mots_filtres = []
        for mot in mots:
            correspondance = False
            
            if champ_recherche in ['tous', 'kabye']:
                if (terme_recherche in mot['mot_kabye'].lower() or
                    any(terme_recherche in variante.lower() for variante in mot.get('variantes_orthographiques', []))):
                    correspondance = True
            
            if not correspondance and champ_recherche in ['tous', 'francais']:
                if (terme_recherche in mot['traduction_francaise'].lower() or
                    any(terme_recherche in sens.lower() for sens in mot.get('sens_multiple', []))):
                    correspondance = True
            
            if not correspondance and champ_recherche == 'tous':
                if (any(terme_recherche in synonyme.lower() for synonyme in mot.get('synonymes', [])) or
                    terme_recherche in mot.get('categorie_grammaticale', '').lower() or
                    terme_recherche in mot.get('sous_categorie', '').lower() or
                    terme_recherche in mot.get('notes_usage', '').lower()):
                    correspondance = True
            
            if correspondance:
                mots_filtres.append(mot)
        
        mots = mots_filtres
    
    # Trier les mots
    mots_tries = sorted(mots, key=lambda x: max(
        x.get('date_modification', ''),
        x.get('date_ajout', '')
    ), reverse=True)
    
    return render_template('liste_mots.html', 
                         mots=mots_tries, 
                         terme_recherche=terme_recherche,
                         nombre_resultats=len(mots),
                         champ_recherche=champ_recherche,
                         initiale_recherche=initiale)


@app.route('/api/mots')
def api_mots():
    """API pour récupérer les mots en JSON"""
    donnees = charger_donnees()
    return jsonify(donnees['mots'])

@app.route('/api/mot/<int:mot_id>')
def api_mot_detail(mot_id):
    """API pour récupérer un mot spécifique en JSON"""
    donnees = charger_donnees()
    mot = next((m for m in donnees['mots'] if m['id'] == mot_id), None)
    
    if mot:
        return jsonify(mot)
    else:
        return jsonify({'error': 'Mot non trouvé'}), 404


@app.route('/statistiques')
def statistiques():
    """Page de statistiques des contributions"""
    donnees = charger_donnees()
    return render_template('statistiques.html', mots=donnees['mots'])

@app.route('/api/statistiques')
def api_statistiques():
    """API pour récupérer les données statistiques"""
    donnees = charger_donnees()
    stats = calculer_statistiques(donnees['mots'])
    return jsonify(stats)

@app.route('/api/maintenance')
def api_maintenance():
    """API pour récupérer les informations de maintenance"""
    return jsonify(get_maintenance_info())

@app.route('/sante')
def sante():
    """Route de santé"""
    return jsonify({
        'status': 'OK',
        'message': 'Dictionnaire Kabyè en ligne',
        'timestamp': datetime.now().isoformat(),
        'total_mots': len(charger_donnees()['mots'])
    })

if __name__ == '__main__':
    # Initialisation au premier démarrage
    initialiser_donnees()
    
    # Démarrer en mode production
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)