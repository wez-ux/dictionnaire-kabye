

from flask import Blueprint, redirect, render_template, jsonify, request, url_for
from database import get_session, MotKabye
from datetime import datetime
import json

validation_bp = Blueprint('validation', __name__)

def json_to_list(data):
    """Convertir les données JSON stockées en liste"""
    if not data:
        return []
    try:
        if isinstance(data, list):
            return data
        return json.loads(data)
    except json.JSONDecodeError:
        if isinstance(data, str):
            if ';' in data:
                return [item.strip() for item in data.split(';') if item.strip()]
            return [data.strip()] if data.strip() else []
        return []

def colonnes_existantes(db_session):
    """Vérifier si les colonnes de validation existent dans la table"""
    try:
        # Tester plusieurs colonnes pour être sûr
        test = db_session.query(
            MotKabye.id,
            MotKabye.statut_validation,
            MotKabye.notes_validation,
            MotKabye.date_validation
        ).limit(1).first()
        return True
    except Exception as e:
        error_str = str(e).lower()
        if 'no such column' in error_str or 'has no attribute' in error_str or 'unrecognized column' in error_str:
            print(f"Colonnes de validation non trouvées: {e}")
            return False
        # Pour d'autres erreurs (connexion, etc.), on relève
        raise e


# Définir la liste des validateurs autorisés
VALIDATEURS_AUTORISES = {
    'Benjamin': {'role': 'expert', 'nom_complet': 'Benjamin Officiel'},
    'Expert': {'role': 'expert', 'nom_complet': 'Expert Kabyè'},
    'Test': {'role': 'validateur', 'nom_complet': 'Testeur'}
}

def is_validateur_autorise(nom_validateur, role=None):
    """Vérifier si le validateur est autorisé"""
    if nom_validateur in VALIDATEURS_AUTORISES:
        if role is None or VALIDATEURS_AUTORISES[nom_validateur]['role'] == role:
            return True
    return False


@validation_bp.route('/')
def interface_validation():
    """Interface principale - Vérifie le paramètre validateur"""
    validateur = request.args.get('validateur')
    
    if not validateur:
        # Si pas de paramètre, rediriger vers le login
        return redirect(url_for('validation.login_page'))
    
    # Vérifier si le validateur est autorisé
    if not is_validateur_autorise(validateur):
        # Rediriger vers le login avec un message d'erreur
        return redirect(url_for('validation.login_page') + '?error=unauthorized')
    
    role = VALIDATEURS_AUTORISES[validateur]['role']
    
    return render_template('validation.html', 
                         validateur_nom=validateur,
                         validateur_role=role)


@validation_bp.route('/login')
def login_page():
    """Page de connexion avec vérification"""
    error = request.args.get('error')
    return render_template('login.html', error=error)

@validation_bp.route('/logout')
def logout():
    """Déconnexion - Redirige vers le login"""
    return redirect(url_for('validation.login_page'))

