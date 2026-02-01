"""
CELCAT AUTOMATIC SCRAPER - FULL SEMESTER + CHANGE DETECTION
===========================================================
Script automatisé pour extraire tout le semestre (4 mois) 
et vérifier les changements chaque jour (2 semaines en avance)
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import time
import os
import sys

class CelcatAutoScraper:
    def __init__(self, login_url, username, password):
        self.login_url = login_url
        self.username = username
        self.password = password
        self.driver = None
        self.all_events = []
        
    def setup_driver(self, headless=True):
        """Configure Chrome pour GitHub Actions"""
        print("🔧 Configuration du navigateur...")
        
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Pour GitHub Actions - utilise Chrome déjà installé
        if os.getenv('GITHUB_ACTIONS'):
            options.binary_location = '/usr/bin/google-chrome'
            service = Service('/usr/bin/chromedriver')
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
        
        self.driver = webdriver.Chrome(service=service, options=options)
        print("✅ Navigateur prêt!")
        return self.driver
    
    def login(self):
        """Connexion à Celcat"""
        print(f"\n🔐 Connexion à {self.login_url}...")
        
        try:
            self.driver.get(self.login_url)
            time.sleep(5)
            
            # Recherche des champs de connexion
            username_field = None
            password_field = None
            
            selectors = [
                (By.NAME, "username", By.NAME, "password"),
                (By.CSS_SELECTOR, "input[type='text']", By.CSS_SELECTOR, "input[type='password']"),
                (By.ID, "username", By.ID, "password"),
            ]
            
            for user_by, user_val, pass_by, pass_val in selectors:
                try:
                    username_field = self.driver.find_element(user_by, user_val)
                    password_field = self.driver.find_element(pass_by, pass_val)
                    print("✅ Champs de connexion trouvés")
                    break
                except:
                    continue
            
            if not username_field or not password_field:
                print("❌ Champs de connexion non trouvés")
                return False
            
            # Remplir et soumettre
            username_field.clear()
            username_field.send_keys(self.username)
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Soumettre le formulaire
            try:
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                submit_button.click()
            except:
                password_field.submit()
            
            time.sleep(5)
            
            # Vérifier connexion
            if "login" not in self.driver.current_url.lower():
                print("✅ Connexion réussie!")
                return True
            else:
                print("❌ Échec de connexion")
                return False
                
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            return False
    
    def navigate_to_week(self, target_date):
        """
        Navigue vers une semaine spécifique
        target_date: datetime object
        """
        print(f"\n📅 Navigation vers la semaine du {target_date.strftime('%Y-%m-%d')}...")
        
        # Cliquer sur vue semaine si nécessaire
        try:
            week_button = self.driver.find_element(By.CSS_SELECTOR, "button.fc-agendaWeek-button")
            week_button.click()
            time.sleep(2)
        except:
            pass  # Déjà en vue semaine
        
        # Calculer combien de semaines en avant/arrière
        today = datetime.now()
        weeks_diff = int((target_date - today).days / 7)
        
        if weeks_diff > 0:
            # Avancer
            next_button_selector = "button.fc-next-button"
            for _ in range(abs(weeks_diff)):
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, next_button_selector)
                    next_btn.click()
                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Erreur navigation: {e}")
                    break
        elif weeks_diff < 0:
            # Reculer
            prev_button_selector = "button.fc-prev-button"
            for _ in range(abs(weeks_diff)):
                try:
                    prev_btn = self.driver.find_element(By.CSS_SELECTOR, prev_button_selector)
                    prev_btn.click()
                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Erreur navigation: {e}")
                    break
        
        time.sleep(2)
        print(f"✅ Arrivé à la semaine cible")
    
    def extract_current_week(self):
        """Extrait les événements de la semaine actuelle visible"""
        print("\n🔍 Extraction de la page...")
        
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Utiliser la fonction d'extraction du fichier original
        events = self._extract_week_events(soup)
        
        return events
    
    def _extract_week_events(self, soup):
        """Extraction des événements - adapté du code original"""
        events_list = []
        
        # Extraire les dates
        date_headers = soup.select('th.fc-day-header')
        dates_map = {}
        
        for index, header in enumerate(date_headers):
            date_val = header.get('data-date')
            if date_val:
                dates_map[index] = date_val
        
        if not dates_map:
            print("⚠️ Aucune date trouvée")
            return events_list
        
        # Trouver les événements
        content_cols = soup.select('.fc-time-grid .fc-content-skeleton td')
        
        current_col_index = 0
        
        for td in content_cols:
            if not td.find('div', class_='fc-event-container'):
                continue
            
            if current_col_index not in dates_map:
                current_col_index += 1
                continue
            
            current_date = dates_map[current_col_index]
            events = td.select('a.fc-time-grid-event')
            
            for event in events:
                event_data = {
                    'date': current_date,
                    'start_time': '',
                    'end_time': '',
                    'title': '',
                    'course_code': '',
                    'course_name': '',
                    'location': '',
                    'teacher': '',
                    'type': '',
                    'groups': []
                }
                
                # Extraction temps
                time_div = event.find('div', class_='fc-time')
                if time_div and time_div.has_attr('data-full'):
                    time_range = time_div['data-full']
                    times = time_range.split('-')
                    event_data['start_time'] = times[0].strip()
                    event_data['end_time'] = times[1].strip() if len(times) > 1 else ""
                
                # Extraction contenu
                content_div = event.find('div', class_='fc-content')
                if content_div:
                    lines = [s.strip() for s in content_div.stripped_strings if s.strip()]
                    
                    # Enlever l'heure si présente
                    if lines and ':' in lines[0]:
                        lines.pop(0)
                    
                    if len(lines) >= 1:
                        event_data['title'] = lines[0]
                    
                    if len(lines) >= 2:
                        import re
                        raw_course = lines[1]
                        match = re.match(r'^([\w\d]+)\s+(.*)', raw_course)
                        if match:
                            event_data['course_code'] = match.group(1)
                            event_data['course_name'] = match.group(2)
                        else:
                            event_data['course_name'] = raw_course
                    
                    if len(lines) >= 3:
                        event_data['location'] = lines[2]
                    
                    if len(lines) >= 4:
                        event_data['teacher'] = lines[3]
                    
                    if len(lines) >= 5:
                        event_data['type'] = lines[4]
                    
                    if len(lines) >= 6:
                        raw_groups = " ".join(lines[5:])
                        # Nettoyer les crochets
                        import re
                        cleaned = re.sub(r'\[.*?\]', '', raw_groups).strip()
                        if cleaned:
                            event_data['groups'] = [cleaned]
                
                events_list.append(event_data)
            
            current_col_index += 1
        
        return events_list
    
    def scrape_full_semester(self, months=4):
        """
        Scrape tout le semestre (4 mois par défaut)
        """
        print(f"\n{'='*60}")
        print(f"🎓 SCRAPING COMPLET DU SEMESTRE ({months} mois)")
        print(f"{'='*60}\n")
        
        all_events = []
        today = datetime.now()
        
        # Calculer le nombre de semaines à scraper
        weeks_to_scrape = int(months * 4.33)  # ~4.33 semaines par mois
        
        for week_offset in range(weeks_to_scrape):
            target_date = today + timedelta(weeks=week_offset)
            
            print(f"\n--- Semaine {week_offset + 1}/{weeks_to_scrape} ---")
            
            try:
                # Naviguer vers la semaine
                self.navigate_to_week(target_date)
                
                # Extraire les événements
                week_events = self.extract_current_week()
                
                if week_events:
                    all_events.extend(week_events)
                    print(f"✅ {len(week_events)} événements extraits")
                else:
                    print("⚠️ Aucun événement trouvé")
                
                # Petite pause pour ne pas surcharger le serveur
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Erreur semaine {week_offset + 1}: {e}")
                continue
        
        # Enlever les doublons (même date + heure + titre)
        unique_events = []
        seen = set()
        
        for event in all_events:
            key = (event['date'], event['start_time'], event['title'])
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        print(f"\n✅ Total: {len(unique_events)} événements uniques extraits")
        
        self.all_events = sorted(unique_events, key=lambda x: (x['date'], x['start_time']))
        return self.all_events
    
    def scrape_next_two_weeks(self):
        """
        Scrape les 2 prochaines semaines pour détecter les changements
        """
        print(f"\n{'='*60}")
        print(f"🔍 VÉRIFICATION DES CHANGEMENTS (2 semaines)")
        print(f"{'='*60}\n")
        
        events = []
        today = datetime.now()
        
        for week_offset in range(2):  # 2 semaines
            target_date = today + timedelta(weeks=week_offset)
            
            print(f"\n--- Semaine {week_offset + 1}/2 ---")
            
            try:
                self.navigate_to_week(target_date)
                week_events = self.extract_current_week()
                
                if week_events:
                    events.extend(week_events)
                    print(f"✅ {len(week_events)} événements extraits")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Erreur: {e}")
                continue
        
        return events
    
    def compare_and_update(self, new_events, existing_file='celcat_data.json'):
        """
        Compare les nouveaux événements avec l'existant et met à jour
        """
        print(f"\n🔄 Comparaison avec les données existantes...")
        
        # Charger les données existantes
        existing_events = []
        if os.path.exists(existing_file):
            try:
                with open(existing_file, 'r', encoding='utf-8') as f:
                    existing_events = json.load(f)
                print(f"📄 {len(existing_events)} événements existants chargés")
            except:
                print("⚠️ Fichier existant corrompu, création d'un nouveau")
        
        # Créer un dictionnaire pour comparaison rapide
        existing_dict = {}
        for event in existing_events:
            key = (event['date'], event['start_time'], event['title'])
            existing_dict[key] = event
        
        # Mettre à jour ou ajouter
        changes_detected = False
        updated_count = 0
        added_count = 0
        
        for new_event in new_events:
            key = (new_event['date'], new_event['start_time'], new_event['title'])
            
            if key in existing_dict:
                # Comparer les détails
                if existing_dict[key] != new_event:
                    existing_dict[key] = new_event
                    updated_count += 1
                    changes_detected = True
                    print(f"🔄 Mis à jour: {new_event['title']} le {new_event['date']}")
            else:
                # Nouvel événement
                existing_dict[key] = new_event
                added_count += 1
                changes_detected = True
                print(f"➕ Ajouté: {new_event['title']} le {new_event['date']}")
        
        # Reconvertir en liste et trier
        all_events = sorted(existing_dict.values(), key=lambda x: (x['date'], x['start_time']))
        
        print(f"\n📊 Résumé:")
        print(f"   - Événements mis à jour: {updated_count}")
        print(f"   - Événements ajoutés: {added_count}")
        print(f"   - Total événements: {len(all_events)}")
        
        return all_events, changes_detected
    
    def save_json(self, events, filename='celcat_data.json'):
        """Sauvegarde en JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=4, ensure_ascii=False)
        print(f"✅ Sauvegardé dans {filename}")
    
    def close(self):
        """Ferme le navigateur"""
        if self.driver:
            self.driver.quit()
            print("\n🔒 Navigateur fermé")


