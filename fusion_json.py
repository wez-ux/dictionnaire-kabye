import json
from collections import defaultdict

# Charger les deux fichiers JSON
with open('mots_kabye_validation.json', 'r', encoding='utf-8') as f:
    data_validation = json.load(f)

with open('mots_kabye.json', 'r', encoding='utf-8') as f:
    data_kabye = json.load(f)

# Créer un dictionnaire pour accéder rapidement aux données de validation par ID
validation_data_by_id = {}

for item in data_validation:
    if 'id' in item:
        validation_data_by_id[item['id']] = {
            'statut_validation': item.get('statut_validation', 'non_disponible'),
            'date_validation': item.get('date_validation', ''),
            'notes_validation': item.get('notes_validation', ''),
            'verifie_par': item.get('verifie_par', '')
        }

# Fusionner les données
fusionnees = []

for item_kabye in data_kabye:
    item_id = item_kabye['id']
    
    # Créer une copie de l'item
    item_fusionne = item_kabye.copy()
    
    # Ajouter les champs de validation si disponibles
    if item_id in validation_data_by_id:
        validation_data = validation_data_by_id[item_id]
        item_fusionne.update(validation_data)
    else:
        # Si l'ID n'existe pas dans le fichier de validation
        item_fusionne['statut_validation'] = 'non_disponible'
        item_fusionne['date_validation'] = ''
        item_fusionne['notes_validation'] = ''
        item_fusionne['verifie_par'] = ''
    
    fusionnees.append(item_fusionne)

# Sauvegarder le résultat fusionné
with open('mots_kabye_fusionne_complet.json', 'w', encoding='utf-8') as f:
    json.dump(fusionnees, f, ensure_ascii=False, indent=2)

# Statistiques
ids_avec_validation = set(validation_data_by_id.keys())
ids_kabye = set(item['id'] for item in data_kabye)

print("=== Statistiques de fusion ===")
print(f"Entrées dans mots_kabye.json : {len(data_kabye)}")
print(f"Entrées dans mots_kabye_validation.json : {len(data_validation)}")
print(f"Entrées fusionnées : {len(fusionnees)}")
print(f"IDs correspondants : {len(ids_avec_validation & ids_kabye)}")
print(f"IDs sans statut de validation : {len(ids_kabye - ids_avec_validation)}")
print(f"Fichier sauvegardé : mots_kabye_fusionne_complet.json")