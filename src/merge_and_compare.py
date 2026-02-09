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

def run():
    # 1. Charger les données
    master_data = load_json(MASTER_JSON_PATH)
    new_data = load_json(NEW_DATA_PATH)

    if not new_data:
        print("Aucune nouvelle donnée scrapée.")
        # Écrit dans GITHUB_OUTPUT que rien n'a changé
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            print(f"changed=false", file=fh)
        return

    # 2. Convertir en dictionnaires pour comparaison facile (ex: clé unique = date + heure + cours)
    # Note : Cette logique dépend de la structure de ton JSON. 
    # Supposons que c'est une liste d'événements.
    
    has_changes = False
    
    # Création d'un index pour le master data pour recherche rapide
    # On suppose que chaque event a un identifiant unique ou une combinaison unique
    # Si tu n'as pas d'ID unique, on compare le contenu brut des semaines concernées.
    
    # --- LOGIQUE SIMPLIFIÉE DE COMPARAISON ---
    # On remplace les événements du master par ceux du new_data s'ils correspondent aux mêmes semaines
    
    # Pour faire simple : on va sérialiser les données pour comparer les chaînes de caractères
    # C'est brute-force mais efficace pour détecter un changement
    original_dump = json.dumps(master_data, sort_keys=True)
    
    # TODO : Ici, insère ta logique de fusion.
    # Exemple : Si new_data contient des cours, on met à jour master_data
    # Ceci est un exemple générique, adapte-le à ta structure de liste/dictionnaire
    
    # Si master_data est une liste d'événements :
    # On supprime les événements du master qui sont dans la plage de dates du new_data
    # Et on insère les new_data à la place.
    
    # (Supposons que new_data est la liste propre des 2 semaines)
    # Cette partie nécessite que tu connaisses la structure exacte de ton JSON
    # Voici une approche "Merge" basique si c'est une liste d'objets
    
    updated_master = master_data # Par défaut
    
    # --- FIN LOGIQUE ---

    # 3. Vérifier si ça a changé
    new_dump = json.dumps(updated_master, sort_keys=True)

    if original_dump != new_dump:
        print("🔄 Changements détectés !")
        has_changes = True
        
        # Sauvegarder le nouveau master
        with open(MASTER_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(updated_master, f, indent=4, ensure_ascii=False)
    else:
        print("✅ Aucun changement détecté.")

    # 4. Communiquer avec GitHub Actions
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        print(f"changed={str(has_changes).lower()}", file=fh)

if __name__ == "__main__":
    run()
