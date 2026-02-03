import json
import re
import os
import glob
from bs4 import BeautifulSoup

def clean_text(text):
    """Fonction utilitaire pour nettoyer le texte (espaces, retours ligne)."""
    if not text:
        return ""
    # Enlever les balises crochets souvent ajoutées par Celcat (ex: [VET3])
    text = re.sub(r'\s*\[.*?\]', '', text) 
    return text.strip()

def extract_celcat_data(html_content):
    """
    Extrait les événements d'une page HTML et retourne une LISTE de dictionnaires.
    (Modification: ne retourne plus un json.dumps string, mais l'objet liste direct)
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    events_list = []

    # 1. Récupérer les dates des colonnes
    date_headers = soup.select('th.fc-day-header')
    dates_map = {} 
    
    for index, header in enumerate(date_headers):
        date_val = header.get('data-date')
        if date_val:
            dates_map[index] = date_val

    # 2. Localiser la grille des événements
    content_cols = soup.select('.fc-time-grid .fc-content-skeleton td')
    
    current_col_index = 0
    
    for td in content_cols:
        # Vérifier si c'est une colonne de jour
        if not td.find('div', class_='fc-event-container'):
            continue
            
        if current_col_index not in dates_map:
            current_col_index += 1
            continue
            
        current_date = dates_map[current_col_index]
        
        events = td.select('a.fc-time-grid-event')
        
        for event in events:
            event_data = {}
            
            # --- Extraction de l'heure ---
            time_div = event.find('div', class_='fc-time')
            if time_div and time_div.has_attr('data-full'):
                time_range = time_div['data-full']
                times = time_range.split('-')
                event_data['date'] = current_date
                event_data['start_time'] = times[0].strip()
                event_data['end_time'] = times[1].strip() if len(times) > 1 else ""
            
            # --- Extraction du contenu textuel ---
            content_div = event.find('div', class_='fc-content')
            if content_div:
                lines = [s for s in content_div.strings if s.strip() and not re.match(r'\d{2}:\d{2}', s)]
                
                if lines and re.search(r'\d{2}:\d{2}', lines[0]):
                    lines.pop(0)

                if len(lines) >= 1:
                    event_data['title'] = clean_text(lines[0])
                
                if len(lines) >= 2:
                    raw_course = clean_text(lines[1])
                    match = re.match(r'^([\w\d]+)\s+(.*)', raw_course)
                    if match:
                        event_data['course_code'] = match.group(1)
                        event_data['course_name'] = match.group(2)
                    else:
                        event_data['course_code'] = ""
                        event_data['course_name'] = raw_course

                if len(lines) >= 3:
                    event_data['location'] = clean_text(lines[2])
                
                if len(lines) >= 4:
                    event_data['teacher'] = clean_text(lines[3])
                
                if len(lines) >= 5:
                    event_data['type'] = clean_text(lines[4])

                if len(lines) >= 6:
                    raw_groups = " ".join(lines[5:])
                    cleaned_groups = clean_text(raw_groups)
                    event_data['groups'] = [cleaned_groups]

            events_list.append(event_data)
        
        current_col_index += 1

    return events_list

# --- Exécution Principale ---

def main():
    # Configuration des dossiers (basé sur ta capture d'écran)
    input_folder = 'archives_html' 
    output_file = 'emploi_du_temps_complet.json'
    
    # Liste globale qui contiendra tous les cours de toutes les semaines
    all_weeks_data = []

    # Trouver tous les fichiers html qui commencent par "week_" dans le dossier
    # Le pattern correspond à archives_html/week_*.html
    search_pattern = os.path.join(input_folder, "week_*.html")
    files = glob.glob(search_pattern)
    
    # Trier les fichiers pour les traiter dans l'ordre chronologique (optionnel mais propre)
    files.sort()

    print(f"Traitement de {len(files)} fichiers trouvés dans '{input_folder}'...")

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extraction des données pour ce fichier spécifique
            week_events = extract_celcat_data(html_content)
            
            # Ajout à la liste globale
            all_weeks_data.extend(week_events)
            
            print(f" -> {os.path.basename(file_path)} : {len(week_events)} événements extraits.")
            
        except Exception as e:
            print(f"ERREUR sur le fichier {file_path}: {e}")

    # (Optionnel) Trier tous les événements par date et heure pour que le JSON final soit propre
    # On trie par date (clé 'date') puis par heure (clé 'start_time')
    all_weeks_data.sort(key=lambda x: (x.get('date', ''), x.get('start_time', '')))

    # Sauvegarde finale
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_weeks_data, f, indent=4, ensure_ascii=False)

    print(f"\nTerminé ! {len(all_weeks_data)} événements totaux sauvegardés dans '{output_file}'.")

if __name__ == "__main__":
    main()
