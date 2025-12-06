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
BASE_DIR = Path(__file__).resolve().parent

# Taille maximale pour les uploads (5MB)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

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

def initialiser_donnees():
    """Initialiser la base de données si nécessaire"""
    session = get_session()
    try:
        # Vérifier si des données existent
        count = session.query(MotKabye).count()
        print(f"Base de données initialisée avec {count} mots.")
    except Exception as e:
        print(f"Erreur d'initialisation: {e}")
    finally:
        session.close()

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

@app.route('/')
def accueil():
    return render_template('formulaire.html')

@app.route('/editer/<int:mot_id>')
def editer_mot(mot_id):
    """Page d'édition d'un mot"""
    session = get_session()
    try:
        mot = session.query(MotKabye).filter(MotKabye.id == mot_id).first()
        if not mot:
            return "Mot non trouvé", 404
        
        # DEBUG: Vérifier ce qui est stocké
        print(f"DEBUG - sens_multiple raw: {mot.sens_multiple}")
        print(f"DEBUG - sens_multiple type: {type(mot.sens_multiple)}")
        print(f"DEBUG - json_to_list result: {json_to_list(mot.sens_multiple)}")
        
        # Convertir les données JSON en listes pour le template
        mot_dict = {
            'id': mot.id,
            'mot_kabye': mot.mot_kabye,
            'variantes_orthographiques': ', '.join(json_to_list(mot.variantes_orthographiques)) if mot.variantes_orthographiques else '',
            'api': mot.api or '',
            'traduction_francaise': mot.traduction_francaise or '',
            'sens_multiple': '; '.join(json_to_list(mot.sens_multiple)) if mot.sens_multiple else '',
            'synonymes': ', '.join(json_to_list(mot.synonymes)) if mot.synonymes else '',
            'categorie_grammaticale': mot.categorie_grammaticale or '',
            'sous_categorie': mot.sous_categorie or '',
            'origine_mot': mot.origine_mot or '',
            'exemple_usage': mot.exemple_usage or '',
            'traduction_exemple': mot.traduction_exemple or '',
            'expressions_associees': json_to_list(mot.expressions_associees),
            'notes_usage': mot.notes_usage or '',
            'image_url': mot.image_url or '',
            'verifie_par': mot.verifie_par or '',
            'date_ajout': mot.date_ajout.strftime("%Y-%m-%d %H:%M:%S") if mot.date_ajout else '',
            'date_modification': mot.date_modification.strftime("%Y-%m-%d %H:%M:%S") if mot.date_modification else ''
        }
        
        return render_template('formulaire.html', mot=mot_dict, edition=True)
    finally:
        session.close()


@app.route('/sauvegarder', methods=['POST'])
def sauvegarder_mot():
    session = get_session()
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
        
        # Vérifier si c'est une édition
        mot_id = data.get('mot_id')
        if mot_id:
            # MODE ÉDITION
            mot_id = int(mot_id)
            mot = session.query(MotKabye).filter(MotKabye.id == mot_id).first()
            
            if not mot:
                return jsonify({'success': False, 'error': 'Mot non trouvé'})
            
            # Vérifier si le nom a changé et s'il existe déjà
            if mot.mot_kabye.lower() != data['mot_kabye'].lower():
                mot_existe = session.query(MotKabye).filter(
                    func.lower(MotKabye.mot_kabye) == data['mot_kabye'].lower(),
                    MotKabye.id != mot_id
                ).first()
                if mot_existe:
                    return jsonify({'success': False, 'error': 'Ce mot existe déjà dans le dictionnaire'})
            
            # Gérer l'image
            image_url = mot.image_url or ''
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
            mot_existe = session.query(MotKabye).filter(
                func.lower(MotKabye.mot_kabye) == data['mot_kabye'].lower()
            ).first()
            
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
            
            # Créer un nouveau mot
            mot = MotKabye()
        
        # Traiter les listes
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
        
        # Mettre à jour les données du mot
        mot.mot_kabye = data['mot_kabye'].strip()
        mot.variantes_orthographiques = list_to_json(variantes)
        mot.api = data.get('api', '').strip()
        mot.traduction_francaise = data['traduction_francaise'].strip()
        mot.sens_multiple = list_to_json(sens_multiple)
        mot.synonymes = list_to_json(synonymes)
        mot.categorie_grammaticale = data.get('categorie_grammaticale', '').strip()
        mot.sous_categorie = data.get('sous_categorie', '').strip()
        mot.origine_mot = data.get('origine_mot', '').strip()
        mot.exemple_usage = data.get('exemple_usage', '').strip()
        mot.traduction_exemple = data.get('traduction_exemple', '').strip()
        mot.expressions_associees = list_to_json(expressions)
        mot.notes_usage = data.get('notes_usage', '').strip()
        mot.image_url = image_url
        mot.verifie_par = data.get('verifie_par', 'Anonyme').strip()
        mot.date_modification = datetime.now()
        
        if not mot_id:
            # Nouveau mot
            mot.date_ajout = datetime.now()
            session.add(mot)
        
        session.commit()
        
        message = f'✅ Mot "{data["mot_kabye"]}" sauvegardé avec succès !'
        if mot_id:
            message = f'✅ Mot "{data["mot_kabye"]}" modifié avec succès !'
        
        return jsonify({
            'success': True, 
            'message': message,
            'image_url': image_url,
            'mot_id': mot.id
        })
            
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        session.close()