@validation_bp.route('/api/mots-a-valider')
def mots_a_valider():
    """Récupérer les mots à valider avec filtres"""
    # Récupérer les paramètres
    validateur = request.args.get('validateur', '')
    statut_filter = request.args.get('statut', 'tous')
    search_filter = request.args.get('search', '')
    lettre_filter = request.args.get('lettre', '')  # Nouveau paramètre
    
    # Si pas dans les paramètres, essayer de le déduire de l'URL de référence
    if not validateur:
        referrer = request.headers.get('Referer', '')
        if referrer:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(referrer)
            params = parse_qs(parsed.query)
            validateur = params.get('validateur', [''])[0]
    
    # Vérifier l'accès
    if not is_validateur_autorise(validateur):
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    db_session = get_session()
    
    try:
        # Liste des lettres spéciales autorisées
        lettres_speciales = ['b', 'c', 'd', 'ɖ', 'f', 'g', 'h', 'j', 'k', 'kp', 'l', 'm', 'n', 
                           'ñ', 'ŋ', 'p', 's', 't', 'w', 'y', 'a', 'e', 'ɛ', 'i', 'o', 'ɔ', 'u', 'ɩ']
        
        # Vérifier si les colonnes de validation existent
        if not colonnes_existantes(db_session):
            # Mode ancienne base de données (sans colonnes de validation)
            query = db_session.query(MotKabye)
            
            # Appliquer le filtre par lettre initiale
            if lettre_filter and lettre_filter in lettres_speciales:
                # Pour 'kp' qui a deux caractères
                if lettre_filter == 'kp':
                    query = query.filter(MotKabye.mot_kabye.ilike('kp%'))
                else:
                    query = query.filter(MotKabye.mot_kabye.ilike(f'{lettre_filter}%'))
            
            # Appliquer la recherche textuelle
            if search_filter:
                search = f"%{search_filter}%"
                query = query.filter(
                    (MotKabye.mot_kabye.ilike(search)) |
                    (MotKabye.traduction_francaise.ilike(search)) |
                    (MotKabye.exemple_usage.ilike(search))
                )
            
            # Appliquer le filtre de statut simplifié
            if statut_filter == 'valide':
                query = query.filter(MotKabye.verifie_par != None)
            elif statut_filter == 'en_attente':
                query = query.filter(MotKabye.verifie_par == None)
            # Pour 'tous', 'a_reviser', 'rejete' - pas de filtre car non supportés
            
            mots = query.order_by(MotKabye.mot_kabye.asc(), MotKabye.date_ajout.asc()).all()
            
            result = []
            for mot in mots:
                statut = 'valide' if mot.verifie_par else 'en_attente'
                
                # Si on filtre par 'a_reviser' ou 'rejete' et qu'on est dans l'ancien schéma,
                # ces statuts n'existent pas, donc on peut retourner une liste vide
                if statut_filter in ['a_reviser', 'rejete'] and statut != statut_filter:
                    continue
                
                result.append({
                    'id': mot.id,
                    'mot_kabye': mot.mot_kabye,
                    'api': mot.api or '',
                    'traduction_francaise': mot.traduction_francaise,
                    'sens_multiple': json_to_list(mot.sens_multiple),
                    'exemple_usage': mot.exemple_usage or '',
                    'traduction_exemple': mot.traduction_exemple or '',
                    'categorie_grammaticale': mot.categorie_grammaticale or '',
                    'statut_validation': statut,
                    'notes_validation': '',
                    'verifie_par': mot.verifie_par or '',
                    'date_validation': mot.date_modification.strftime("%Y-%m-%d") if mot.date_modification else ''
                })
            return jsonify(result)
        
        # Mode nouvelle base de données (avec colonnes de validation)
        query = db_session.query(MotKabye)
        
        # Appliquer le filtre par lettre initiale
        if lettre_filter and lettre_filter in lettres_speciales:
            # Pour 'kp' qui a deux caractères
            if lettre_filter == 'kp':
                query = query.filter(MotKabye.mot_kabye.ilike('kp%'))
            else:
                query = query.filter(MotKabye.mot_kabye.ilike(f'{lettre_filter}%'))
        
        # Appliquer les filtres de statut
        if statut_filter != 'tous':
            if statut_filter == 'en_attente':
                query = query.filter(
                    (MotKabye.statut_validation == 'en_attente') | 
                    (MotKabye.statut_validation == None) |
                    (MotKabye.statut_validation == '')
                )
            elif statut_filter == 'valide':
                query = query.filter(MotKabye.statut_validation == 'valide')
            elif statut_filter == 'a_reviser':
                query = query.filter(MotKabye.statut_validation == 'a_reviser')
            elif statut_filter == 'rejete':
                query = query.filter(MotKabye.statut_validation == 'rejete')
        
        # Appliquer la recherche
        if search_filter:
            search = f"%{search_filter}%"
            query = query.filter(
                (MotKabye.mot_kabye.ilike(search)) |
                (MotKabye.traduction_francaise.ilike(search)) |
                (MotKabye.exemple_usage.ilike(search)) |
                (MotKabye.api.ilike(search))
            )
        
        # Pour le filtre 'tous', on montre tous les mots
        # (pas de filtre supplémentaire)
        
        mots = query.order_by(MotKabye.mot_kabye.asc(), MotKabye.date_ajout.asc()).all()
        
        result = []
        for mot in mots:
            result.append({
                'id': mot.id,
                'mot_kabye': mot.mot_kabye,
                'api': mot.api or '',
                'traduction_francaise': mot.traduction_francaise,
                'sens_multiple': json_to_list(mot.sens_multiple),
                'exemple_usage': mot.exemple_usage or '',
                'traduction_exemple': mot.traduction_exemple or '',
                'categorie_grammaticale': mot.categorie_grammaticale or '',
                'statut_validation': mot.statut_validation or 'en_attente',
                'notes_validation': mot.notes_validation or '',
                'verifie_par': mot.verifie_par or '',
                'date_validation': mot.date_validation.strftime("%Y-%m-%d") if mot.date_validation else ''
            })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Erreur dans mots_a_valider: {e}")
        return jsonify({'error': str(e), 'details': 'Erreur serveur lors du filtrage'}), 500
    finally:
        db_session.close()


