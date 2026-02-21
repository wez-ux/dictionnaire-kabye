import json
from datetime import datetime
from pathlib import Path

from database import get_session, MotKabye


def parse_date(value):
    if not value:
        return None
    try:
        # Essayer le format avec heure
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            # Essayer le format date seule
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None


def migrer_json_vers_db():
    BASE_DIR = Path(__file__).resolve().parent
    DATA_FILE = BASE_DIR / "data" / "mots_kabye.json"
    VALIDATION_FILE = BASE_DIR / "data" / "mots_kabye_validation.json"
    
    # Charger les données principales
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Charger les données de validation
    validation_data = {}
    try:
        with open(VALIDATION_FILE, "r", encoding="utf-8") as f:
            validation_list = json.load(f)
            # Créer un dictionnaire avec l'ID comme clé pour accès rapide
            for item in validation_list:
                if "id" in item:
                    # Normaliser les clés pour assurer la compatibilité
                    validation_data[item["id"]] = {
                        "statut_validation": item.get("statut_validation", "en_attente"),
                        "notes_validation": item.get("notes_validation", ""),
                        "date_validation": item.get("date_validation", None),
                        "verifie_par": item.get("verifie_par", "")
                    }
    except FileNotFoundError:
        print("⚠️ Fichier de validation non trouvé, utilisation des valeurs par défaut")
    except Exception as e:
        print(f"⚠️ Erreur lors du chargement du fichier de validation : {e}")

    session = get_session()
    ajoutés = 0
    ignorés = 0
    mis_a_jour = 0

    try:
        for mot in data:
            # Sécurité minimale
            if "mot_kabye" not in mot or "traduction_francaise" not in mot:
                continue

            # Vérifier si le mot existe déjà
            existe = session.query(MotKabye).filter_by(
                mot_kabye=mot["mot_kabye"],
                traduction_francaise=mot["traduction_francaise"]
            ).first()

            # Récupérer les données de validation pour cet ID
            mot_id = mot.get("id")
            validation_info = validation_data.get(mot_id, {})
            
            # Déterminer les valeurs par défaut ou depuis validation
            statut_val = validation_info.get("statut_validation", "en_attente")
            notes_val = validation_info.get("notes_validation", "")
            date_val = validation_info.get("date_validation")
            verifie_par_val = validation_info.get("verifie_par", mot.get("verifie_par", "Anonyme"))

            if existe:
                # Mettre à jour les champs de validation si le mot existe déjà
                if statut_val != "en_attente" and existe.statut_validation == "en_attente":
                    existe.statut_validation = statut_val
                    existe.notes_validation = notes_val
                    existe.date_validation = parse_date(date_val)
                    existe.verifie_par = verifie_par_val
                    mis_a_jour += 1
                ignorés += 1
                print(
                    f"⏭️ Déjà existant : "
                    f"{mot['mot_kabye']} → {mot['traduction_francaise']} "
                    f"(id_db={existe.id})"
                )
                continue

            # Créer un nouveau mot
            nouveau = MotKabye(
                mot_kabye=mot["mot_kabye"],
                variantes_orthographiques=json.dumps(
                    mot.get("variantes_orthographiques", []),
                    ensure_ascii=False
                ),
                api=mot.get("api"),
                traduction_francaise=mot["traduction_francaise"],
                sens_multiple=json.dumps(
                    mot.get("sens_multiple", []),
                    ensure_ascii=False
                ),
                synonymes=json.dumps(
                    mot.get("synonymes", []),
                    ensure_ascii=False
                ),
                categorie_grammaticale=mot.get("categorie_grammaticale"),
                sous_categorie=mot.get("sous_categorie"),
                origine_mot=mot.get("origine_mot"),
                exemple_usage=mot.get("exemple_usage"),
                traduction_exemple=mot.get("traduction_exemple"),
                expressions_associees=json.dumps(
                    mot.get("expressions_associees", []),
                    ensure_ascii=False
                ),
                notes_usage=mot.get("notes_usage"),
                image_url=mot.get("image_url"),
                verifie_par=verifie_par_val,
                date_ajout=parse_date(mot.get("date_ajout")) or datetime.now(),
                date_modification=parse_date(mot.get("date_modification")) or datetime.now(),
                
                # Champs de validation
                statut_validation=statut_val,
                notes_validation=notes_val,
                date_validation=parse_date(date_val)
            )

            session.add(nouveau)
            ajoutés += 1

        session.commit()
        print("✅ Migration terminée avec succès")
        print(f"➕ Nouveaux mots ajoutés : {ajoutés}")
        print(f"🔄 Mots mis à jour (validation) : {mis_a_jour}")
        print(f"⏭️ Ignorés (déjà existants) : {ignorés}")
        
        # Statistiques sur la validation
        statuts_count = {}
        if validation_data:
            for info in validation_data.values():
                statut = info.get("statut_validation", "en_attente")
                statuts_count[statut] = statuts_count.get(statut, 0) + 1
            
            print("\n📊 Statistiques de validation importées :")
            for statut, count in statuts_count.items():
                print(f"  {statut}: {count}")

    except Exception as e:
        session.rollback()
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    migrer_json_vers_db()