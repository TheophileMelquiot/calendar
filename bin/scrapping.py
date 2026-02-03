"""
EXTRACTION CELCAT VUE HEBDOMADAIRE AVEC AUTHENTIFICATION
=========================================================
Script pour extraire automatiquement votre emploi du temps Celcat en vue semaine
même avec authentification requise
"""

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

class CelcatAuthExtractor:
    def __init__(self, login_url, username, password):
        """
        Extracteur Celcat avec authentification
        
        Args:
            login_url: URL de la page de connexion
            username: Votre identifiant
            password: Votre mot de passe
        """
        self.login_url = login_url
        self.username = username
        self.password = password
        self.driver = None
        self.events = []
    
    def setup_driver(self, headless=False):
        """
        Configure le navigateur Chrome
        
        Args:
            headless: Si True, navigateur invisible (plus rapide)
        """
        print("🔧 Configuration du navigateur...")
        
        options = webdriver.ChromeOptions()
        
        if headless:
            options.add_argument('--headless')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        
        # Initialisation du driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        print("✅ Navigateur prêt!")
        return self.driver
    
    def login(self):
        """
        Se connecte à Celcat avec vos identifiants
        """
        print(f"\n🔐 Connexion à {self.login_url}...")
        
        try:
            self.driver.get(self.login_url)
            
            # Attendre que la page charge
            time.sleep(8)
            
            # MÉTHODE 1: Recherche des champs par attribut 'name'
            try:
                username_field = self.driver.find_element(By.NAME, "username")
                password_field = self.driver.find_element(By.NAME, "password")
                print("✅ Champs trouvés (method: name)")
            except:
                # MÉTHODE 2: Recherche par type='text' et type='password'
                try:
                    username_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='text']")
                    password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                    print("✅ Champs trouvés (method: type)")
                except:
                    # MÉTHODE 3: Recherche par ID
                    try:
                        username_field = self.driver.find_element(By.ID, "username")
                        password_field = self.driver.find_element(By.ID, "password")
                        print("✅ Champs trouvés (method: id)")
                    except:
                        print("❌ Impossible de trouver les champs de connexion")
                        print("💡 Le HTML de la page est:")
                        print(self.driver.page_source[:1000])
                        return False
            
            # Remplir les champs
            username_field.clear()
            username_field.send_keys(self.username)
            
            password_field.clear()
            password_field.send_keys(self.password)
            
            print("✅ Identifiants saisis")
            
            # Chercher le bouton de connexion
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button.login",
                ".btn-login",
                "//button[contains(text(), 'Connexion')]",
                "//button[contains(text(), 'Se connecter')]",
                "//input[@value='Connexion']"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    if selector.startswith("//"):
                        submit_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if submit_button:
                        print(f"✅ Bouton de connexion trouvé: {selector}")
                        break
                except:
                    continue
            
            if not submit_button:
                print("⚠️  Bouton non trouvé, tentative d'envoi du formulaire...")
                username_field.submit()
            else:
                submit_button.click()
            
            # Attendre la redirection
            time.sleep(8)
            
            # Vérifier si la connexion a réussi
            current_url = self.driver.current_url
            if "login" in current_url.lower() or "connexion" in current_url.lower():
                print("❌ La connexion semble avoir échoué")
                print(f"URL actuelle: {current_url}")
                return False
            
            print("✅ Connexion réussie!")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la connexion: {e}")
            return False
    
    def extract_events_from_page(self):
        """
        Extrait tous les événements de la page actuelle
        """
        print("\n🔍 Extraction des événements...")
        
        # Récupérer le HTML de la page
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Sauvegarde du HTML pour debug
        with open('celcat_page_week.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        print("📄 HTML sauvegardé dans: celcat_page_week.html")
        
        # Extraire les événements de la vue hebdomadaire
        events = extract_week_events(soup)
        
        return events
    
    def save_events(self, filename='celcat_week.json'):
        """
        Sauvegarde les événements dans un fichier JSON
        """
        if not self.events:
            print("⚠️  Aucun événement à sauvegarder")
            return
        
        # Trier par date et heure
        self.events.sort(key=lambda x: (x['date'], x['start_time']))
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.events, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ {len(self.events)} événements sauvegardés dans {filename}")
    
    def close(self):
        """
        Ferme le navigateur
        """
        if self.driver:
            self.driver.quit()
            print("\n🔒 Navigateur fermé")


def extract_week_events(soup):
    """
    Extrait les événements de la vue hebdomadaire Celcat
    
    Structure de la page Celcat:
    - div.fc-content-skeleton contient les événements
    - Les événements sont des balises <a> avec class="fc-time-grid-event"
    - Chaque <a> contient un div.fc-content avec les informations
    """
    print("\n📅 Extraction de la vue hebdomadaire...")
    
    events_list = []
    
    # 1. EXTRAIRE LES DATES DES COLONNES
    dates_map = extract_week_dates(soup)
    print(f"📆 Dates extraites: {dates_map}")
    
    if not dates_map:
        print("❌ Impossible d'extraire les dates")
        return events_list
    
    # 2. TROUVER LA GRILLE DE TEMPS (fc-content-skeleton)
    # Cette div contient tous les événements organisés par colonne (jour)
    content_skeleton = soup.find('div', class_='fc-content-skeleton')
    
    if not content_skeleton:
        print("❌ Impossible de trouver fc-content-skeleton")
        return events_list
    
    print("✅ Grille d'événements trouvée")
    
    # 3. TROUVER TOUTES LES COLONNES DE CONTENU (une par jour)
    # Structure: <td> -> <div class="fc-content-col"> -> <div class="fc-event-container">
    content_cols = content_skeleton.find_all('div', class_='fc-content-col')
    
    print(f"📊 {len(content_cols)} colonnes trouvées")
    
    # 4. PARCOURIR CHAQUE COLONNE (= chaque jour)
    for col_idx, col_div in enumerate(content_cols):
        # Obtenir la date pour cette colonne
        event_date = dates_map.get(col_idx)
        
        if not event_date:
            continue
        
        # Trouver tous les conteneurs d'événements dans cette colonne
        event_containers = col_div.find_all('div', class_='fc-event-container')
        
        for container in event_containers:
            # Trouver tous les événements (balises <a>)
            event_links = container.find_all('a', class_='fc-time-grid-event')
            
            for event_link in event_links:
                parsed_event = parse_week_event_detail(event_link, event_date, None)
                if parsed_event:
                    events_list.append(parsed_event)
                    print(f"  ✓ {parsed_event['title']} - {parsed_event['date']} à {parsed_event['start_time']}")
    
    print(f"\n✅ {len(events_list)} événements extraits de la vue hebdomadaire")
    return events_list


def extract_week_dates(soup):
    """
    Extrait les dates des colonnes du calendrier hebdomadaire
    
    Dans le HTML Celcat:
    <th class="fc-day-header" data-date="2026-01-26">lun. 26/1</th>
    
    Retourne un dictionnaire: {index_colonne: 'YYYY-MM-DD'}
    """
    dates_map = {}
    
    # Chercher les en-têtes de jours avec l'attribut data-date
    day_headers = soup.find_all('th', class_='fc-day-header')
    
    if not day_headers:
        print("❌ Aucun en-tête de jour trouvé")
        return dates_map
    
    for idx, header in enumerate(day_headers):
        # Méthode 1: Extraire depuis l'attribut data-date (le plus fiable)
        date_str = header.get('data-date')
        
        if date_str:
            dates_map[idx] = date_str
            continue
        
        # Méthode 2: Parser le texte (ex: "lun. 26/1")
        text = header.get_text(strip=True)
        date_match = re.search(r'(\d{1,2})/(\d{1,2})', text)
        if date_match:
            day = int(date_match.group(1))
            month = int(date_match.group(2))
            
            # Déduire l'année à partir du titre principal (ex: "26 janv. – 1 févr. 2026")
            year = 2026  # Par défaut
            
            # Chercher l'année dans le titre
            title_h2 = soup.find('h2')
            if title_h2:
                year_match = re.search(r'\b(20\d{2})\b', title_h2.get_text())
                if year_match:
                    year = int(year_match.group(1))
            
            dates_map[idx] = f"{year}-{month:02d}-{day:02d}"
    
    return dates_map


def parse_week_event_detail(event_elem, date_str, default_time):
    """
    Extrait les détails d'un événement de la vue hebdomadaire Celcat
    
    Structure HTML d'un événement:
    <a class="fc-time-grid-event">
      <div class="fc-content">
        <div class="fc-time" data-start="08:35" data-full="08:35 - 10:30">
          <span>08:35 - 10:30</span>
        </div>
        TD1 Physiopath RESPIRATOIRE
        <br>
        062 Sémiologie physiopathologie intégrée [...]
        <br>
        220 TD - Porte n° 220
        <br>
        Mignot Grégoire
        <br>
        TD
        <br>
        VET3-classe 5 [VET3-classe 5]<br>VET3-classe 6 [...]
      </div>
    </a>
    
    Returns:
        dict: Événement avec date, start_time, end_time, title, course_code, 
              course_name, location, teacher, type, groups
    """
    event = {
        'date': date_str,
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
    
    # 1. TROUVER LE DIV DE CONTENU
    content_div = event_elem.find('div', class_='fc-content')
    if not content_div:
        return None
    
    # 2. EXTRAIRE LES HEURES (start_time et end_time)
    time_div = content_div.find('div', class_='fc-time')
    if time_div:
        # Récupérer data-start et extraire end_time depuis data-full
        start = time_div.get('data-start', '')
        full_time = time_div.get('data-full', '')
        
        if start:
            event['start_time'] = start
        
        # Extraire l'heure de fin depuis data-full (format: "08:35 - 10:30")
        if full_time:
            time_parts = re.findall(r'(\d{2}:\d{2})', full_time)
            if len(time_parts) >= 2:
                event['end_time'] = time_parts[1]
    
    # 3. EXTRAIRE LE TEXTE BRUT (en remplaçant les <br> par des séparateurs)
    # Cloner le div pour ne pas modifier l'original
    content_copy = BeautifulSoup(str(content_div), 'html.parser')
    
    # Supprimer le div fc-time pour ne pas le retraiter
    time_div_copy = content_copy.find('div', class_='fc-time')
    if time_div_copy:
        time_div_copy.decompose()
    
    # Remplacer tous les <br> par un marqueur unique
    for br in content_copy.find_all('br'):
        br.replace_with('|||BREAK|||')
    
    # Récupérer le texte
    full_text = content_copy.get_text(separator='', strip=True)
    
    # Séparer par les marqueurs
    parts = [p.strip() for p in full_text.split('|||BREAK|||') if p.strip()]
    
    if not parts:
        return None
    
    # 4. PARSER LES DIFFÉRENTS CHAMPS SELON LEUR POSITION
    idx = 0
    
    # A. TITRE (première ligne après l'heure)
    if idx < len(parts):
        event['title'] = parts[idx]
        idx += 1
    
    # B. CODE ET NOM DU COURS (ligne avec format "XXX Nom du cours [...]")
    # Pattern: commence par 3-4 chiffres ou lettres-chiffres
    while idx < len(parts):
        part = parts[idx]
        
        # Chercher pattern: "062 Sémiologie..." ou "0610 Techniques..."
        match = re.match(r'^([A-Z]*\d{2,4}[A-Z]*)\s+(.+)', part)
        if match:
            event['course_code'] = match.group(1)
            raw_name = match.group(2)
            
            # Nettoyer le nom (enlever la partie entre crochets)
            if '[' in raw_name:
                event['course_name'] = raw_name.split('[')[0].strip()
            else:
                event['course_name'] = raw_name.strip()
            
            idx += 1
            break
        idx += 1
    
    # C. LIEU/SALLE (ligne avec "Amphi", "Salle", "TD", "Porte", etc.)
    # Peut aussi être "e-learning"
    loc_keywords = ['Amphi', 'Salle', 'TD -', 'TP -', 'Porte', 'Espace modulaire', 
                    'e-learning', 'Labo', 'FC Espace']
    
    while idx < len(parts):
        part = parts[idx]
        
        # Vérifier si contient un mot-clé de lieu
        if any(kw in part for kw in loc_keywords):
            event['location'] = part
            idx += 1
            break
        
        # Sinon, pourrait être un nom de prof, on continue
        idx += 1
    
    # D. ENSEIGNANT (format: "Nom Prénom" ou "Prénom Nom")
    # Doit commencer par une majuscule et contenir au moins 2 mots
    exclude_teacher = ['CM', 'TD', 'TP', 'VET', 'Master', 'Examen', 'Evaluation']
    
    while idx < len(parts):
        part = parts[idx]
        
        # Pattern pour nom de personne: au moins 2 mots avec majuscules
        # Ex: "Mignot Grégoire", "Hernandez-Rodriguez Juan"
        is_name = re.match(r'^[A-ZÀ-Ý][a-zàèéêëïîôùûç\-]+\s+[A-ZÀ-Ý][a-zàèéêëïîôùûç\-]+', part)
        is_not_excluded = not any(ex in part for ex in exclude_teacher)
        
        if is_name and is_not_excluded:
            event['teacher'] = part
            idx += 1
            break
        
        idx += 1
    
    # E. TYPE DE COURS (CM, TD, TP, etc.)
    type_keywords = ['CM', 'TD', 'TP', 'Examen', 'Evaluation', 'Oral', 'Conférence', 'Contrôle']
    
    while idx < len(parts):
        part = parts[idx]
        
        # Vérifier si c'est exactement un type (pas juste contenu dans le texte)
        if part.strip() in type_keywords:
            event['type'] = part.strip()
            idx += 1
            break
        
        idx += 1
    
    # F. GROUPES (tout ce qui reste, souvent avec des crochets)
    # Ex: "VET3-classe 5 [VET3-classe 5]"
    while idx < len(parts):
        part = parts[idx]
        
        # Nettoyer: retirer la partie entre crochets qui est souvent redondante
        if '[' in part:
            clean_group = part.split('[')[0].strip()
        else:
            clean_group = part.strip()
        
        # Ajouter uniquement si contient "VET", "Master", "Groupe", "classe", etc.
        group_keywords = ['VET', 'Master', 'Groupe', 'classe', 'TD', 'TP']
        if any(kw in clean_group for kw in group_keywords) and clean_group:
            if clean_group not in event['groups']:
                event['groups'].append(clean_group)
        
        idx += 1
    
    return event


def main():
    """
    Fonction principale - PERSONNALISEZ ICI VOS PARAMÈTRES
    """
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║       🎓 EXTRACTEUR CELCAT - VUE HEBDOMADAIRE 🎓        ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # ========================================
    # ⚙️  CONFIGURATION À PERSONNALISER
    # ========================================
    try:
        with open('reponse.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("✅ Configuration chargée depuis reponse.json")
    except FileNotFoundError:
        print("❌ Erreur : Le fichier 'reponse.json' est introuvable.")
        return
    except json.JSONDecodeError:
        print("❌ Erreur : Le fichier 'reponse.json' est mal formaté.")
        return

    LOGIN_URL = config.get("login_url", "").strip()  # URL de connexion
    USERNAME = config.get("username", "").strip()   # Votre identifiant
    PASSWORD = config.get("password", "").strip()   # Votre mot de passe
    #CALENDAR_URL = "https://votre-celcat.com/calendar"  # URL du calendrier (optionnel)
    
    SHOW_BROWSER = True  # Mettre à False pour masquer le navigateur (plus rapide)
    
    # ========================================
    
    # Créer l'extracteur
    extractor = CelcatAuthExtractor(LOGIN_URL, USERNAME, PASSWORD)
    
    try:
        # 1. Configurer le navigateur
        extractor.setup_driver(headless=not SHOW_BROWSER)
        
        # 2. Se connecter
        if not extractor.login():
            print("\n❌ Échec de la connexion. Vérifiez vos identifiants.")
            return
        
        # 3. Naviguer vers le calendrier (si URL spécifiée)
        #if CALENDAR_URL:
            print(f"\n📅 Navigation vers: {CALENDAR_URL}")
            extractor.driver.get(CALENDAR_URL)
            time.sleep(5)  # Attendre le chargement
        
        # 4. S'assurer qu'on est en vue hebdomadaire
        print("\n🔄 Passage en vue hebdomadaire...")
        try:
            # Chercher le bouton "Semaine" ou "Week"
            week_button = None
            week_selectors = [
                "button.fc-agendaWeek-button",
                "button[class*='week']",
                "//button[contains(text(), 'Semaine')]",
                "//button[contains(text(), 'Week')]"
            ]
            
            for selector in week_selectors:
                try:
                    if selector.startswith("//"):
                        week_button = extractor.driver.find_element(By.XPATH, selector)
                    else:
                        week_button = extractor.driver.find_element(By.CSS_SELECTOR, selector)
                    if week_button:
                        week_button.click()
                        print("✅ Vue hebdomadaire activée")
                        time.sleep(3)
                        break
                except:
                    continue
            
            if not week_button:
                print("⚠️  Bouton 'Semaine' non trouvé, on suppose qu'on est déjà en vue hebdomadaire")
        except Exception as e:
            print(f"⚠️  Impossible de changer de vue: {e}")
        
        # 5. Extraire les événements
        extractor.events = extractor.extract_events_from_page()
        
        # 6. Sauvegarder
        extractor.save_events('celcat_week.json')
        
        print("\n" + "="*60)
        print("✅ EXTRACTION TERMINÉE AVEC SUCCÈS!")
        print("="*60)
        print(f"\n📊 Résumé:")
        print(f"   - Événements trouvés: {len(extractor.events)}")
        print(f"   - Fichier JSON: celcat_week.json")
        print(f"   - Fichier HTML (debug): celcat_page_week.html")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 7. Fermer le navigateur
        input("\n⏸️  Appuyez sur Entrée pour fermer le navigateur...")
        extractor.close()


if __name__ == "__main__":
    main()


"""
📦 INSTALLATION REQUISE
========================

pip install selenium webdriver-manager beautifulsoup4

========================

💡 UTILISATION
========================

1. Modifiez les paramètres dans la fonction main():
   - LOGIN_URL: URL de votre page de connexion Celcat
   - USERNAME: Votre identifiant
   - PASSWORD: Votre mot de passe
   - CALENDAR_URL: URL directe du calendrier (si vous l'avez)

2. Lancez le script:
   python celcat_week_scraper.py

3. Le script va:
   - Se connecter automatiquement
   - Passer en vue hebdomadaire
   - Extraire tous les événements
   - Les sauvegarder dans celcat_week.json

4. Structure des données extraites:
   {
     "date": "2026-01-29",
     "start_time": "08:30",
     "end_time": "10:25",
     "title": "Titre du cours",
     "course_code": "065",
     "course_name": "Anglais comm scientifique",
     "location": "220 TD - Porte n° 703",
     "teacher": "Dupont Jean",
     "type": "TD",
     "groups": ["VET3"]
   }

========================
"""
