# 📅 CELCAT Calendar Auto-Sync

**Synchronisation automatique de votre emploi du temps CELCAT vers un calendrier ICS**

Ce projet scrappe automatiquement votre emploi du temps CELCAT et le convertit en fichier `.ics` hébergé sur GitHub Pages, synchronisable avec Google Calendar, Apple Calendar, Outlook, etc.

---

## 🎯 Fonctionnalités

- ✅ **Scraping complet du semestre** (6 mois) tous les 6 mois
- ✅ **Vérification quotidienne** des 2 prochaines semaines pour détecter les changements
- ✅ **Mise à jour automatique** via GitHub Actions
- ✅ **Hébergement gratuit** sur GitHub Pages
- ✅ **Compatible** avec tous les calendriers (Google, Apple, Outlook, etc.)

---

## 📋 Prérequis

- Un compte GitHub
- Accès à votre emploi du temps CELCAT (identifiants)
- 10 minutes de configuration

---

## 🚀 Installation et Configuration

### Étape 1: Fork ou Clone ce Repository

#### Option A: Fork (Recommandé)
1. Cliquez sur le bouton **Fork** en haut à droite de cette page
2. Attendez que le fork soit créé
3. Vous avez maintenant votre propre copie du projet !

#### Option B: Créer un nouveau repository
1. Créez un nouveau repository sur GitHub
2. Clonez-le localement:
   ```bash
   git clone https://github.com/VOTRE-USERNAME/VOTRE-REPO.git
   cd VOTRE-REPO
   ```
3. Copiez tous les fichiers de ce projet dans votre repository

---

### Étape 2: Configuration des Secrets GitHub

Les secrets GitHub permettent de stocker vos identifiants de manière sécurisée.

1. Allez dans votre repository GitHub
2. Cliquez sur **Settings** (⚙️ en haut)
3. Dans le menu de gauche, allez dans **Secrets and variables** → **Actions**
4. Cliquez sur **New repository secret**
5. Ajoutez les 3 secrets suivants:

   **Secret 1: `CELCAT_LOGIN_URL`**
   - Name: `CELCAT_LOGIN_URL`
   - Value: `https://calendar.oniris-nantes.fr/login` (ou votre URL de connexion)
   
   **Secret 2: `CELCAT_USERNAME`**
   - Name: `CELCAT_USERNAME`
   - Value: Votre identifiant CELCAT
   
   **Secret 3: `CELCAT_PASSWORD`**
   - Name: `CELCAT_PASSWORD`
   - Value: Votre mot de passe CELCAT

⚠️ **Important**: Ne partagez JAMAIS ces secrets publiquement !

---

### Étape 3: Activer GitHub Actions

1. Dans votre repository, allez dans l'onglet **Actions**
2. Si c'est la première fois, GitHub vous demandera d'activer les workflows
3. Cliquez sur **I understand my workflows, go ahead and enable them**

---

### Étape 4: Activer GitHub Pages

1. Allez dans **Settings** → **Pages** (dans le menu de gauche)
2. Dans **Source**, sélectionnez:
   - **Branch**: `main` (ou `master`)
   - **Folder**: `/ (root)`
3. Cliquez sur **Save**
4. Attendez quelques minutes que le site soit déployé
5. Votre calendrier sera accessible à:
   ```
   https://VOTRE-USERNAME.github.io/VOTRE-REPO/emploi_du_temps.ics
   ```

---

### Étape 5: Premier Scraping (Manuel)

Pour lancer le premier scraping complet:

1. Allez dans **Actions**
2. Cliquez sur le workflow **📅 CELCAT Calendar Auto-Update**
3. Cliquez sur **Run workflow** (bouton à droite)
4. Sélectionnez **Mode**: `full`
5. Cliquez sur **Run workflow**
6. Attendez quelques minutes (5-10 min pour 4 mois)

Une fois terminé, votre fichier `emploi_du_temps.ics` sera disponible sur GitHub Pages !

---

## 📱 Ajouter le Calendrier à votre Application

### Google Calendar

