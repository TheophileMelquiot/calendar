import json
import re
from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
import pytz

# Configuration
INPUT_HTML_FILE = 'celcat_page_week.html'
OUTPUT_JSON_FILE = 'emploi_du_temps.json'
OUTPUT_ICS_FILE = 'emploi_du_temps.ics'
# Le fuseau horaire de VOTRE emploi du temps (France)
LOCAL_TIMEZONE = pytz.timezone("Europe/Paris")

def clean_text(text):
    """Nettoie les espaces inutiles et les caractères invisibles."""
    if not text:
        return None
    # Remplace les espaces insécables et nettoie
    text = text.replace('\xa0', ' ').strip()
    return text if text else None

def parse_html_to_json(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    events_list = []
    
    # 1. Récupération des dates (Headers)
    headers = soup.select('th.fc-day-header')
    date_map = {}
    
    # print(f"DEBUG: Nombre d'en-têtes de dates trouvés : {len(headers)}")

    for index, header in enumerate(headers):
        date_str = header.get('data-date')
        if date_str:
            date_map[index] = date_str

    # 2. Récupération de la grille
    content_skeleton = soup.select_one('.fc-time-grid .fc-content-skeleton tbody tr')
    
    if not content_skeleton:
        # Fallback si la structure est légèrement différente
        content_skeleton = soup.select_one('.fc-content-skeleton tbody tr')

    if not content_skeleton:
        return {"events": []}

    columns = content_skeleton.find_all('td')
    # On ignore la colonne des axes horaires (celle qui contient les heures à gauche)
    data_columns = [col for col in columns if 'fc-axis' not in col.get('class', [])]

    # 3. Extraction des événements
    count_events = 0
    for col_index, col in enumerate(data_columns):
        # Logique pour trouver la bonne date associée à la colonne
        current_date = None
        
        # Décalage fréquent : souvent l'index 0 des headers est l'axe, donc on tente col_index + 1
        # Sinon on tente col_index tout court.
        if (col_index) in date_map:
             current_date = date_map[col_index]
        elif (col_index + 1) in date_map: # Cas le plus courant avec FullCalendar
            current_date = date_map[col_index + 1]
            
        if not current_date:
            continue

        events = col.select('.fc-time-grid-event')
        
        for event_tag in events:
            count_events += 1
            
            # --- Extraction des heures ---
            start_time = "00:00"
            end_time = "00:00"
            
            time_div = event_tag.select_one('.fc-time')
            if time_div and 'data-full' in time_div.attrs:
                # Format attendu souvent "HH:MM - HH:MM"
                times = time_div['data-full'].split('-')
                if len(times) >= 2:
                    start_time = clean_text(times[0])
                    end_time = clean_text(times[1])
            else:
                # Fallback: essayer de lire le texte de la div time si data-full absent
                if time_div:
                    t_text = time_div.get_text()
                    parts = t_text.split('-')
                    if len(parts) >= 2:
                        start_time = clean_text(parts[0])
                        end_time = clean_text(parts[1])

            # --- Extraction du contenu ---
            content_div = event_tag.select_one('.fc-content')
            if not content_div: continue

            lines = [clean_text(s) for s in content_div.stripped_strings]
            # Filtrer les lignes vides ou redondantes
            info_lines = [line for line in lines if line and not re.search(r'\d{1,2}:\d{2}', line)]

            title = "Cours"
            course_name = ""
            location = ""
            teacher = ""
            type_cours = ""

            # Logique heuristique basée sur la position des lignes
            if len(info_lines) > 0: 
                title = info_lines[0] # Ex: [CM] Matière...
            
            if len(info_lines) > 1:
                # Souvent la ligne 2 est le nom détaillé ou le prof
                # On essaie de détecter si c'est un prof ou une salle
                if "Amphi" in info_lines[1] or "Salle" in info_lines[1] or re.search(r'\d{3}', info_lines[1]):
                    location = info_lines[1]
                else:
                    course_name = info_lines[1]

            if len(info_lines) > 2:
                if not location: location = info_lines[2]
                else: teacher = info_lines[2]
            
            if len(info_lines) > 3 and not teacher:
                teacher = info_lines[3]

            # Détection du type (CM, TD, TP) dans le titre
            if "[TD]" in title: type_cours = "TD"
            elif "[CM]" in title: type_cours = "CM"
            elif "[TP]" in title: type_cours = "TP"

            event_obj = {
                "date": current_date,
                "start_time": start_time,
                "end_time": end_time,
                "title": title,
                "course_name": course_name,
                "location": location,
                "teacher": teacher,
                "type": type_cours
            }
            events_list.append(event_obj)

    print(f"Extraction terminée : {count_events} événements trouvés.")
    return {"events": events_list}

def json_to_ics(json_data):
    c = Calendar()
    
    # On ajoute un créateur pour faire pro
    c.creator = "-//VetoPlanning//FR"

    for item in json_data.get("events", []):
        e = Event()
        
        # Construction du titre propre
        # Si le type est déjà dans le titre, on ne le répète pas
        e.name = item['title']
        
        # Construction des dates avec fuseau horaire
        begin_str = f"{item['date']} {item['start_time']}"
        end_str = f"{item['date']} {item['end_time']}"
        
        try:
            # 1. Créer un objet datetime "naïf" (sans fuseau)
            dt_naive_start = datetime.strptime(begin_str, "%Y-%m-%d %H:%M")
            dt_naive_end = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
            
            # 2. Lui dire "C'est l'heure de Paris"
            dt_paris_start = LOCAL_TIMEZONE.localize(dt_naive_start)
            dt_paris_end = LOCAL_TIMEZONE.localize(dt_naive_end)
            
            # 3. Convertir en UTC (Z) pour l'iPhone
            # La librairie ICS gère mieux si on lui donne du UTC direct ou si on laisse faire,
            # mais convertir explicitement en UTC garantit le format 'Z'.
            e.begin = dt_paris_start.astimezone(pytz.utc)
            e.end = dt_paris_end.astimezone(pytz.utc)
            
        except ValueError as err:
            print(f"Erreur de date pour l'événement {item['title']} : {err}")
            continue

        e.location = item['location']
        
        # Description riche
        desc_lines = []
        if item['course_name'] and item['course_name'] not in item['title']:
            desc_lines.append(f"Matière: {item['course_name']}")
        
        # On remet le code matière complet s'il existe dans le titre original entre crochets
        # Ex: [0610 Techniques...] -> On garde l'info
        
        if item['teacher']: 
            desc_lines.append(f"Prof: {item['teacher']}")
            
        e.description = "\n".join(desc_lines)
        
        # Ajout à l'agenda
        c.events.add(e)

    return c

def main():
    try:
        with open(INPUT_HTML_FILE, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Erreur : Le fichier {INPUT_HTML_FILE} est introuvable.")
        return

    print("--- DÉBUT ANALYSE ---")
    json_data = parse_html_to_json(html_content)
    
    if not json_data['events']:
        print("\nATTENTION : Aucun événement trouvé. Le fichier HTML est peut-être vide ou le format a changé.")
    else:
        # 1. Sauvegarde JSON
        with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)
        print(f"Fichier JSON généré : {OUTPUT_JSON_FILE}")

        # 2. Création de l'objet Calendar
        calendar = json_to_ics(json_data)
        
        # 3. Génération du texte ICS
        ics_content = calendar.serialize()
        
        # 4. POST-TRAITEMENT pour compatibilité Apple (Le Hack Magique)
        # La librairie 'ics' ne permet pas facilement d'ajouter CALSCALE, on le fait à la main ici.
        if "CALSCALE:GREGORIAN" not in ics_content:
            ics_content = ics_content.replace("VERSION:2.0", "VERSION:2.0\nCALSCALE:GREGORIAN\nMETHOD:PUBLISH")
        
        # 5. Sauvegarde du fichier ICS final
        with open(OUTPUT_ICS_FILE, 'w', encoding='utf-8') as f:
            f.write(ics_content)
        
        print(f"Fichier ICS généré : {OUTPUT_ICS_FILE}")
        print("Terminé avec succès. Importez ce fichier sur votre iPhone.")

if __name__ == "__main__":
    main()
