"""
Add Swahili, French, and Italian translations for mobile app
(Using existing Django translations as foundation)
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSLATIONS_DIR = os.path.join(BASE_DIR, "translations")

# Core translations to add for SW/FR/IT
SW_CORE = {
    "common": {
        "save": "Hifadhi",
        "cancel": "Ghairi",
        "submit": "Wasilisha",
        "edit": "Hariri",
        "delete": "Futa",
        "view": "Angalia",
        "apply": "Omba",
        "accept": "Kubali",
        "reject": "Kataa",
        "loading": "Inapakia...",
        "error": "Hitilafu",
        "success": "Mafanikio",
        "noResults": "Hakuna matokeo",
        "back": "Rudi",
        "close": "Funga",
        "confirm": "Thibitisha",
        "yes": "Ndio",
        "no": "Hapana",
        "ok": "Sawa",
        "retry": "Jaribu Tena",
        "search": "Tafuta"
    },
    "nav": {
        "home": "Nyumbani",
        "dashboard": "Dashibodi",
        "jobs": "Kazi",
        "assignments": "Majukumu",
        "earnings": "Mapato",
        "messages": "Ujumbe",
        "notifications": "Arifa",
        "profile": "Wasifu",
        "settings": "Mipangilio",
        "logout": "Toka"
    },
    "auth": {
        "login": "Ingia",
        "signIn": "Ingia",
        "email": "Barua Pepe",
        "password": "Nywila",
        "username": "Jina la Mtumiaji",
        "forgotPassword": "Umesahau Nywila?",
        "welcomeBack": "Karibu Tena!",
        "noAccount": "Huna akaunti?",
        "firstName": "Jina la Kwanza",
        "lastName": "Jina la Mwisho",
        "phone": "Nambari ya Simu"
    },
    "dashboard": {
        "title": "Dashibodi",
        "welcome": "Karibu tena",
        "quickActions": "Vitendo vya Haraka",
        "totalAssigned": "Jumla Iliyoteuliwa",
        "activeJobs": "Kazi Hai",
        "completedJobs": "Zimekamilika",
        "pendingJobs": "Zinasubiri",
        "totalEarnings": "Jumla ya Mapato"
    },
    "profile": {
        "title": "Wasifu",
        "myProfile": "Wasifu Wangu",
        "editProfile": "Hariri Wasifu",
        "verified": "Imethibitishwa",
        "notVerified": "Haijathibitishwa",
        "availableForWork": "Inapatikana kwa Kazi",
        "documents": "Hati",
        "skills": "Ujuzi",
        "experience": "Uzoefu",
        "location": "Mahali"
    },
    "settings": {
        "title": "Mipangilio",
        "account": "Akaunti",
        "language": "Lugha",
        "security": "Usalama",
        "changePassword": "Badilisha Nywila",
        "notifications": "Arifa",
        "privacy": "Faragha"
    }
}

FR_CORE = {
    "common": {
        "save": "Enregistrer",
        "cancel": "Annuler",
        "submit": "Soumettre",
        "edit": "Modifier",
        "delete": "Supprimer",
        "view": "Voir",
        "apply": "Postuler",
        "accept": "Accepter",
        "reject": "Refuser",
        "loading": "Chargement...",
        "error": "Erreur",
        "success": "Succès",
        "noResults": "Aucun résultat",
        "back": "Retour",
        "close": "Fermer",
        "confirm": "Confirmer",
        "yes": "Oui",
        "no": "Non",
        "ok": "OK",
        "retry": "Réessayer",
        "search": "Rechercher"
    },
    "nav": {
        "home": "Accueil",
        "dashboard": "Tableau de bord",
        "jobs": "Emplois",
        "assignments": "Missions",
        "earnings": "Gains",
        "messages": "Messages",
        "notifications": "Notifications",
        "profile": "Profil",
        "settings": "Paramètres",
        "logout": "Déconnexion"
    },
    "auth": {
        "login": "Connexion",
        "signIn": "Se connecter",
        "email": "E-mail",
        "password": "Mot de passe",
        "username": "Nom d'utilisateur",
        "forgotPassword": "Mot de passe oublié ?",
        "welcomeBack": "Bon retour !",
        "noAccount": "Pas de compte ?",
        "firstName": "Prénom",
        "lastName": "Nom",
        "phone": "Numéro de téléphone"
    },
    "dashboard": {
        "title": "Tableau de bord",
        "welcome": "Bon retour",
        "quickActions": "Actions rapides",
        "totalAssigned": "Total assigné",
        "activeJobs": "Emplois actifs",
        "completedJobs": "Terminés",
        "pendingJobs": "En attente",
        "totalEarnings": "Gains totaux"
    },
    "profile": {
        "title": "Profil",
        "myProfile": "Mon Profil",
        "editProfile": "Modifier le profil",
        "verified": "Vérifié",
        "notVerified": "Non vérifié",
        "availableForWork": "Disponible",
        "documents": "Documents",
        "skills": "Compétences",
        "experience": "Expérience",
        "location": "Lieu"
    },
    "settings": {
        "title": "Paramètres",
        "account": "Compte",
        "language": "Langue",
        "security": "Sécurité",
        "changePassword": "Changer le mot de passe",
        "notifications": "Notifications",
        "privacy": "Confidentialité"
    }
}

IT_CORE = {
    "common": {
        "save": "Salva",
        "cancel": "Annulla",
        "submit": "Invia",
        "edit": "Modifica",
        "delete": "Elimina",
        "view": "Visualizza",
        "apply": "Candidati",
        "accept": "Accetta",
        "reject": "Rifiuta",
        "loading": "Caricamento...",
        "error": "Errore",
        "success": "Successo",
        "noResults": "Nessun risultato",
        "back": "Indietro",
        "close": "Chiudi",
        "confirm": "Conferma",
        "yes": "Sì",
        "no": "No",
        "ok": "OK",
        "retry": "Riprova",
        "search": "Cerca"
    },
    "nav": {
        "home": "Home",
        "dashboard": "Cruscotto",
        "jobs": "Lavori",
        "assignments": "Incarichi",
        "earnings": "Guadagni",
        "messages": "Messaggi",
        "notifications": "Notifiche",
        "profile": "Profilo",
        "settings": "Impostazioni",
        "logout": "Esci"
    },
    "auth": {
        "login": "Accedi",
        "signIn": "Accedi",
        "email": "E-mail",
        "password": "Password",
        "username": "Nome utente",
        "forgotPassword": "Password dimenticata?",
        "welcomeBack": "Bentornato!",
        "noAccount": "Non hai un account?",
        "firstName": "Nome",
        "lastName": "Cognome",
        "phone": "Numero di telefono"
    },
    "dashboard": {
        "title": "Cruscotto",
        "welcome": "Bentornato",
        "quickActions": "Azioni rapide",
        "totalAssigned": "Totale assegnati",
        "activeJobs": "Lavori attivi",
        "completedJobs": "Completati",
        "pendingJobs": "In attesa",
        "totalEarnings": "Guadagni totali"
    },
    "profile": {
        "title": "Profilo",
        "myProfile": "Il mio profilo",
        "editProfile": "Modifica profilo",
        "verified": "Verificato",
        "notVerified": "Non verificato",
        "availableForWork": "Disponibile",
        "documents": "Documenti",
        "skills": "Competenze",
        "experience": "Esperienza",
        "location": "Posizione"
    },
    "settings": {
        "title": "Impostazioni",
        "account": "Account",
        "language": "Lingua",
        "security": "Sicurezza",
        "changePassword": "Cambia password",
        "notifications": "Notifiche",
        "privacy": "Privacy"
    }
}

def merge_translations(lang_code, new_trans):
    file_path = os.path.join(TRANSLATIONS_DIR, f"{lang_code}.json")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        existing = json.load(f)
    
    for section, translations in new_trans.items():
        if section not in existing:
            existing[section] = {}
        existing[section].update(translations)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Updated {lang_code}.json with {sum(len(v) for v in new_trans.values())} keys")

# Update all three languages
merge_translations("sw", SW_CORE)
merge_translations("fr", FR_CORE)
merge_translations("it", IT_CORE)

print("\n✓ Core translations added for Swahili, French, and Italian!")
print("Note: Full translations (682 strings) require professional translation service")
print("Current translations cover the most commonly used screens and actions")
