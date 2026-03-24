"""
SCRAPER COMPLET - EMPLOI DU TEMPS 6 MOIS (+ ARCHIVAGE HTML)
===========================================================
Scrape 26 semaines (6 mois) d'emploi du temps
Stocke les événements en JSON et archive le HTML brut hebdomadaire
"""
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta
import re
import os
import sys

# Importer les fonctions du scraper original (si nécessaire pour deps externes)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class CelcatCompleteScraper:
    def __init__(self, login_url, username, password):
        """
        Scraper complet pour 6 mois d'emploi du temps
        
        Args:
            login_url: URL de la page de connexion
            username: Identifiant
            password: Mot de passe
        """
        self.login_url = login_url
        self.username = username
        self.password = password
        self.driver = None
        self.all_events = []
        
        # Configuration de l'archivage
        self.archive_dir = "archives_html"
        self._setup_archive_dir()
        
    def _setup_archive_dir(self):
        """Crée le dossier d'archive s'il n'existe pas"""
        try:
            os.makedirs(self.archive_dir, exist_ok=True)
            print(f"📁 Dossier d'archive prêt : {self.archive_dir}")
        except Exception as e:
            print(f"⚠️ Impossible de créer le dossier d'archive : {e}")

    def setup_driver(self, headless=True):
        """Configure le navigateur Chrome"""
        print("🔧 Configuration du navigateur...")
        
        options = webdriver.ChromeOptions()
        
        if headless:
            options.add_argument('--headless')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        print("✅ Navigateur prêt!")
        return self.driver
    
    def login(self):
        """Se connecte à Celcat"""
        print(f"\n🔐 Connexion à {self.login_url}...")
        
        try:
            self.driver.get(self.login_url)
            time.sleep(8)
            
            # Recherche des champs de connexion
            try:
                username_field = self.driver.find_element(By.NAME, "username")
                password_field = self.driver.find_element(By.NAME, "password")
            except Exception:
                try:
                    username_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='text']")
                    password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                except Exception:
                    username_field = self.driver.find_element(By.ID, "username")
                    password_field = self.driver.find_element(By.ID, "password")
            
            username_field.clear()
            username_field.send_keys(self.username)
            password_field.clear()
            password_field.send_keys(self.password)
            
            print("✅ Identifiants saisis")
            
            # Recherche du bouton de connexion
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "//button[contains(text(), 'Connexion')]",
                "//button[contains(text(), 'Se connecter')]"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    if selector.startswith("//"):
                        submit_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if submit_button:
                        break
                except Exception:
                    continue
            
            if submit_button:
                submit_button.click()
            else:
                username_field.submit()
            
            time.sleep(8)
            
            print("✅ Connexion réussie!")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la connexion: {e}")
            return False
    
    def navigate_to_week(self, week_date):
        """Navigate vers une semaine spécifique"""
        print(f"\n📅 Navigation vers la semaine du {week_date.strftime('%d/%m/%Y')}...")
        
        try:
            # Cliquer sur le sélecteur de date
            date_picker = self.driver.find_element(By.CLASS_NAME, "fc-center")
            date_picker.click()
            time.sleep(2)
            
            # Chercher et cliquer sur la date
            date_cells = self.driver.find_elements(By.CSS_SELECTOR, "td[data-date]")
            
            target_iso = week_date.strftime("%Y-%m-%d")
            found = False
            
            for cell in date_cells:
                cell_date = cell.get_attribute("data-date")
                if cell_date == target_iso:
                    cell.click()
                    time.sleep(3)
                    found = True
                    break
            
            if not found:
                # Fallback si la date n'est pas dans le mois affiché
                print("   ⚠️ Date non visible directement, utilisation navigation bouton...")
            
            return True
            
        except Exception as e:
            print(f"⚠️  Navigation manuelle nécessaire: {e}")
            return True
    
    def save_week_html(self, week_date):
        """
        Sauvegarde le HTML brut de la semaine courante
        """
        try:
            filename = f"week_{week_date.strftime('%Y-%m-%d')}.html"
            filepath = os.path.join(self.archive_dir, filename)
            
            html_content = self.driver.page_source
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            print(f"   💾 HTML archivé: {filename}")
            return True
        except Exception as e:
            print(f"   ❌ Erreur archivage HTML: {e}")
            return False

    def extract_week_events(self, week_date):
        """Extrait les événements de la semaine courante"""
        print(f"🔍 Extraction des événements de la semaine {week_date.strftime('%d/%m/%Y')}...")
        
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        events = []
        
        # Extraire les dates de la semaine
        dates_map = self.extract_week_dates(soup)
        
        if not dates_map:
            print("❌ Impossible d'extraire les dates")
            return events
        
        # Extraire les événements
        content_skeleton = soup.find('div', class_='fc-content-skeleton')
        
        if not content_skeleton:
            print("⚠️  Aucun événement trouvé pour cette semaine")
            return events
        
        event_containers = content_skeleton.find_all('a', class_='fc-time-grid-event')
        
        print(f"   📌 {len(event_containers)} événements trouvés")
        
        for event_tag in event_containers:
            try:
                event = self.parse_event(event_tag, dates_map)
                if event and event not in events:
                    events.append(event)
            except Exception as e:
                print(f"   ⚠️  Erreur parsing événement: {e}")
                continue
        
        return events
    
    def extract_week_dates(self, soup):
        """Extrait les dates des colonnes de la semaine"""
        dates_map = {}
        try:
            day_headers = soup.find_all('th', class_='fc-day-header')
            for header in day_headers:
                date_str = header.get('data-date')
                if date_str:
                    classes = header.get('class', [])
                    day_classes = ['fc-sun', 'fc-mon', 'fc-tue', 'fc-wed', 'fc-thu', 'fc-fri', 'fc-sat']
                    col_idx = 0
                    for idx, day_class in enumerate(day_classes):
                        if day_class in classes:
                            col_idx = idx
                            break
                    dates_map[col_idx] = date_str
        except Exception as e:
            print(f"Erreur extraction dates: {e}")
        return dates_map
    
    def parse_event(self, event_tag, dates_map):
        """Parse un événement individuel"""
        event = {
            'date': '', 'start_time': '', 'end_time': '', 'title': '',
            'course_code': '', 'course_name': '', 'location': '',
            'teacher': '', 'type': '', 'groups': []
        }
        
        try:
            # Date
            style = event_tag.get('style', '')
            left_match = re.search(r'left:\s*(\d+(?:\.\d+)?)%', style)
            if left_match:
                left_percent = float(left_match.group(1))
                col_idx = int(left_percent / 14.2857)
                event['date'] = dates_map.get(col_idx, '')
            
            # Heures
            time_span = event_tag.find('span', class_='fc-time')
            if time_span:
                time_text = time_span.get('data-full', '') or time_span.text
                time_match = re.match(r'(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})', time_text)
                if time_match:
                    event['start_time'] = time_match.group(1)
                    event['end_time'] = time_match.group(2)
            
            # Contenu
            fc_content = event_tag.find('div', class_='fc-content')
            if fc_content:
                title_span = fc_content.find('span', class_='fc-title')
                if title_span:
                    full_text = title_span.get_text(separator=' ', strip=True)
                    parts = [p.strip() for p in full_text.split('\n') if p.strip()]
                    
                    if parts:
                        code_match = re.match(r'^(0?\d{1,3})', parts[0])
                        if code_match:
                            event['course_code'] = code_match.group(1)
                            parts[0] = parts[0][len(event['course_code']):].strip()
                    
                    if parts and parts[0]: event['title'] = parts[0]
                    
                    for i, part in enumerate(parts):
                        if len(part) > 15 and not any(kw in part for kw in ['TD', 'TP', 'CM', 'Amphi']):
                            event['course_name'] = part
                            parts.pop(i)
                            break
                    
                    loc_keywords = ['Amphi', 'TD', 'TP', 'Salle', 'Porte', 'Espace', 'e-learning']
                    for part in parts:
                        if any(kw in part for kw in loc_keywords):
                            event['location'] = part
                            break
                    
                    for part in parts:
                        if re.match(r'^[A-ZÀ-Ý][a-zàèéêëïîôùûç\-]+\s+[A-ZÀ-Ý]', part):
                            event['teacher'] = part
                            break
                    
                    type_keywords = ['CM', 'TD', 'TP', 'Examen', 'Evaluation']
                    for part in parts:
                        if part.strip() in type_keywords:
                            event['type'] = part.strip()
                            break
                    
                    for part in parts:
                        if 'VET' in part or 'classe' in part:
                            clean_group = part.split('[')[0].strip() if '[' in part else part.strip()
                            if clean_group and clean_group not in event['groups']:
                                event['groups'].append(clean_group)
        
        except Exception as e:
            print(f"Erreur parsing: {e}")
        
        return event
    
    def scrape_full_semester(self, nb_weeks=26):
        """
        Scrape nb_weeks semaines à partir d'aujourd'hui et archive le HTML
        """
        print(f"\n{'='*70}")
        print(f"🎓 SCRAPING COMPLET - {nb_weeks} SEMAINES + ARCHIVAGE")
        print(f"{'='*70}\n")
        
        start_date = datetime.now()
        
        for week_num in range(nb_weeks):
            try:
                # Calculer la date de la semaine
                week_date = start_date + timedelta(weeks=week_num)
                
                print(f"\n📅 Semaine {week_num + 1}/{nb_weeks} - {week_date.strftime('%d/%m/%Y')}")
                print("-" * 50)
                
                # Navigation
                if week_num > 0:
                    try:
                        next_button = self.driver.find_element(By.CLASS_NAME, "fc-next-button")
                        next_button.click()
                        time.sleep(3) # Attente chargement AJAX
                    except Exception as e:
                        print(f"⚠️  Impossible de naviguer: {e}")
                
                # --- NOUVEAUTÉ : Archivage HTML ---
                self.save_week_html(week_date)
                # ----------------------------------
                
                # Extraction
                week_events = self.extract_week_events(week_date)
                
                for event in week_events:
                    if event not in self.all_events:
                        self.all_events.append(event)
                
                print(f"✅ {len(week_events)} événements extraits")
                print(f"📊 Total actuel: {len(self.all_events)} événements")
                
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Erreur semaine {week_num + 1}: {e}")
                continue
        
        print(f"\n{'='*70}")
        print(f"✅ SCRAPING TERMINÉ")
        print(f"📊 Total final: {len(self.all_events)} événements")
        print(f"📁 Archives HTML disponibles dans : {self.archive_dir}/")
        print(f"{'='*70}\n")
    
    def save_events(self, filename='emploi_du_temps_complet.json'):
        """Sauvegarde tous les événements dans un fichier JSON"""
        if not self.all_events:
            print("⚠️  Aucun événement à sauvegarder")
            return
        
        self.all_events.sort(key=lambda x: (x['date'], x['start_time']))
        
        output = {
            'metadata': {
                'scrape_date': datetime.now().isoformat(),
                'total_events': len(self.all_events),
                'archive_dir': self.archive_dir
            },
            'events': self.all_events
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"✅ JSON sauvegardé dans {filename}")
    
    def close(self):
        """Ferme le navigateur"""
        if self.driver:
            self.driver.quit()
            print("🔒 Navigateur fermé")