@app.route('/supprimer/<int:mot_id>', methods=['POST'])
def supprimer_mot(mot_id):
    session = get_session()
    try:
        mot = session.query(MotKabye).filter(MotKabye.id == mot_id).first()
        
        if not mot:
            return jsonify({'success': False, 'error': 'Mot non trouvé'})
        
        nom_mot = mot.mot_kabye
        
        # Supprimer l'image associée si elle existe
        if mot.image_url:
            supprimer_image_cloudinary(mot.image_url)
        
        # Supprimer le mot
        session.delete(mot)
        session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'✅ Mot "{nom_mot}" supprimé avec succès !'
        })
            
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        session.close()

@app.route('/mots')
def liste_mots():
    """Afficher tous les mots avec recherche multi-critères"""
    session = get_session()
    try:
        # Récupérer les paramètres de recherche
        terme_recherche = request.args.get('q', '').strip().lower()
        champ_recherche = request.args.get('champ', 'tous')
        initiale = request.args.get('initiale', '').upper()
        
        # Requête de base
        query = session.query(MotKabye)
        
        # Filtrer par initiale si spécifiée
        if initiale and len(initiale) == 1:
            query = query.filter(MotKabye.mot_kabye.startswith(initiale))
        
        # Filtrer par terme de recherche si spécifié
        if terme_recherche:
            if champ_recherche in ['tous', 'kabye']:
                query = query.filter(
                    or_(
                        MotKabye.mot_kabye.ilike(f'%{terme_recherche}%'),
                        MotKabye.variantes_orthographiques.ilike(f'%{terme_recherche}%')
                    )
                )
            elif champ_recherche in ['tous', 'francais']:
                query = query.filter(
                    or_(
                        MotKabye.traduction_francaise.ilike(f'%{terme_recherche}%'),
                        MotKabye.sens_multiple.ilike(f'%{terme_recherche}%')
                    )
                )
        
        # Trier par date de modification
        mots = query.order_by(MotKabye.date_modification.desc()).all()
        
        # Convertir pour l'affichage
        mots_affichage = []
        for mot in mots:
            mots_affichage.append({
                'id': mot.id,
                'mot_kabye': mot.mot_kabye,
                'api': mot.api,
                'traduction_francaise': mot.traduction_francaise,
                'exemple_usage': mot.exemple_usage,
                'verifie_par': mot.verifie_par,
                'categorie_grammaticale': mot.categorie_grammaticale,
                'date_modification': mot.date_modification.strftime("%Y-%m-%d %H:%M:%S") if mot.date_modification else '',
                'image_url': mot.image_url
            })
        
        return render_template('liste_mots.html', 
                             mots=mots_affichage, 
                             terme_recherche=terme_recherche,
                             nombre_resultats=len(mots_affichage),
                             champ_recherche=champ_recherche,
                             initiale_recherche=initiale)
    finally:
        session.close()

