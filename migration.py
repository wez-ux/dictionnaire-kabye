# migration.py (fichier séparé)
import sqlite3
import os

def migrer_database():
    """Ajouter les colonnes manquantes"""
    db_path = 'dictionnaire.db'  
    
    if not os.path.exists(db_path):
        print(f"✗ Base de données {db_path} non trouvée")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Vérifier les colonnes existantes
        cursor.execute("PRAGMA table_info(mots_kabye)")
        colonnes = [col[1] for col in cursor.fetchall()]
        
        print("Colonnes actuelles:", colonnes)
        
        # Ajouter les colonnes manquantes
        if 'statut_validation' not in colonnes:
            cursor.execute("ALTER TABLE mots_kabye ADD COLUMN statut_validation TEXT DEFAULT 'en_attente'")
            print("✓ Colonne statut_validation ajoutée")
        
        if 'notes_validation' not in colonnes:
            cursor.execute("ALTER TABLE mots_kabye ADD COLUMN notes_validation TEXT")
            print("✓ Colonne notes_validation ajoutée")
        
        if 'date_validation' not in colonnes:
            cursor.execute("ALTER TABLE mots_kabye ADD COLUMN date_validation DATETIME")
            print("✓ Colonne date_validation ajoutée")
        
        conn.commit()
        print("✓ Migration terminée avec succès")
        return True
        
    except Exception as e:
        print(f"✗ Erreur lors de la migration: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    migrer_database()