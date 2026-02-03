import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from ics import Calendar, Event
import re

# 1. Chargement du fichier JSON
input_filename = 'emploi_du_temps_complet.json'
output_filename = 'emploi_du_temps_complet_v2.ics'

try:
    with open(input_filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"Erreur : Le fichier '{input_filename}' est introuvable.")
    exit()

def convert_time_to_24h(time_str):
    """
    Convertit une heure au format AM/PM ou 24h en format 24h
    Exemples:
      "2:00 PM" -> "14:00"
      "8:30 AM" -> "08:30"
      "14:00" -> "14:00" (déjà en format 24h)
    """
    if not time_str:
        return None
    
    time_str = time_str.strip()
    
    # Si déjà au format 24h (contient ':' mais pas AM/PM)
    if ':' in time_str and 'AM' not in time_str.upper() and 'PM' not in time_str.upper():
        # Ajouter un 0 si l'heure est sur 1 chiffre
        parts = time_str.split(':')
        if len(parts[0]) == 1:
            return f"0{time_str}"
        return time_str
    
    # Format AM/PM
    try:
        # Remplacer les espaces multiples et normaliser
        time_str = re.sub(r'\s+', ' ', time_str)
        
        # Parser avec AM/PM
        time_obj = datetime.strptime(time_str, "%I:%M %p")
        return time_obj.strftime("%H:%M")
    except ValueError:
        try:
            # Essayer sans espace avant AM/PM
            time_obj = datetime.strptime(time_str, "%I:%M%p")
            return time_obj.strftime("%H:%M")
        except ValueError:
            print(f"⚠️ Format d'heure non reconnu : '{time_str}' - ignoré")
            return None

# Création du calendrier
cal = Calendar()

# Aide à la compatibilité
try:
    cal.method = "PUBLISH"
except AttributeError:
    pass 

now = datetime.now()
events_added = 0
events_skipped = 0

for item in data:
    e = Event()
    
    # --- Extraction des variables ---
    course_code = item.get('course_code', '')
    course_name = item.get('course_name', '')
    title_raw = item.get('title', '')
    location = item.get('location', '')
    teacher = item.get('teacher', '')
    event_type = item.get('type', '')

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
        events_skipped += 1
        continue

    # Convertir les heures AM/PM en format 24h
    start_24h = convert_time_to_24h(start_str)
    end_24h = convert_time_to_24h(end_str) if end_str else None

    if not start_24h:
        print(f"⚠️ Événement ignoré (heure invalide) : {e.name}")
        events_skipped += 1
        continue

    # Gestion "Toute la journée"
    if start_24h == "00:00":
        e.begin = date_str 
        e.make_all_day()
        e.created = now
        e.last_modified = now
        cal.events.add(e)
        events_added += 1
        continue

    # Conversion date + heure
    try:
        # On définit le fuseau horaire de Paris
        paris_tz = ZoneInfo("Europe/Paris")
        
        # On crée la date de début et on lui "colle" l'étiquette Paris
        dt_start = datetime.strptime(f"{date_str} {start_24h}", "%Y-%m-%d %H:%M")
        e.begin = dt_start.replace(tzinfo=paris_tz)
        
        if end_24h:
            dt_end = datetime.strptime(f"{date_str} {end_24h}", "%Y-%m-%d %H:%M")
            e.end = dt_end.replace(tzinfo=paris_tz)
        else:
            # Sécurité (1h par défaut)
            e.end = e.begin + timedelta(minutes=60)
            
    except ValueError as err:
        print(f"⚠️ Erreur de date pour '{e.name}': {err}")
        events_skipped += 1
        continue

    # Metadata
    e.created = now
    e.last_modified = now

    # Ajout au calendrier
    cal.events.add(e)
    events_added += 1

# 3. Sauvegarde
with open(output_filename, 'w', encoding='utf-8') as f:
    f.writelines(cal.serialize())

print(f"\n{'='*60}")
print(f"✅ Succès ! Le fichier '{output_filename}' a été créé")
print(f"📊 Statistiques :")
print(f"   - Événements ajoutés : {events_added}")
print(f"   - Événements ignorés : {events_skipped}")
print(f"{'='*60}")