1. Ouvrez [Google Calendar](https://calendar.google.com)
2. À gauche, cliquez sur **+** à côté de "Autres agendas"
3. Sélectionnez **Depuis une URL**
4. Collez votre URL:
   ```
   https://VOTRE-USERNAME.github.io/VOTRE-REPO/emploi_du_temps.ics
   ```
5. Cliquez sur **Ajouter un agenda**

**Mise à jour**: Google Calendar met à jour automatiquement les calendriers externes toutes les 8-24h.

---

### Apple Calendar (iPhone/Mac)

#### Sur iPhone:
1. Allez dans **Réglages** → **Calendrier** → **Comptes**
2. Appuyez sur **Ajouter un compte**
3. Sélectionnez **Autre**
4. Appuyez sur **Ajouter un calendrier avec abonnement**
5. Collez votre URL et appuyez sur **Suivant**

#### Sur Mac:
1. Ouvrez l'application **Calendrier**
2. Menu **Fichier** → **Nouvel abonnement au calendrier**
3. Collez votre URL
4. Cliquez sur **S'abonner**

---

### Outlook

1. Ouvrez [Outlook.com](https://outlook.com)
2. Cliquez sur **Ajouter un calendrier**
3. Sélectionnez **S'abonner à partir du Web**
4. Collez votre URL
5. Donnez un nom à votre calendrier
6. Cliquez sur **Importer**

---

## ⚙️ Configuration Avancée

### Modifier les Horaires de Scraping

Éditez le fichier `.github/workflows/celcat-auto-update.yml`:

```yaml
on:
  schedule:
    # Scraping complet tous les 6 mois (1er janvier et juillet)
    - cron: '0 2 1 1,7 *'
    
    # Vérification quotidienne à 3h du matin
    - cron: '0 3 * * *'
```

**Format CRON**:
- `'0 3 * * *'` = Tous les jours à 3h
- `'0 */6 * * *'` = Toutes les 6 heures
- `'0 0 * * 1'` = Tous les lundis à minuit

---

### Modifier la Durée de Scraping Complet

Dans `scraper_auto.py`, ligne ~180:

```python
events = scraper.scrape_full_semester(months=4)  # Changez 4 en 6 pour 6 mois
```

---

## 🧪 Test en Local

### Installation

```bash
# Cloner le repository
git clone https://github.com/VOTRE-USERNAME/VOTRE-REPO.git
cd VOTRE-REPO

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

### Configuration

1. Copiez `config.json.example` en `config.json`
2. Remplissez vos identifiants dans `config.json`

### Exécution

```bash
# Scraping complet (4 mois)
python scraper_auto.py full

# Vérification (2 semaines)
python scraper_auto.py check

# Conversion en ICS
python json_to_ics.py
```

---

## 📊 Structure du Projet

```
.
├── .github/
│   └── workflows/
│       └── celcat-auto-update.yml    # Workflow GitHub Actions
├── scraper_auto.py                    # Script de scraping principal
├── json_to_ics.py                     # Conversion JSON → ICS
├── requirements.txt                   # Dépendances Python
├── config.json.example                # Exemple de configuration
├── .gitignore                         # Fichiers à ignorer
├── celcat_data.json                   # Données scrapées (généré)
└── emploi_du_temps.ics               # Calendrier ICS (généré)
```

---

## 🔍 Vérification du Statut

### Voir les Logs de Scraping

1. Allez dans **Actions**
2. Cliquez sur le dernier workflow exécuté
3. Cliquez sur **scrape-and-generate** pour voir les détails

### Vérifier le Calendrier

Téléchargez directement le fichier:
```
https://VOTRE-USERNAME.github.io/VOTRE-REPO/emploi_du_temps.ics
```

Vous pouvez l'ouvrir avec un éditeur de texte pour vérifier son contenu.

---

## 🐛 Résolution de Problèmes

### Le workflow échoue

**Problème**: Erreur de connexion
- ✅ Vérifiez que vos secrets sont correctement configurés
- ✅ Vérifiez que votre URL de connexion est correcte
- ✅ Testez votre connexion manuellement sur CELCAT

**Problème**: Timeout
- ✅ Le site CELCAT peut être lent, réessayez plus tard
- ✅ Augmentez les temps d'attente dans `scraper_auto.py`

### Le calendrier ne se met pas à jour

**Google Calendar**:
- La mise à jour peut prendre 8-24h
- Retirez et réajoutez le calendrier

**Apple Calendar**:
- Forcez la synchronisation: Paramètres → Mail → Comptes → Récupérer de nouvelles données

### Le fichier ICS est vide

- Vérifiez que le scraping a réussi dans les logs Actions
- Vérifiez que `celcat_data.json` contient des données
- Testez en local avec `python scraper_auto.py check`

---

## 🔐 Sécurité

- ✅ **Secrets GitHub**: Vos identifiants sont chiffrés et sécurisés
- ✅ **Pas de commit**: Le fichier `config.json` est dans `.gitignore`
- ✅ **Lecture seule**: Le scraper ne modifie rien sur CELCAT
- ⚠️ **Accès public**: Le fichier `.ics` est public (pas de données sensibles dedans)

---

## 📝 Personnalisation

### Modifier le Format du Titre

Dans `json_to_ics.py`, ligne ~50:

```python
# Format actuel: "066 TD - Pharmacologie et toxicologie clinique"
e.name = f"{course_code} {event_type} - {course_name}"

# Autres formats possibles:
# e.name = f"{course_name} ({event_type})"  # Pharmacologie (TD)
# e.name = f"[{course_code}] {course_name}"  # [066] Pharmacologie
```

### Ajouter des Alarmes

Dans `json_to_ics.py`, après `e.description = ...`:

```python
from ics import Alarm

# Alarme 15 minutes avant
alarm = Alarm(trigger=timedelta(minutes=-15))
e.alarms = [alarm]
```

---

## 🎓 Utilisation Avancée

### Plusieurs Calendriers

Pour créer plusieurs calendriers (ex: par type de cours):

1. Dupliquez `json_to_ics.py` en `json_to_ics_cm.py`, `json_to_ics_td.py`
2. Ajoutez des filtres:
   ```python
   # Dans json_to_ics_cm.py
   data = [item for item in data if item.get('type') == 'CM']
   ```
3. Modifiez le workflow pour générer plusieurs fichiers

### Notifications par Email

Ajoutez à la fin du workflow `.github/workflows/celcat-auto-update.yml`:

```yaml
- name: 📧 Envoyer notification
  if: steps.scrape.outputs.changes_detected == 'true'
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.MAIL_USERNAME }}
    password: ${{ secrets.MAIL_PASSWORD }}
    subject: "🔄 Emploi du temps mis à jour"
    body: "Des changements ont été détectés dans votre emploi du temps !"
    to: votre-email@example.com