@validation_bp.route('/api/mot/<int:mot_id>')
def get_mot_detail(mot_id):
    """Récupérer les détails complets d'un mot avec formatage JSON"""
    db_session = get_session()
    try:
        mot = db_session.query(MotKabye).filter(MotKabye.id == mot_id).first()
        if mot:
            # Fonction pour formater les champs JSON
            def formater_champ_json(data, champ_name):
                valeur = getattr(mot, champ_name, '')
                if not valeur:
                    return []
                try:
                    if isinstance(valeur, str):
                        return json.loads(valeur)
                    elif isinstance(valeur, list):
                        return valeur
                    else:
                        return []
                except json.JSONDecodeError:
                    # Si ce n'est pas du JSON valide, traiter comme texte simple
                    if ';' in valeur:
                        return [item.strip() for item in valeur.split(';') if item.strip()]
                    return [valeur.strip()] if valeur.strip() else []
            
            # Formater les expressions associées
            expressions = formater_champ_json(mot.expressions_associees, 'expressions_associees')
            # Si expressions est une liste de strings, convertir en liste de dicts
            expressions_formatees = []
            for expr in expressions:
                if isinstance(expr, dict):
                    expressions_formatees.append(expr)
                elif isinstance(expr, str):
                    # Essayer de parser "expression: traduction"
                    if ':' in expr:
                        parts = expr.split(':', 1)
                        expressions_formatees.append({
                            'expression': parts[0].strip(),
                            'traduction': parts[1].strip() if len(parts) > 1 else ''
                        })
                    else:
                        expressions_formatees.append({
                            'expression': expr.strip(),
                            'traduction': ''
                        })
            
            result = {
                'id': mot.id,
                'mot_kabye': mot.mot_kabye or '',
                'variantes_orthographiques': formater_champ_json(mot.variantes_orthographiques, 'variantes_orthographiques'),
                'api': mot.api or '',
                'traduction_francaise': mot.traduction_francaise or '',
                'sens_multiple': formater_champ_json(mot.sens_multiple, 'sens_multiple'),
                'synonymes': formater_champ_json(mot.synonymes, 'synonymes'),
                'categorie_grammaticale': mot.categorie_grammaticale or '',
                'sous_categorie': mot.sous_categorie or '',
                'origine_mot': mot.origine_mot or '',
                'exemple_usage': mot.exemple_usage or '',
                'traduction_exemple': mot.traduction_exemple or '',
                'expressions_associees': expressions_formatees,
                'notes_usage': mot.notes_usage or '',
                'image_url': mot.image_url or '',
                'statut_validation': mot.statut_validation or 'en_attente',
                'notes_validation': mot.notes_validation or '',
                'verifie_par': mot.verifie_par or '',
                'date_validation': mot.date_validation.strftime("%Y-%m-%d") if mot.date_validation else ''
            }
            return jsonify(result)
        else:
            return jsonify({'error': 'Mot non trouvé'}), 404
    except Exception as e:
        print(f"Erreur dans get_mot_detail: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@validation_bp.route('/api/valider/<int:mot_id>', methods=['POST'])
def valider_mot(mot_id):
    """Valider ou rejeter un mot avec toutes les modifications"""
    data = request.get_json()
    validateur = data.get('validateur', '')
    
    # Vérifier l'accès
    if not is_validateur_autorise(validateur):
        return jsonify({'success': False, 'error': 'Accès non autorisé'}), 403
    
    db_session = get_session()
    
    try:
        mot = db_session.query(MotKabye).filter(MotKabye.id == mot_id).first()
        if not mot:
            return jsonify({'success': False, 'error': 'Mot non trouvé'}), 404
        
        # Mettre à jour les champs de validation
        mot.verifie_par = validateur
        mot.date_modification = datetime.now()
        
        # Mettre à jour les champs de validation spécifiques
        if hasattr(mot, 'statut_validation'):
            mot.statut_validation = data.get('statut', 'valide')
            mot.notes_validation = data.get('notes', '')
            mot.date_validation = datetime.now()
        
        # Appliquer toutes les modifications
        modifications = data.get('modifications', {})
        
        # Champs textuels simples
        champs_simples = [
            'mot_kabye', 'api', 'traduction_francaise',
            'categorie_grammaticale', 'sous_categorie',
            'origine_mot', 'exemple_usage', 'traduction_exemple',
            'notes_usage', 'image_url'
        ]
        
        for champ in champs_simples:
            if champ in modifications:
                setattr(mot, champ, modifications[champ])
        
        # Champs JSON/Text (listes)
        champs_listes = [
            'variantes_orthographiques', 'sens_multiple',
            'synonymes', 'expressions_associees'
        ]
        
        for champ in champs_listes:
            if champ in modifications:
                # Convertir en JSON si c'est une liste
                valeur = modifications[champ]
                if isinstance(valeur, list):
                    setattr(mot, champ, json.dumps(valeur, ensure_ascii=False))
                else:
                    setattr(mot, champ, valeur)
        
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Mot "{mot.mot_kabye}" mis à jour avec succès',
            'statut': data.get('statut', 'valide'),
            'date_validation': mot.date_validation.strftime("%Y-%m-%d") if mot.date_validation else None
        })
        
    except Exception as e:
        db_session.rollback()
        print(f"Erreur dans valider_mot: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@validation_bp.route('/api/statistiques-validation')
def statistiques_validation():
    """Statistiques de validation"""
    db_session = get_session()
    try:
        total = db_session.query(MotKabye).count()
        
        try:
            valides = db_session.query(MotKabye).filter(MotKabye.statut_validation == 'valide').count()
            en_attente = db_session.query(MotKabye).filter(
                (MotKabye.statut_validation == 'en_attente') | 
                (MotKabye.statut_validation == None)
            ).count()
            a_reviser = db_session.query(MotKabye).filter(MotKabye.statut_validation == 'a_reviser').count()
            rejetes = db_session.query(MotKabye).filter(MotKabye.statut_validation == 'rejete').count()
        except:
            valides = db_session.query(MotKabye).filter(MotKabye.verifie_par != None).count()
            en_attente = db_session.query(MotKabye).filter(MotKabye.verifie_par == None).count()
            a_reviser = 0
            rejetes = 0
        
        pourcentage_valide = (valides / total * 100) if total > 0 else 0
        
        return jsonify({
            'total': total,
            'valides': valides,
            'en_attente': en_attente,
            'a_reviser': a_reviser,
            'rejetes': rejetes,
            'pourcentage_valide': pourcentage_valide
        })
    except Exception as e:
        print(f"Erreur dans statistiques_validation: {e}")
        return jsonify({
            'total': 0,
            'valides': 0,
            'en_attente': 0,
            'a_reviser': 0,
            'rejetes': 0,
            'pourcentage_valide': 0
        })
    finally:
        db_session.close()