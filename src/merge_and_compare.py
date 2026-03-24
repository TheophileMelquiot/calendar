import json
import os
import sys

# Chemins des fichiers
MASTER_JSON_PATH = 'json/emploi_du_temps_complet.json'
NEW_DATA_PATH = 'temp_update.json' # Le fichier généré par ton scraper léger

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_events(data):
    """Retourne la liste d'événements que data soit un dict avec 'events' ou une liste."""
    if isinstance(data, dict):
        return data.get('events', [])
    return data

def run():
    # 1. Charger les données
    master_data = extract_events(load_json(MASTER_JSON_PATH))
    new_data = extract_events(load_json(NEW_DATA_PATH))

    if not new_data:
        print("Aucune nouvelle donnée scrapée.")
        # Écrit dans GITHUB_OUTPUT que rien n'a changé
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            print(f"changed=false", file=fh)
        return

    # 2. Snapshot de l'état original pour comparaison
    original_dump = json.dumps(master_data, sort_keys=True)

    # 3. Déterminer la plage de dates couverte par les nouvelles données
    new_dates = [e['date'] for e in new_data if e.get('date')]
    if not new_dates:
        print("Aucune date trouvée dans les nouvelles données.")
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            print(f"changed=false", file=fh)
        return

    min_date = min(new_dates)
    max_date = max(new_dates)
    print(f"Plage de mise à jour : {min_date} → {max_date}")

    # 4. Supprimer du master les événements qui tombent dans cette plage de dates
    # Events without a date are preserved (treated as outside any range)
    filtered_master = [
        e for e in master_data
        if not e.get('date') or not (min_date <= e['date'] <= max_date)
    ]

    # 5. Insérer les nouveaux événements et trier
    updated_master = filtered_master + new_data
    updated_master.sort(key=lambda x: (x.get('date', ''), x.get('start_time', '')))

    # 6. Vérifier si ça a changé
    new_dump = json.dumps(updated_master, sort_keys=True)

    has_changes = original_dump != new_dump

    if has_changes:
        print("🔄 Changements détectés !")

        # Sauvegarder le nouveau master
        os.makedirs(os.path.dirname(MASTER_JSON_PATH), exist_ok=True)
        with open(MASTER_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(updated_master, f, indent=4, ensure_ascii=False)
    else:
        print("✅ Aucun changement détecté.")

    # 7. Communiquer avec GitHub Actions
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        print(f"changed={str(has_changes).lower()}", file=fh)

if __name__ == "__main__":
    run()
