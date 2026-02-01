"""
JSON TO ICS CONVERTER - Optimized for automation
=================================================
Convertit celcat_data.json en fichier .ics compatible avec tous les calendriers
"""

import json
from datetime import datetime, timedelta
from ics import Calendar, Event
import os

def convert_json_to_ics(input_file='celcat_data.json', output_file='emploi_du_temps.ics'):
    """
    Convertit le JSON en fichier ICS
    """
    print(f"📄 Lecture de {input_file}...")
    
    # Charger les données
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Erreur: Le fichier '{input_file}' est introuvable.")
        return False
    except json.JSONDecodeError:
        print(f"❌ Erreur: Le fichier '{input_file}' est mal formaté.")
        return False
    
    print(f"✅ {len(data)} événements chargés")
    
    # Créer le calendrier
    cal = Calendar()
    
    # Métadonnées du calendrier
    cal.method = "PUBLISH"
    cal.scale = "GREGORIAN"
    
    now = datetime.now()
    events_created = 0
    events_skipped = 0
    
    for item in data:
        try:
            e = Event()
            
            # Extraction des données
            course_code = item.get('course_code', '')
            course_name = item.get('course_name', '')
            title_raw = item.get('title', '')
            location = item.get('location', '')
            teacher = item.get('teacher', '')
            event_type = item.get('type', '')
            
            # Titre formaté: "{course_code} {type} - {course_name}"
            # Si title_raw contient des infos supplémentaires, les ajouter
            if title_raw and title_raw not in course_name:
                e.name = f"{course_code} {event_type} - {course_name} - {title_raw}"
            else:
                e.name = f"{course_code} {event_type} - {course_name}"
            
            # Nettoyer le nom (enlever doubles espaces, tirets seuls, etc.)
            e.name = ' '.join(e.name.split())
            e.name = e.name.replace(' -  - ', ' - ')
            
            # Lieu avec professeur
            if teacher and location:
                e.location = f"{location} - {teacher}"
            elif location:
                e.location = location
            elif teacher:
                e.location = teacher
            
            # Description détaillée
            description_lines = []
            if course_name:
                description_lines.append(f"Matière: {course_name}")
            if event_type:
                description_lines.append(f"Type: {event_type}")
            if teacher:
                description_lines.append(f"Enseignant: {teacher}")
            if location:
                description_lines.append(f"Salle: {location}")
            if course_code:
                description_lines.append(f"Code: {course_code}")
            
            groups = item.get('groups', [])
            if groups:
                description_lines.append(f"Groupes: {', '.join(groups)}")
            
            e.description = "\\n".join(description_lines)
            
            # Gestion des dates et heures
            date_str = item.get('date')
            start_str = item.get('start_time')
            end_str = item.get('end_time')
            
            if not date_str or not start_str:
                print(f"⚠️ Événement sans date/heure ignoré: {e.name}")
                events_skipped += 1
                continue
            
            # Événement toute la journée
            if start_str == "00:00" or not end_str:
                e.begin = date_str
                e.make_all_day()
            else:
                # Événement avec heure
                try:
                    e.begin = datetime.strptime(f"{date_str} {start_str}", "%Y-%m-%d %H:%M")
                    
                    if end_str:
                        e.end = datetime.strptime(f"{date_str} {end_str}", "%Y-%m-%d %H:%M")
                    else:
                        # Par défaut 1h
                        e.end = e.begin + timedelta(hours=1)
                
                except ValueError as err:
                    print(f"⚠️ Erreur de date pour '{e.name}': {err}")
                    events_skipped += 1
                    continue
            
            # Métadonnées
            e.created = now
            e.last_modified = now
            
            # Catégories pour filtrage
            if event_type:
                e.categories = [event_type]
            
            # Ajouter au calendrier
            cal.events.add(e)
            events_created += 1
            
        except Exception as e:
            print(f"⚠️ Erreur pour un événement: {e}")
            events_skipped += 1
            continue
    
    # Sauvegarder
    print(f"\n💾 Sauvegarde dans {output_file}...")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(cal.serialize())
        
        print(f"\n✅ SUCCÈS!")
        print(f"   - Événements créés: {events_created}")
        print(f"   - Événements ignorés: {events_skipped}")
        print(f"   - Fichier: {output_file}")
        print(f"   - Taille: {os.path.getsize(output_file) / 1024:.2f} KB")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")
        return False


if __name__ == "__main__":
    success = convert_json_to_ics()
    
    if not success:
        exit(1)
