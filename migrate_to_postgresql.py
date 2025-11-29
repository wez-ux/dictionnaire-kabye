import json
from datetime import datetime
from database import get_session, MotKabye
from pathlib import Path

def migrer_donnees_json_vers_postgresql():
    """Migrer les données du JSON vers PostgreSQL"""
    
    # Charger les données JSON existantes
    BASE_DIR = Path(__file__).resolve().parent
    DATA_FILE = BASE_DIR / "data" / "mots_kabye.json"
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        donnees = json.load(f)
    
    session = get_session()
    
    try:
        # Vérifier si la table est déjà peuplée
        count_existant = session.query(MotKabye).count()
        if count_existant > 0:
            print(f"⚠️  La base de données contient déjà {count_existant} entrées.")
            reponse = input("Voulez-vous écraser les données existantes ? (oui/non): ")
            if reponse.lower() != 'oui':
                print("Migration annulée.")
                return
        
        # Vider la table si nécessaire
        session.query(MotKabye).delete()
        
        # Migrer chaque mot
        for mot_json in donnees['mots']:
            mot_db = MotKabye(
                id=mot_json['id'],
                mot_kabye=mot_json['mot_kabye'],
                variantes_orthographiques=json.dumps(mot_json.get('variantes_orthographiques', []), ensure_ascii=False),
                api=mot_json.get('api', ''),
                traduction_francaise=mot_json['traduction_francaise'],
                sens_multiple=json.dumps(mot_json.get('sens_multiple', []), ensure_ascii=False),
                synonymes=json.dumps(mot_json.get('synonymes', []), ensure_ascii=False),
                categorie_grammaticale=mot_json.get('categorie_grammaticale', ''),
                sous_categorie=mot_json.get('sous_categorie', ''),
                origine_mot=mot_json.get('origine_mot', ''),
                exemple_usage=mot_json.get('exemple_usage', ''),
                traduction_exemple=mot_json.get('traduction_exemple', ''),
                expressions_associees=json.dumps(mot_json.get('expressions_associees', []), ensure_ascii=False),
                notes_usage=mot_json.get('notes_usage', ''),
                image_url=mot_json.get('image_url', ''),
                verifie_par=mot_json.get('verifie_par', 'Anonyme'),
                date_ajout=datetime.strptime(mot_json.get('date_ajout'), "%Y-%m-%d %H:%M:%S") if mot_json.get('date_ajout') else datetime.now(),
                date_modification=datetime.strptime(mot_json.get('date_modification'), "%Y-%m-%d %H:%M:%S") if mot_json.get('date_modification') else datetime.now()
            )
            session.add(mot_db)
        
        session.commit()
        print(f"✅ Migration réussie ! {len(donnees['mots'])} mots migrés vers PostgreSQL.")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Erreur lors de la migration : {e}")
    finally:
        session.close()

if __name__ == '__main__':
    migrer_donnees_json_vers_postgresql()