@app.route('/api/mots')
def api_mots():
    """API pour récupérer les mots en JSON"""
    session = get_session()
    try:
        mots = session.query(MotKabye).all()
        result = []
        for mot in mots:
            result.append({
                'id': mot.id,
                'mot_kabye': mot.mot_kabye,
                'variantes_orthographiques': json_to_list(mot.variantes_orthographiques),
                'api': mot.api,
                'traduction_francaise': mot.traduction_francaise,
                'sens_multiple': json_to_list(mot.sens_multiple),
                'synonymes': json_to_list(mot.synonymes),
                'categorie_grammaticale': mot.categorie_grammaticale,
                'sous_categorie': mot.sous_categorie,
                'origine_mot': mot.origine_mot,
                'exemple_usage': mot.exemple_usage,
                'traduction_exemple': mot.traduction_exemple,
                'expressions_associees': json_to_list(mot.expressions_associees),
                'notes_usage': mot.notes_usage,
                'image_url': mot.image_url,
                'verifie_par': mot.verifie_par,
                'date_ajout': mot.date_ajout.strftime("%Y-%m-%d %H:%M:%S") if mot.date_ajout else '',
                'date_modification': mot.date_modification.strftime("%Y-%m-%d %H:%M:%S") if mot.date_modification else ''
            })
        return jsonify(result)
    finally:
        session.close()

@app.route('/api/mot/<int:mot_id>')
def api_mot_detail(mot_id):
    """API pour récupérer un mot spécifique en JSON"""
    session = get_session()
    try:
        mot = session.query(MotKabye).filter(MotKabye.id == mot_id).first()
        if mot:
            result = {
                'id': mot.id,
                'mot_kabye': mot.mot_kabye,
                'variantes_orthographiques': json_to_list(mot.variantes_orthographiques),
                'api': mot.api,
                'traduction_francaise': mot.traduction_francaise,
                'sens_multiple': json_to_list(mot.sens_multiple),
                'synonymes': json_to_list(mot.synonymes),
                'categorie_grammaticale': mot.categorie_grammaticale,
                'sous_categorie': mot.sous_categorie,
                'origine_mot': mot.origine_mot,
                'exemple_usage': mot.exemple_usage,
                'traduction_exemple': mot.traduction_exemple,
                'expressions_associees': json_to_list(mot.expressions_associees),
                'notes_usage': mot.notes_usage,
                'image_url': mot.image_url,
                'verifie_par': mot.verifie_par,
                'date_ajout': mot.date_ajout.strftime("%Y-%m-%d %H:%M:%S") if mot.date_ajout else '',
                'date_modification': mot.date_modification.strftime("%Y-%m-%d %H:%M:%S") if mot.date_modification else ''
            }
            return jsonify(result)
        else:
            return jsonify({'error': 'Mot non trouvé'}), 404
    finally:
        session.close()

def calculer_statistiques(mots):
    """Calculer les statistiques par personne"""
    stats_par_personne = {}
    
    for mot in mots:
        verifie_par = mot.verifie_par or 'Non spécifié'
        
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
        categorie = mot.categorie_grammaticale or 'Non spécifiée'
        stats_par_personne[verifie_par]['categories'][categorie] = \
            stats_par_personne[verifie_par]['categories'].get(categorie, 0) + 1
        
        # Traiter les dates
        date_ajout = mot.date_ajout
        if date_ajout:
            mois_annee = date_ajout.strftime("%Y-%m")
            
            # Statistiques par mois
            stats_par_personne[verifie_par]['mots_par_mois'][mois_annee] = \
                stats_par_personne[verifie_par]['mots_par_mois'].get(mois_annee, 0) + 1
            
            # Dernière activité
            if not stats_par_personne[verifie_par]['derniere_activite'] or \
               date_ajout > datetime.strptime(stats_par_personne[verifie_par]['derniere_activite'], "%Y-%m-%d %H:%M:%S"):
                stats_par_personne[verifie_par]['derniere_activite'] = date_ajout.strftime("%Y-%m-%d %H:%M:%S")
    
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

@app.route('/statistiques')
def statistiques():
    """Page de statistiques des contributions"""
    return render_template('statistiques.html')

@app.route('/api/statistiques')
def api_statistiques():
    """API pour récupérer les données statistiques"""
    session = get_session()
    try:
        mots = session.query(MotKabye).all()
        stats = calculer_statistiques(mots)
        return jsonify(stats)
    finally:
        session.close()

@app.route('/api/maintenance')
def api_maintenance():
    """API pour récupérer les informations de maintenance"""
    return jsonify(get_maintenance_info())

@app.route('/sante')
def sante():
    """Route de santé"""
    session = get_session()
    try:
        total_mots = session.query(MotKabye).count()
        return jsonify({
            'status': 'OK',
            'message': 'Dictionnaire Kabyè en ligne',
            'timestamp': datetime.now().isoformat(),
            'total_mots': total_mots
        })
    finally:
        session.close()

if __name__ == '__main__':
    # Initialisation au premier démarrage
    initialiser_donnees()
    
    # Démarrer en mode production
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)