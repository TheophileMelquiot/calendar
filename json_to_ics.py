import json
from datetime import datetime
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from ics import Calendar, Event

# 1. Chargement du fichier JSON
input_filename = 'emploi_du_temps_complet.json'
output_filename = 'emploi_du_temps_complet_v2.ics'

try:
    with open(input_filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"Erreur : Le fichier '{input_filename}' est introuvable.")
    exit()

# Création du calendrier
cal = Calendar()

# Aide à la compatibilité
try:
    cal.method = "PUBLISH"
except AttributeError:
    pass 

now = datetime.now()

for item in data:
    e = Event()
    
    # --- Extraction des variables ---
    course_code = item.get('course_code', '')
    course_name = item.get('course_name', '')
    title_raw = item.get('title', '')
    location = item.get('location', '')
    teacher = item.get('teacher', '')
    event_type = item.get('type', '') # Récupération du type (CM, TD, etc.)

    # --- MODIFICATION DU TITRE ---
    # Format : "{course_code} {type} - {course_name} - {title_raw}"
    e.name = f"{course_code} {event_type} - {course_name} - {title_raw}"
        
    # --- Lieu avec Professeur ---
    if teacher:
        e.location = f"{location} - {teacher}"
    else:
        e.location = location

    # --- Description ---
    description_lines = [
        f"Matière: {course_name}",
        f"Type: {event_type}",
        f"Intervenant: {teacher}",
        f"Salle: {location}",
        f"Code: {course_code}",
        f"Groupes: {', '.join(item.get('groups', []))}"
    ]
    e.description = "\n".join(description_lines)

    # --- Gestion des Dates et Heures ---
    date_str = item.get('date')
    start_str = item.get('start_time')
    end_str = item.get('end_time')

    if not date_str or not start_str:
        continue

    # Gestion "Toute la journée"
    if start_str == "00:00":
        e.begin = date_str 
        e.make_all_day()
        e.created = now
        e.last_modified = now
        cal.events.add(e)
        continue

    # Conversion date + heure
    try:
        # On définit le fuseau horaire de Paris
        paris_tz = ZoneInfo("Europe/Paris")
        
        # On crée la date de début et on lui "colle" l'étiquette Paris
        dt_start = datetime.strptime(f"{date_str} {start_str}", "%Y-%m-%d %H:%M")
        e.begin = dt_start.replace(tzinfo=paris_tz)
        
        if end_str:
            dt_end = datetime.strptime(f"{date_str} {end_str}", "%Y-%m-%d %H:%M")
            e.end = dt_end.replace(tzinfo=paris_tz)
        else:
            # Sécurité (1h par défaut)
            e.end = e.begin + timedelta(minutes=60)
            
    except ValueError as err:
        print(f"Erreur de date pour l'événement '{e.name}': {err}")
        continue

    # Metadata
    e.created = now
    e.last_modified = now

    # Ajout au calendrier
    cal.events.add(e)

# 3. Sauvegarde
with open(output_filename, 'w', encoding='utf-8') as f:
    f.writelines(cal.serialize())

print(f"Succès ! Le fichier '{output_filename}' a été créé avec {len(cal.events)} événements.")