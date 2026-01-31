import json
import re
from bs4 import BeautifulSoup

def clean_text(text):
    """Fonction utilitaire pour nettoyer le texte (espaces, retours ligne)."""
    if not text:
        return ""
    # Enlever les balises crochets souvent ajoutées par Celcat (ex: [VET3])
    text = re.sub(r'\s*\[.*?\]', '', text) 
    return text.strip()

def extract_celcat_to_json(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    events_list = []

    # 1. Récupérer les dates des colonnes (Lundi, Mardi, etc.)
    # Les en-têtes contiennent l'attribut 'data-date' (ex: "2026-01-26")
    date_headers = soup.select('th.fc-day-header')
    dates_map = {} # Dictionnaire index_colonne -> date string
    
    for index, header in enumerate(date_headers):
        date_val = header.get('data-date')
        if date_val:
            dates_map[index] = date_val

    # 2. Localiser la grille des événements
    # Dans FullCalendar, les événements sont dans 'fc-content-skeleton' à l'intérieur du 'fc-time-grid'
    # La première colonne (index 0) est souvent l'axe des heures, donc les jours commencent après.
    
    # On cherche les colonnes de contenu
    content_cols = soup.select('.fc-time-grid .fc-content-skeleton td')
    
    # On saute la première colonne qui sert d'axe (si elle ne contient pas d'événements)
    # L'index des dates_map est aligné avec les colonnes de données.
    
    current_col_index = 0
    
    for td in content_cols:
        # Vérifier si c'est une colonne de jour (contient généralement des event-container)
        if not td.find('div', class_='fc-event-container'):
            continue
            
        # Récupérer la date associée à cette colonne
        # Note: Parfois l'axe des heures décale l'index, on s'assure d'avoir une date
        if current_col_index not in dates_map:
            current_col_index += 1
            continue
            
        current_date = dates_map[current_col_index]
        
        # Trouver tous les événements dans cette colonne
        events = td.select('a.fc-time-grid-event')
        
        for event in events:
            event_data = {}
            
            # --- Extraction de l'heure ---
            # Trouvé dans <div class="fc-time" data-full="08:35 - 10:30">
            time_div = event.find('div', class_='fc-time')
            if time_div and time_div.has_attr('data-full'):
                time_range = time_div['data-full'] # ex: "08:35 - 10:30"
                times = time_range.split('-')
                event_data['date'] = current_date
                event_data['start_time'] = times[0].strip()
                event_data['end_time'] = times[1].strip() if len(times) > 1 else ""
            
            # --- Extraction du contenu textuel ---
            # Le contenu est dans <div class="fc-content"> séparé par des <br>
            # Structure typique CELCAT observée dans ton fichier :
            # 1. Heure (déjà traitée)
            # 2. Titre (ex: TD1 Physiopath RESPIRATOIRE)
            # 3. Matière (Code + Nom)
            # 4. Salle
            # 5. Professeur
            # 6. Type (CM/TD)
            # 7. Groupes
            
            content_div = event.find('div', class_='fc-content')
            if content_div:
                # On utilise .strings pour récupérer les noeuds textes séparés
                # On filtre les textes vides ou qui sont juste l'heure affichée
                lines = [s for s in content_div.strings if s.strip() and not re.match(r'\d{2}:\d{2}', s)]
                
                # Mapping basé sur la position (heuristique standard Celcat)
                # Note: lines[0] est souvent l'heure affichée visuellement (ex "08:35 - 10:30"), on doit l'ignorer si déjà prise
                
                # Nettoyage de la liste pour enlever l'heure si elle apparait en premier texte
                if lines and re.search(r'\d{2}:\d{2}', lines[0]):
                    lines.pop(0)

                if len(lines) >= 1:
                    event_data['title'] = clean_text(lines[0])
                
                if len(lines) >= 2:
                    raw_course = clean_text(lines[1])
                    # Séparer le code (ex: 066) du nom
                    # Regex: Cherche le premier mot (chiffres/lettres) puis le reste
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
                    # Les groupes peuvent être sur plusieurs lignes ou une seule
                    raw_groups = " ".join(lines[5:])
                    # Nettoyer les doublons [Entre crochets] et séparer si besoin
                    cleaned_groups = clean_text(raw_groups)
                    # Si plusieurs groupes, on les met dans une liste
                    event_data['groups'] = [cleaned_groups] # Simplification, ou split sur "," si besoin

            events_list.append(event_data)
        
        current_col_index += 1

    return json.dumps(events_list, indent=4, ensure_ascii=False)

# --- Exécution ---

# 1. Lire le fichier local
file_path = 'celcat_page_week.html' # Assure-toi que le fichier est dans le même dossier
with open(file_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

# 2. Convertir
json_output = extract_celcat_to_json(html_content)

# 3. Afficher ou sauvegarder
print(json_output)

# Pour sauvegarder dans un fichier :
with open('celcat_data.json', 'w', encoding='utf-8') as f:
    f.write(json_output)