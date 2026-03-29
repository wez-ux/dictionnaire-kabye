import json
from datetime import datetime
from pathlib import Path

from database import get_session, MotFrancais


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None


def migrer_json_francais_vers_db():
    BASE_DIR = Path(__file__).resolve().parent
    DATA_FILE = BASE_DIR / "data" / "mots_francais.json"

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    session = get_session()
    ajoutes = 0
    ignores = 0

    try:
        for mot in data:

            # 🔒 Sécurité minimale
            if "mot_francais" not in mot or "traduction_kabye" not in mot:
                continue

            # 🔍 Vérifier doublon
            existe = session.query(MotFrancais).filter_by(
                mot_francais=mot["mot_francais"]
            ).first()

            if existe:
                ignores += 1
                print(f"⏭️ Déjà existant : {mot['mot_francais']} (id={existe.id})")
                continue

            # 🧠 Conversion JSON → string (comme ta DB)
            def to_json(value):
                return json.dumps(value or [], ensure_ascii=False)

            # ✨ Création
            nouveau = MotFrancais(
                mot_francais=mot["mot_francais"],
                variantes_orthographiques=to_json(mot.get("variantes_orthographiques")),
                traduction_kabye=mot["traduction_kabye"],
                sens_multiple=to_json(mot.get("sens_multiple")),
                synonymes=to_json(mot.get("synonymes")),
                antonymes=to_json(mot.get("antonymes")),
                categorie_grammaticale=mot.get("categorie_grammaticale"),
                sous_categorie=mot.get("sous_categorie"),
                exemple_usage=mot.get("exemple_usage"),
                traduction_exemple=mot.get("traduction_exemple"),
                expressions_associees=to_json(mot.get("expressions_associees")),
                notes_usage=mot.get("notes_usage"),
                image_url=mot.get("image_url"),
                verifie_par=mot.get("verifie_par", "Anonyme"),

                # 📅 Dates
                date_ajout=parse_date(mot.get("date_ajout")) or datetime.now(),
                date_modification=parse_date(mot.get("date_modification")) or datetime.now(),

                # ✅ VALIDATION (NOUVEAU)
                statut_validation=mot.get("statut_validation") or "en_attente",
                notes_validation=mot.get("notes_validation") or "",
                date_validation=parse_date(mot.get("date_validation")) or datetime.now()
            )

            session.add(nouveau)
            ajoutes += 1

        session.commit()

        print("\n✅ Migration terminée")
        print(f"➕ Ajoutés : {ajoutes}")
        print(f"⏭️ Ignorés : {ignores}")

    except Exception as e:
        session.rollback()
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()


if __name__ == "__main__":
    migrer_json_francais_vers_db()