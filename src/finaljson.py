import json
import re
import os
import glob
from datetime import datetime
from bs4 import BeautifulSoup

def clean_text(text):
    """Fonction utilitaire pour nettoyer le texte (espaces, retours ligne)."""
    if not text:
        return ""
    # Enlever les balises crochets souvent ajoutées par Celcat (ex: [VET3])
    text = re.sub(r'\s*\[.*?\]', '', text) 
    return text.strip()

def convert_to_24h(time_str):
    """
    Convertit une chaîne d'heure (9:00 AM, 2:00 PM ou 14:00) au format 24h (HH:MM).
    """
    if not time_str:
        return ""
    time_str = time_str.strip()
    # Essayer différents formats (Anglais AM/PM ou Français 24h)
    formats = ['%I:%M %p', '%I:%M%p', '%H:%M']
    
    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            return dt.strftime('%H:%M')
        except ValueError:
            continue
    return time_str  # Retourne l'original si conversion impossible

def extract_celcat_data(html_content):
    """
    Extrait les événements d'une page HTML et retourne une LISTE de dictionnaires.
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
            
            # --- Extraction de l'heure (et conversion format Français) ---
            time_div = event.find('div', class_='fc-time')
            if time_div and time_div.has_attr('data-full'):
                time_range = time_div['data-full']
                times = time_range.split('-')
                event_data['date'] = current_date
                # Conversion explicite en 24h (ex: 2:00 PM -> 14:00)
                event_data['start_time'] = convert_to_24h(times[0])
                event_data['end_time'] = convert_to_24h(times[1]) if len(times) > 1 else ""
            
            # --- Extraction du contenu textuel ---
            content_div = event.find('div', class_='fc-content')
            if content_div:
                # On récupère toutes les chaînes de caractères brutes
                raw_lines = [s.strip() for s in content_div.stripped_strings if s.strip()]
                
                lines = []
                for line in raw_lines:
                    # REGEX CRITIQUE : Ignore les lignes qui ne sont que des horaires
                    # Ex: "9:00 AM", "14:00", "8:30 AM - 5:00 PM"
                    # Cela empêche le décalage des données quand l'heure est affichée dans le texte
                    if re.match(r'^\d{1,2}:\d{2}(\s*[AaPp][Mm])?(\s*-\s*\d{1,2}:\d{2}(\s*[AaPp][Mm])?)?$', line):
                        continue
                    lines.append(line)

                # Maintenant que les lignes d'heures sont filtrées, l'ordre est rétabli
                if len(lines) >= 1:
                    event_data['title'] = clean_text(lines[0])
                
                if len(lines) >= 2:
                    raw_course = clean_text(lines[1])
                    # Tente de séparer Code et Nom (ex: "065 Anglais")
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
                    # Regroupe tout le reste comme "groupes"
                    event_data['groups'] = [clean_text(l) for l in lines[5:]]

            events_list.append(event_data)
            
        current_col_index += 1

    return events_list

# --- Bloc principal (inchangé sauf appels) ---
if __name__ == "__main__":
    input_folder = "archives_html"
    output_file = "emploi_du_temps_complet.json"
    
    all_weeks_data = []
    
    if not os.path.exists(input_folder):
        print(f"Le dossier '{input_folder}' n'existe pas.")
        exit(1)

    search_pattern = os.path.join(input_folder, "week_*.html")
    files = glob.glob(search_pattern)
    files.sort()

    print(f"Traitement de {len(files)} fichiers trouvés dans '{input_folder}'...")

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            week_events = extract_celcat_data(html_content)
            all_weeks_data.extend(week_events)
            
            print(f" -> {os.path.basename(file_path)} : {len(week_events)} événements extraits.")
            
        except Exception as e:
            print(f"ERREUR sur le fichier {file_path}: {e}")

    # Tri par date et heure
    all_weeks_data.sort(key=lambda x: (x.get('date', ''), x.get('start_time', '')))

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_weeks_data, f, ensure_ascii=False, indent=4)

    print(f"Extraction terminée ! Données sauvegardées dans '{output_file}'.")
