from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# Configuration
DATA_DIR = Path('/home/ubuntu/dictionnaire-kabye/data')
DATA_FILE = DATA_DIR / 'mots_kabye.json'

def initialiser_donnees():
    """Créer le dossier data et le fichier JSON s'ils n'existent pas"""
    DATA_DIR.mkdir(exist_ok=True)
    
    if not DATA_FILE.exists():
        donnees_initiales = {
            "mots": [
                {
                    "id": 1,
                    "mot_kabye": "aalayu",
                    "api": "[âlâyú]",
                    "traduction_francaise": "qui sera le premier",
                    "categorie_grammaticale": "nom",
                    "exemple_usage": "Aalayu tem qui sera le premier à finir",
                    "verifie_par": "Admin",
                    "date_ajout": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                {
                    "id": 2,
                    "mot_kabye": "abaa",
                    "api": "[ábaa]",
                    "traduction_francaise": "exprime la pitié, l'innocence, l'agacement",
                    "categorie_grammaticale": "interjection",
                    "exemple_usage": "Pakpa-u hayu abaa yem",
                    "verifie_par": "Admin",
                    "date_ajout": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            ],
            "prochain_id": 3
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

@app.route('/')
def accueil():
    return render_template('formulaire.html')

@app.route('/sauvegarder', methods=['POST'])
def sauvegarder_mot():
    try:
        data = request.get_json()
        
        # Validation
        if not data.get('mot_kabye') or not data.get('traduction_francaise'):
            return jsonify({'success': False, 'error': 'Mot kabyè et traduction française sont obligatoires'})
        
        # Charger les données existantes
        donnees = charger_donnees()
        
        # Vérifier si le mot existe déjà
        mot_existe = any(mot['mot_kabye'].lower() == data['mot_kabye'].lower() 
                        for mot in donnees['mots'])
        
        if mot_existe:
            return jsonify({'success': False, 'error': 'Ce mot existe déjà dans le dictionnaire'})
        
        # Créer le nouveau mot
        nouveau_mot = {
            "id": donnees['prochain_id'],
            "mot_kabye": data['mot_kabye'].strip(),
            "api": data.get('api', '').strip(),
            "traduction_francaise": data['traduction_francaise'].strip(),
            "categorie_grammaticale": data.get('categorie_grammaticale', '').strip(),
            "exemple_usage": data.get('exemple_usage', '').strip(),
            "verifie_par": data.get('verifie_par', 'Anonyme').strip(),
            "date_ajout": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Ajouter le mot et mettre à jour l'ID
        donnees['mots'].append(nouveau_mot)
        donnees['prochain_id'] += 1
        
        # Sauvegarder
        if sauvegarder_donnees(donnees):
            return jsonify({
                'success': True, 
                'message': f'✅ Mot "{data["mot_kabye"]}" sauvegardé avec succès !'
            })
        else:
            return jsonify({'success': False, 'error': 'Erreur lors de la sauvegarde'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mots')
def liste_mots():
    """Afficher tous les mots"""
    donnees = charger_donnees()
    mots = donnees['mots']
    mots_tries = sorted(mots, key=lambda x: x['mot_kabye'])
    return render_template('liste_mots.html', mots=mots_tries)

@app.route('/api/mots')
def api_mots():
    """API pour récupérer les mots en JSON"""
    donnees = charger_donnees()
    return jsonify(donnees['mots'])

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