```

---

## 📞 Support

- 🐛 **Bug**: Ouvrez une [Issue](https://github.com/VOTRE-USERNAME/VOTRE-REPO/issues)
- 💡 **Question**: Consultez les [Discussions](https://github.com/VOTRE-USERNAME/VOTRE-REPO/discussions)
- 📖 **Documentation**: Ce README

---

## 📜 Licence

Ce projet est sous licence MIT. Vous êtes libre de l'utiliser, le modifier et le redistribuer.

---

## 🙏 Remerciements

- CELCAT pour leur plateforme
- GitHub pour l'hébergement gratuit
- La communauté open-source

---

## ⚡ Mises à Jour

**Version 1.0.0** (Février 2026)
- ✅ Scraping automatique complet
- ✅ Détection de changements
- ✅ Hébergement GitHub Pages
- ✅ Documentation complète

---

**🎉 Votre emploi du temps est maintenant synchronisé automatiquement !**

**URL de votre calendrier**: 
```
https://VOTRE-USERNAME.github.io/VOTRE-REPO/emploi_du_temps.ics
```

**N'oubliez pas de**:
- ⭐ Star ce repository si ça vous aide
- 🔄 Partager avec vos camarades
- 📝 Contribuer si vous avez des améliorations

---

Made with ❤️ by [Votre Nom]
