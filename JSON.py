"""
EXTRACTION CELCAT AVEC AUTHENTIFICATION
========================================
Script pour extraire automatiquement votre emploi du temps Celcat
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
    
    #def navigate_to_calendar(self, calendar_url=None):
        """
        Navigue vers la page du calendrier
        
        Args:
            calendar_url: URL spécifique du calendrier (optionnel)
        """
        if calendar_url:
            print(f"\n📅 Navigation vers le calendrier: {calendar_url}")
            self.driver.get(calendar_url)
        else:
            print("\n📅 Recherche du calendrier dans la page...")
            # Chercher un lien vers le calendrier
            calendar_links = [
                "//a[contains(text(), 'Emploi du temps')]",
                "//a[contains(text(), 'Planning')]",
                "//a[contains(text(), 'Calendrier')]",
                "a[href*='calendar']",
                "a[href*='planning']"
            ]
            
            for selector in calendar_links:
                try:
                    if selector.startswith("//"):
                        link = self.driver.find_element(By.XPATH, selector)
                    else:
                        link = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    link.click()
                    print(f"✅ Calendrier trouvé!")
                    break
                except:
                    continue
        
        time.sleep(3)
        return True
    
    def extract_events_from_page(self):
        """
        Extrait tous les événements de la page actuelle
        """
        print("\n🔍 Extraction des événements...")
        
        # Récupérer le HTML de la page
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Sauvegarde du HTML pour debug
        with open('celcat_page.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        print("📄 HTML sauvegardé dans: celcat_page.html")
        
        # Chercher les événements
        event_selectors = [
            {'selector': 'div[class*="event"]', 'type': 'css'},
            {'selector': 'td[class*="Cell"]', 'type': 'css'},
            {'selector': 'div[data-event]', 'type': 'css'},
            {'selector': '//div[contains(@class, "Event")]', 'type': 'xpath'},
            {'selector': '//td[contains(@style, "background")]', 'type': 'xpath'}
        ]
        
        found_events = []
        
        for selector_info in event_selectors:
            try:
                if selector_info['type'] == 'css':
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector_info['selector'])
                else:
                    elements = self.driver.find_elements(By.XPATH, selector_info['selector'])
                
                if elements and len(elements) > 5:  # Au moins 5 éléments
                    found_events = elements
                    print(f"✅ {len(elements)} événements trouvés avec: {selector_info['selector']}")
                    break
            except:
                continue
        
        if not found_events:
            print("⚠️  Aucun événement trouvé automatiquement")
            print("💡 Analyse manuelle du HTML...")
            self._manual_html_analysis(soup)
            return []
        
        # Extraire les données de chaque événement
        for element in found_events:
            try:
                event_data = self._parse_event_element(element)
                if event_data and event_data.get('title'):
                    self.events.append(event_data)
            except Exception as e:
                continue
        
        print(f"✅ {len(self.events)} événements extraits avec succès!")
        return self.events
    
    def _parse_event_element(self, element):
        """
        Parse un élément HTML pour en extraire les informations
        """
        event = {
            'title': '',
            'start_time': '',
            'end_time': '',
            'date': '',
            'location': '',
            'teacher': '',
            'description': '',
            'raw_text': ''
        }
        
        # Récupérer le texte complet
        text = element.text.strip()
        event['raw_text'] = text
        
        if not text or len(text) < 3:
            return None
        
        # Séparer les lignes
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        if not lines:
            return None
        
        # Premier ligne = titre du cours
        event['title'] = lines[0]
        
        # Chercher les horaires (format: HH:MM - HH:MM ou HH:MM-HH:MM)
        time_pattern = r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})'
        for line in lines:
            match = re.search(time_pattern, line)
            if match:
                event['start_time'] = f"{match.group(1)}:{match.group(2)}"
                event['end_time'] = f"{match.group(3)}:{match.group(4)}"
                break
        
        # Chercher la salle
        location_patterns = [
            r'Amphi\s+([A-Z0-9]+)',
            r'Salle\s+([A-Z0-9]+)',
            r'\b([A-Z]\d+)\b',
            r'\[([^\]]+)\]'
        ]
        
        for line in lines:
            for pattern in location_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    event['location'] = match.group(0)
                    break
            if event['location']:
                break
        
        # Chercher le code du cours (ex: 064, 062, etc.)
        code_pattern = r'\b(\d{3})\b'
        for line in lines:
            match = re.search(code_pattern, line)
            if match:
                event['course_code'] = match.group(1)
                break
        
        # Description = tout sauf la première ligne
        if len(lines) > 1:
            event['description'] = '\n'.join(lines[1:])
        
        # Attributs data
        for attr in ['data-date', 'data-start', 'data-end', 'data-location', 'data-title']:
            try:
                value = element.get_attribute(attr)
                if value:
                    key = attr.replace('data-', '')
                    event[key] = value
            except:
                pass
        
        return event
    
    def _manual_html_analysis(self, soup):
        """
        Analyse manuelle du HTML pour comprendre la structure
        """
        print("\n🔬 ANALYSE MANUELLE DU HTML")
        print("=" * 60)
        
        # Chercher les tableaux
        tables = soup.find_all('table')
        print(f"📊 {len(tables)} tableaux trouvés")
        
        # Chercher les divs avec du style background
        colored_divs = soup.find_all('div', style=re.compile(r'background'))
        print(f"🎨 {len(colored_divs)} divs colorés trouvés")
        
        # Afficher un exemple
        if colored_divs:
            print("\n📋 Exemple de div coloré:")
            print(colored_divs[0].prettify()[:500])
        
        # Chercher les classes intéressantes
        all_classes = set()
        for tag in soup.find_all(True):
            if tag.get('class'):
                all_classes.update(tag.get('class'))
        
        event_classes = [c for c in all_classes if any(keyword in c.lower() for keyword in ['event', 'cell', 'cours', 'slot'])]
        
        if event_classes:
            print("\n🔍 Classes potentiellement intéressantes:")
            for cls in event_classes[:10]:
                print(f"  - {cls}")
    
    def save_to_json(self, filename='celcat_events.json'):
        """
        Sauvegarde les événements en JSON
        """
        if not self.events:
            print("\n⚠️  Aucun événement à sauvegarder")
            return None
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.events, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ {len(self.events)} événements sauvegardés dans: {filename}")
        
        # Afficher un exemple
        print("\n📋 Exemple d'événement:")
        print(json.dumps(self.events[0], indent=2, ensure_ascii=False))
        
        return filename
    
    def close(self):
        """
        Ferme le navigateur
        """
        if self.driver:
            self.driver.quit()
            print("\n🔒 Navigateur fermé")


def main():
    print("=" * 70)
    print("  📚 EXTRACTION AUTOMATIQUE CELCAT AVEC AUTHENTIFICATION")
    print("=" * 70)
    
    # Configuration
    print("\n🔧 CONFIGURATION")
    print("-" * 70)
    
# --- MODIFICATION ICI : CHARGEMENT DU JSON ---
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

    # Attribution des variables
    login_url = config.get("login_url", "").strip()
    username = config.get("username", "").strip()
    password = config.get("password", "").strip()
    #calendar_url = config.get("calendar_url", "").strip() or None
    
    # Gestion du choix o/n pour le navigateur
    show_choice = config.get("show_browser", "n").strip().lower()
    show_browser = (show_choice == 'o')
    # ----------------------------------------------
    
    if not login_url or not username or not password:
        print("❌ Erreur : Identifiants ou URL manquants dans le fichier JSON.")
        return
    
    
    # Création de l'extracteur
    extractor = CelcatAuthExtractor(login_url, username, password)
    
    try:
        # Configuration du navigateur
        extractor.setup_driver(headless=not show_browser)
        
        # Connexion
        if not extractor.login():
            print("\n❌ Échec de la connexion. Vérifiez vos identifiants.")
            return
        
        # Navigation vers le calendrier
        #extractor.navigate_to_calendar(calendar_url)
        
        # Extraction des événements
        events = extractor.extract_events_from_page()
        
        if events:
            # Sauvegarde
            extractor.save_to_json()
            
            print("\n" + "=" * 70)
            print("✅ EXTRACTION TERMINÉE AVEC SUCCÈS!")
            print("=" * 70)
            print("\n📂 Fichiers créés:")
            print("   - celcat_events.json : Vos événements structurés")
            print("   - celcat_page.html : HTML de la page (pour debug)")
            print("\n🎯 PROCHAINE ÉTAPE:")
            print("   Je vais créer le script de conversion en .ics pour iPhone!")
            nettoyer_donnees_celcat()
        else:
            print("\n⚠️  Aucun événement extrait.")
            print("💡 Consultez le fichier celcat_page.html et envoyez-moi sa structure")
            print("   pour que je puisse adapter le script!")
            nettoyer_donnees_celcat()
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Fermer le navigateur
        input("\nAppuyez sur Entrée pour fermer le navigateur...")
        extractor.close()

# ==============================================================================
# ✂️ CODE OPTIMISÉ POUR TON HTML SPÉCIFIQUE (FullCalendar Month View) ✂️
# ==============================================================================

# ==============================================================================
# ✂️ CODE CORRIGÉ : GESTION DES ROWSPANS (Décalages verticaux)
# ==============================================================================

def nettoyer_donnees_celcat():
    """
    Lit celcat_page.html et extrait les données en prenant en compte 
    les décalages verticaux (rowspan) pour ne pas rater d'événements.
    """
    import json
    import re
    from bs4 import BeautifulSoup

    print("\n🧹 Démarrage du nettoyage (Algorithme: Rowspan Tracking)...")
    
    try:
        with open('celcat_page.html', 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print("❌ Erreur : 'celcat_page.html' introuvable.")
        return

    soup = BeautifulSoup(html, 'html.parser')
    events_clean = []
    
    weeks = soup.find_all('div', class_='fc-content-skeleton')
    
    for week in weeks:
        # 1. DATES (Récupération des entêtes de colonnes)
        dates_map = {}
        thead = week.find('thead')
        if thead:
            day_headers = thead.find_all('td', class_='fc-day-top')
            for col_idx, td in enumerate(day_headers):
                date_str = td.get('data-date')
                if date_str:
                    dates_map[col_idx] = date_str

        # 2. PARCOURS DES LIGNES (TBODY)
        tbody = week.find('tbody')
        if not tbody: continue
        
        rows = tbody.find_all('tr')
        
        # 'spans' suit le nombre de lignes encore bloquées pour chaque colonne (0 à 6)
        # Initialisé à 0 pour les 7 jours de la semaine
        spans = [0] * 7 
        
        for row in rows:
            cells = row.find_all('td')
            cell_iter = iter(cells) # Itérateur pour consommer les cellules une par une
            
            for col_idx in range(7):
                # CAS A : La colonne est occupée par un événement du dessus (rowspan)
                if spans[col_idx] > 0:
                    spans[col_idx] -= 1
                    # On ne lit PAS de nouvelle cellule, car cette case est "virtuellement" 
                    # occupée par l'extension de l'événement précédent.
                    continue
                
                # CAS B : La colonne est libre, on lit la prochaine cellule HTML disponible
                try:
                    cell = next(cell_iter)
                except StopIteration:
                    break # Fin de ligne
                
                # Si cette cellule s'étale sur plusieurs lignes vers le bas, on met à jour 'spans'
                rowspan = int(cell.get('rowspan', 1))
                if rowspan > 1:
                    spans[col_idx] = rowspan - 1
                
                # Si c'est un événement, on l'extrait
                if 'fc-event-container' in cell.get('class', []):
                    # Grâce à notre boucle for col_idx, on a la BONNE date, même s'il y a des trous
                    event_date = dates_map.get(col_idx)
                    event_link = cell.find('a', class_='fc-day-grid-event')
                    
                    if event_link and event_date:
                        parsed_event = parse_single_event_detail(event_link, event_date)
                        if parsed_event:
                            events_clean.append(parsed_event)

    # 3. SAUVEGARDE ET TRI
    events_clean.sort(key=lambda x: (x['date'], x['start_time']))
    
    filename = 'celcat_clean.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(events_clean, f, indent=2, ensure_ascii=False)
        
    print(f"\n✅ TERMINÉ ! {len(events_clean)} événements extraits (y compris les chevauchements).")
    print(f"📂 Fichier généré : {filename}")

# Note: La fonction parse_single_event_detail reste identique à celle que tu avais, 
# elle est appelée correctement ici.

def parse_single_event_detail(event_elem, date_str):
    """Extrait les détails d'un bloc événement HTML"""
    
    event = {
        'date': date_str,
        'start_time': '', 
        'title': '',
        'course_code': '', 
        'course_name': '', 
        'location': '',
        'teacher': '', 
        'type': '', 
        'groups': []
    }

    # 1. CONTENU BRUT
    content_div = event_elem.find('div', class_='fc-content')
    if not content_div: return None

    # Heure (ex: <span class="fc-time">08:30</span>)
    time_span = content_div.find('span', class_='fc-time')
    if time_span:
        event['start_time'] = time_span.get_text(strip=True)
    else:
        # Parfois l'heure n'est pas dans le span, mais au début du texte
        # Ou c'est un événement journée entière
        event['start_time'] = "00:00"

    # Extraction du texte structuré avec ||| comme séparateur
    for br in content_div.find_all('br'):
        br.replace_with('|||')
    
    full_text = content_div.get_text(separator='|||', strip=True)
    # Nettoyage des doublons de séparateurs générés par get_text
    raw_parts = [p.strip() for p in full_text.split('|||') if p.strip()]
    
    parts = []
    # Filtrer l'heure si elle se répète dans le texte
    for p in raw_parts:
        if p != event['start_time'] and p != "|||":
            parts.append(p)

    if not parts: return None

    # 2. LOGIQUE D'EXTRACTION SPÉCIFIQUE (Basée sur ton HTML)
    
    # Index de lecture
    idx = 0
    
    # --- A. TITRE (Souvent la première ligne, ex: "Présentation UE...") ---
    if idx < len(parts):
        # Parfois la première ligne est juste l'heure répétée ou un espace
        if re.match(r'^\d{2}:\d{2}$', parts[idx]):
            idx += 1
        
        if idx < len(parts):
            event['title'] = parts[idx]
            idx += 1

    # --- B. CODE ET NOM DU COURS (ex: 064 Réglementation...) ---
    # On cherche une ligne qui commence par 3 chiffres
    while idx < len(parts):
        part = parts[idx]
        # Regex: Commence par 3 ou 4 chiffres, suivi d'espace, suivi de texte
        match = re.match(r'^(\d{3,4})\s+(.+)', part)
        if match:
            event['course_code'] = match.group(1)
            # Nettoyer le nom (souvent répété entre crochets à la fin)
            raw_name = match.group(2)
            if '[' in raw_name:
                event['course_name'] = raw_name.split('[')[0].strip()
            else:
                event['course_name'] = raw_name
            idx += 1
            break # On a trouvé le cours, on passe à la suite
        idx += 1
        
    # --- C. SALLE (ex: Amphi G5, 220 TD - Porte n° 220) ---
    # Mots clés spécifiques trouvés dans ton HTML
    loc_keywords = ['Amphi', 'Salle', 'Porte', 'Espace modulaire', 'e-learning', 'Labo']
    while idx < len(parts):
        part = parts[idx]
        if any(kw in part for kw in loc_keywords) and not re.match(r'^\d{3}', part):
            event['location'] = part
            idx += 1
            break
        idx += 1

    # --- D. ENSEIGNANT (ex: Ruvoen Nathalie) ---
    # Cherche pattern: Mot Majuscule + Espace + Mot Majuscule
    # Et qui n'est PAS un type de cours (CM, TD) ou un Groupe (VET3)
    exclude_list = ['CM', 'TD', 'TP', 'VET3', 'Master', 'Examen']
    while idx < len(parts):
        part = parts[idx]
        # Regex pour Nom Prénom (au moins 2 lettres, commence par Maj)
        is_name = re.match(r'^[A-Z][a-zéèë\-]+\s+[A-Z][a-zéèë\-]+', part)
        is_not_excluded = not any(ex in part for ex in exclude_list)
        
        if is_name and is_not_excluded:
            event['teacher'] = part
            idx += 1
            break
        idx += 1

    # --- E. TYPE (CM, TD, TP) ---
    type_keywords = ['CM', 'TD', 'TP', 'Examen', 'Evaluation', 'Oral', 'Conférence']
    while idx < len(parts):
        part = parts[idx]
        # Vérification exacte ou contient
        if part in type_keywords or any(t == part for t in type_keywords):
            event['type'] = part
            idx += 1
            break
        idx += 1

    # --- F. GROUPES (Le reste, souvent avec des crochets ou VET3) ---
    while idx < len(parts):
        part = parts[idx]
        # Si contient des crochets ou "VET" ou "Master"
        if '[' in part or 'VET' in part or 'Master' in part:
            # Nettoyage : "VET3 [VET3]" -> "VET3"
            clean_group = part.split('[')[0].strip()
            if clean_group:
                event['groups'].append(clean_group)
        idx += 1

    return event

if __name__ == "__main__":
    main()


"""
📦 INSTALLATION REQUISE
========================

pip install selenium webdriver-manager beautifulsoup4

Ça va télécharger automatiquement ChromeDriver!

========================

💡 CONSEILS D'UTILISATION
========================

1. Lancez le script une première fois avec "Afficher navigateur = OUI"
   pour voir ce qui se passe

2. Si ça ne trouve pas les événements automatiquement:
   - Regardez le fichier celcat_page.html créé
   - Envoyez-moi un extrait du HTML
   - Je pourrai adapter le script précisément!

3. Une fois que ça marche, relancez avec "Afficher navigateur = NON"
   pour que ce soit plus rapide

========================
"""