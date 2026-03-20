"""
Add Phase 2 translation strings (landing page + login page content)
to all three .po files and recompile .mo files.
"""
import os
import polib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

NEW_TRANSLATIONS = {
    "sw": {
        "Tanzania's #1 Worker Platform": "Jukwaa la Kwanza la Wafanyakazi Tanzania",
        "Connect With": "Unganika Na",
        "Skilled Workers": "Wafanyakazi Wenye Ujuzi",
        "You Can Trust": "Unaoamini",
        "Post a job, hire a verified professional or find new work opportunities. Worker Connect brings clients, workers and agents together on one secure platform.": "Chapisha kazi, ajiri mtaalamu aliyethibitishwa au pata fursa mpya za kazi. Worker Connect inaunganisha wateja, wafanyakazi na mawakala kwenye jukwaa moja salama.",
        "Join for Free": "Jiunge Bila Malipo",
        "Request Service": "Omba Huduma",
        "Jobs Completed": "Kazi Zilizokamilika",
        "Service Categories": "Aina za Huduma",
        "Satisfaction Rate": "Kiwango cha Kuridhika",
        "Verified Workers": "Wafanyakazi Waliothibitishwa",
        "Daily Tracking": "Ufuatiliaji wa Kila Siku",
        "Honest Reviews": "Maoni ya Kweli",
        "Manage Anywhere": "Simamia Popote",
        "How It Works": "Jinsi Inavyofanya Kazi",
        "Simple, Transparent and Safe": "Rahisi, Wazi na Salama",
        "Choose Your Role": "Chagua Jukumu Lako",
        "Agent Portal": "Lango la Wakala",
        "Sign in": "Ingia",
        "Enter your credentials to continue": "Weka nambari zako ili uendelee",
        "Username": "Jina la Mtumiaji",
        "Password": "Nywila",
        "Remember me": "Nikumbuke",
        "Welcome": "Karibu",
        "Back": "Tena",
        "Sign in to access your dashboard, manage requests, and connect with workers or clients.": "Ingia kufikia dashibodi yako, simamia maombi, na kuwasiliana na wafanyakazi au wateja.",
        "Don't have an account?": "Huna akaunti?",
    },
    "fr": {
        "Tanzania's #1 Worker Platform": "La plateforme n\u00b01 des travailleurs en Tanzanie",
        "Connect With": "Connectez-vous avec",
        "Skilled Workers": "des travailleurs qualifi\u00e9s",
        "You Can Trust": "en qui vous pouvez avoir confiance",
        "Post a job, hire a verified professional or find new work opportunities. Worker Connect brings clients, workers and agents together on one secure platform.": "Publiez un emploi, embauchez un professionnel v\u00e9rifi\u00e9 ou trouvez de nouvelles opportunit\u00e9s. Worker Connect r\u00e9unit clients, travailleurs et agents sur une seule plateforme s\u00e9curis\u00e9e.",
        "Join for Free": "Rejoindre gratuitement",
        "Request Service": "Demander un service",
        "Jobs Completed": "Emplois termin\u00e9s",
        "Service Categories": "Cat\u00e9gories de services",
        "Satisfaction Rate": "Taux de satisfaction",
        "Verified Workers": "Travailleurs v\u00e9rifi\u00e9s",
        "Daily Tracking": "Suivi quotidien",
        "Honest Reviews": "Avis honn\u00eates",
        "Manage Anywhere": "G\u00e9rez de n\u2019importe o\u00f9",
        "How It Works": "Comment \u00e7a marche",
        "Simple, Transparent and Safe": "Simple, transparent et s\u00fbr",
        "Choose Your Role": "Choisissez votre r\u00f4le",
        "Agent Portal": "Portail agent",
        "Sign in": "Se connecter",
        "Enter your credentials to continue": "Entrez vos identifiants pour continuer",
        "Username": "Nom d\u2019utilisateur",
        "Password": "Mot de passe",
        "Remember me": "Se souvenir de moi",
        "Welcome": "Bienvenue",
        "Back": "Retour",
        "Sign in to access your dashboard, manage requests, and connect with workers or clients.": "Connectez-vous pour acc\u00e9der \u00e0 votre tableau de bord, g\u00e9rer les demandes et communiquer avec les travailleurs ou les clients.",
        "Don't have an account?": "Pas encore de compte\u00a0?",
    },
    "it": {
        "Tanzania's #1 Worker Platform": "La piattaforma n\u00b01 dei lavoratori in Tanzania",
        "Connect With": "Connettiti con",
        "Skilled Workers": "lavoratori qualificati",
        "You Can Trust": "di cui ti puoi fidare",
        "Post a job, hire a verified professional or find new work opportunities. Worker Connect brings clients, workers and agents together on one secure platform.": "Pubblica un lavoro, assumi un professionista verificato o trova nuove opportunit\u00e0 di lavoro. Worker Connect unisce clienti, lavoratori e agenti su un\u2019unica piattaforma sicura.",
        "Join for Free": "Unisciti gratuitamente",
        "Request Service": "Richiedi servizio",
        "Jobs Completed": "Lavori completati",
        "Service Categories": "Categorie di servizi",
        "Satisfaction Rate": "Tasso di soddisfazione",
        "Verified Workers": "Lavoratori verificati",
        "Daily Tracking": "Monitoraggio giornaliero",
        "Honest Reviews": "Recensioni oneste",
        "Manage Anywhere": "Gestisci ovunque",
        "How It Works": "Come funziona",
        "Simple, Transparent and Safe": "Semplice, trasparente e sicuro",
        "Choose Your Role": "Scegli il tuo ruolo",
        "Agent Portal": "Portale agente",
        "Sign in": "Accedi",
        "Enter your credentials to continue": "Inserisci le tue credenziali per continuare",
        "Username": "Nome utente",
        "Password": "Password",
        "Remember me": "Ricordami",
        "Welcome": "Benvenuto",
        "Back": "Indietro",
        "Sign in to access your dashboard, manage requests, and connect with workers or clients.": "Accedi per visualizzare il tuo cruscotto, gestire le richieste e comunicare con lavoratori o clienti.",
        "Don't have an account?": "Non hai un account?",
    },
}

def update_po_file(lang, translations):
    po_path = os.path.join(BASE_DIR, "locale", lang, "LC_MESSAGES", "django.po")
    mo_path = os.path.join(BASE_DIR, "locale", lang, "LC_MESSAGES", "django.mo")

    po = polib.pofile(po_path, encoding="utf-8")
    existing = {entry.msgid for entry in po}

    added = 0
    for msgid, msgstr in translations.items():
        if msgid not in existing:
            entry = polib.POEntry(msgid=msgid, msgstr=msgstr)
            po.append(entry)
            added += 1
            print(f"  [{lang}] + {msgid[:60]}")
        else:
            print(f"  [{lang}] = already exists: {msgid[:60]}")

    po.save(po_path)
    po.save_as_mofile(mo_path)
    print(f"  [{lang}] Saved: {added} new entries, .mo compiled.\n")


for lang, translations in NEW_TRANSLATIONS.items():
    print(f"\n=== {lang.upper()} ===")
    update_po_file(lang, translations)

print("Done! Restart the Django dev server for changes to take effect.")
