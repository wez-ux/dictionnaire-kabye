import json
from datetime import datetime
from pathlib import Path

from database import get_session, MotKabye


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def migrer_json_vers_db():
    BASE_DIR = Path(__file__).resolve().parent
    DATA_FILE = BASE_DIR / "data" / "mots_kabye.json"

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    session = get_session()
    ajoutés = 0
    ignorés = 0

    try:
        for mot in data["mots"]:
            # Vérification d'existence
            existe = session.query(MotKabye).filter_by(
                mot_kabye=mot["mot_kabye"],
                traduction_francaise=mot["traduction_francaise"]
            ).first()

            if existe:
                ignorés += 1
                continue

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
                verifie_par=mot.get("verifie_par", "Anonyme"),
                date_ajout=parse_date(mot.get("date_ajout")) or datetime.now(),
                date_modification=parse_date(mot.get("date_modification")) or datetime.now(),

                # Nouveaux champs
                statut_validation="en_attente",
                notes_validation=None,
                date_validation=None
            )

            session.add(nouveau)
            ajoutés += 1

        session.commit()
        print(f"✅ Migration terminée")
        print(f"➕ Ajoutés : {ajoutés}")
        print(f"⏭️ Ignorés (déjà existants) : {ignorés}")

    except Exception as e:
        session.rollback()
        print(f"❌ Erreur : {e}")
    finally:
        session.close()


if __name__ == "__main__":
    migrer_json_vers_db()