def main():
    """Fonction principale"""
    
    # Charger la configuration
    try:
        # En production (GitHub Actions), utiliser les variables d'environnement
        if os.getenv('GITHUB_ACTIONS'):
            LOGIN_URL = os.getenv('CELCAT_LOGIN_URL')
            USERNAME = os.getenv('CELCAT_USERNAME')
            PASSWORD = os.getenv('CELCAT_PASSWORD')
            MODE = os.getenv('SCRAPE_MODE', 'check')  # 'full' ou 'check'
        else:
            # En local, utiliser le fichier config
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            LOGIN_URL = config['login_url']
            USERNAME = config['username']
            PASSWORD = config['password']
            MODE = sys.argv[1] if len(sys.argv) > 1 else 'check'
        
        print(f"⚙️ Mode: {MODE}")
        
    except Exception as e:
        print(f"❌ Erreur de configuration: {e}")
        return
    
    # Créer le scraper
    scraper = CelcatAutoScraper(LOGIN_URL, USERNAME, PASSWORD)
    
    try:
        # Setup et connexion
        scraper.setup_driver(headless=True)
        
        if not scraper.login():
            print("❌ Échec de connexion")
            return
        
        # Naviguer vers le calendrier
        calendar_url = LOGIN_URL.replace('/login', '/calendar')
        scraper.driver.get(calendar_url)
        time.sleep(5)
        
        if MODE == 'full':
            # Mode complet: scraper 4 mois
            events = scraper.scrape_full_semester(months=4)
            scraper.save_json(events, 'celcat_data.json')
            
        else:
            # Mode check: vérifier les 2 prochaines semaines
            new_events = scraper.scrape_next_two_weeks()
            updated_events, has_changes = scraper.compare_and_update(new_events)
            scraper.save_json(updated_events, 'celcat_data.json')
            
            # Pour GitHub Actions
            if os.getenv('GITHUB_ACTIONS'):
                with open(os.getenv('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
                    f.write(f"changes_detected={'true' if has_changes else 'false'}\n")
        
        print(f"\n{'='*60}")
        print("✅ SCRAPING TERMINÉ AVEC SUCCÈS!")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