def update_celcat_url_with_today(url):
    """
    Remplace ou ajoute le paramètre dt=YYYY-MM-DD avec la date du jour
    """
    today = datetime.now().strftime("%Y-%m-%d")

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    # Forcer la date du jour
    query["dt"] = [today]

    new_query = urlencode(query, doseq=True)

    updated_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

    print(f"📅 URL mise à jour avec la date du jour : {today}")
    return updated_url


def main():
    """Fonction principale"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║   🎓 SCRAPER COMPLET - 6 MOIS (26 SEMAINES) + ARCHIVE 🎓  ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    try:
        with open('reponse.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("✅ Configuration chargée depuis reponse.json")
    except FileNotFoundError:
        print("❌ Erreur : Le fichier 'reponse.json' est introuvable.")
        return
    
    RAW_LOGIN_URL = config.get("login_url", "").strip()
    LOGIN_URL = update_celcat_url_with_today(RAW_LOGIN_URL)

    USERNAME = config.get("username", "").strip()
    PASSWORD = config.get("password", "").strip()
    
    NB_WEEKS = int(os.environ.get('NB_WEEKS', '26'))
    
    scraper = CelcatCompleteScraper(LOGIN_URL, USERNAME, PASSWORD)
    
    try:
        scraper.setup_driver(headless=True)  # HEADLESS pour GitHub Actions
        
        if not scraper.login():
            print("\n❌ Échec de la connexion")
            return
        
        time.sleep(5)
        
        print("\n🔄 Passage en vue hebdomadaire...")
        try:
            week_button = scraper.driver.find_element(By.CSS_SELECTOR, "button.fc-agendaWeek-button")
            week_button.click()
            time.sleep(3)
        except Exception:
            pass
        
        scraper.scrape_full_semester(nb_weeks=NB_WEEKS)
        scraper.save_events('emploi_du_temps_complet.json')
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Input supprimé pour GitHub Actions
        # input("\n⏸️  Appuyez sur Entrée pour fermer...")
        scraper.close()

if __name__ == "__main__":
    main()
