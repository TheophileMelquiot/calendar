import json
from datetime import datetime
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from ics import Calendar, Event

# 1. Chargement du fichier JSON
input_filename = 'emploi_du_temps_complet.json'
output_filename = 'mon_emploi_du_temps_fixed.ics'

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

def parse_time(time_str):
    """
    Parse une heure qui peut être au format 12h (AM/PM) ou 24h
    Retourne un objet time ou None si invalide
    """
    if not time_str:
        return None
    
    time_str = time_str.strip()
    
    # Format 24h (HH:MM)
    if ':' in time_str and not ('AM' in time_str.upper() or 'PM' in time_str.upper()):
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            pass
    
    # Format 12h avec AM/PM
    for fmt in ["%I:%M %p", "%I:%M%p"]:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    
    return None

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
        paris_tz = ZoneInfo("Europe/Paris")
        
        # Parser la date (format YYYY-MM-DD)
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as err:
            print(f"Erreur de format de date pour '{date_str}': {err}")
            continue
        
        # Parser l'heure de début
        start_time = parse_time(start_str)
        if not start_time:
            print(f"Erreur: impossible de parser l'heure de début '{start_str}' pour l'événement '{e.name}'")
            continue
        
        # Créer le datetime de début
        dt_start = datetime.combine(date_obj, start_time)
        e.begin = dt_start.replace(tzinfo=paris_tz)
        
        # Parser l'heure de fin
        if end_str:
            end_time = parse_time(end_str)
            if end_time:
                dt_end = datetime.combine(date_obj, end_time)
                e.end = dt_end.replace(tzinfo=paris_tz)
            else:
                # Si le parsing échoue, utiliser 1h par défaut
                e.end = e.begin + timedelta(hours=1)
        else:
            # Pas d'heure de fin fournie, utiliser 1h par défaut
            e.end = e.begin + timedelta(hours=1)
            
    except Exception as err:
        print(f"Erreur de traitement pour l'événement '{e.name}': {err}")
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
