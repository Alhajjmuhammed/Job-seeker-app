"""
Add Phase 3 translation strings (all remaining untranslated content)
to all three .po files and recompile .mo files.
"""
import os
import polib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

NEW_TRANSLATIONS = {
    "sw": {
        # Trust bar descriptions
        "Every worker is ID-verified and approved by our admin team before going live": "Kila mfanyakazi anathibitishwa na timu yetu ya utawala kabla ya kuanza kazi",
        "Workers clock in and out \u2014 clients see progress in real time": "Wafanyakazi wanaingia na kutoka \u2014 wateja wanaona maendeleo wakati halisi",
        "Clients rate workers after each job, building a trusted, safe network": "Wateja wanakadiri wafanyakazi baada ya kila kazi, kujenga mtandao wa kuaminiwa na salama",
        "Full mobile support \u2014 post jobs and manage requests on the go": "Msaada kamili wa simu \u2014 chapisha kazi na usimamie maombi ukiwa njiani",
        # How It Works
        "From registration to review, every step is built to protect workers and clients alike.": "Kuanzia usajili hadi ukaguzi, kila hatua imejengwa kulinda wafanyakazi na wateja.",
        "Register & Build Your Profile": "Jiandikishe na Jenga Wasifu Wako",
        "Workers upload their national ID and skills. Clients set up company details. Takes just a few minutes to get started.": "Wafanyakazi wapakua kitambulisho cha taifa na ujuzi. Wateja wanasanidi maelezo ya kampuni. Inachukua dakika chache kuanza.",
        "Admin Verifies Workers": "Wasimamizi Wanathibitisha Wafanyakazi",
        "Every worker goes through our review process before appearing as available for hire. No unverified talent on the platform.": "Kila mfanyakazi anapitia mchakato wetu wa ukaguzi kabla ya kuonekana kama anapatikana kuajiriwa. Hakuna talanta isiyothibitishwa kwenye jukwaa.",
        "Post a Service Request": "Tuma Ombi la Huduma",
        "Clients describe the job, choose a category, set the location, date and duration \u2014 daily, monthly or custom.": "Wateja wanaelezea kazi, kuchagua kategoria, kuweka eneo, tarehe na muda \u2014 kila siku, kila mwezi au maalum.",
        "Admin Assigns the Right Worker": "Msimamizi Anateua Mfanyakazi Sahihi",
        "Our team matches the best verified worker to your request and notifies both parties instantly.": "Timu yetu inaunganisha mfanyakazi bora aliyethibitishwa na ombi lako na inawaarifu pande zote mara moja.",
        "Work Tracked Daily": "Kazi Inafuatiliwa Kila Siku",
        "Assigned workers clock in and out each day. Progress is fully visible to clients and admin at all times.": "Wafanyakazi waliowekwa wanaingia na kutoka kila siku. Maendeleo yanaonekana kikamilifu kwa wateja na wasimamizi wakati wote.",
        "Review After Completion": "Ukaguzi Baada ya Kukamilika",
        "Once the job is done, clients rate the worker. Reviews help surface the best professionals on the platform.": "Kazi ikisha, wateja wanakadiri mfanyakazi. Ukaguzi husaidia kuonyesha wataalamu bora kwenye jukwaa.",
        # About section
        "About Worker Connect": "Kuhusu Worker Connect",
        "Built for Tanzania's": "Imejengwa kwa Tanzania",
        "Growing Workforce": "Nguvu Kazi Inayokua",
        "Worker Connect is Tanzania's first dedicated platform bridging the gap between skilled professionals and the clients who need them \u2014 built to solve a real problem with a real digital solution.": "Worker Connect ni jukwaa la kwanza nchini Tanzania linalounganisha wataalamu wenye ujuzi na wateja wanaowahitaji \u2014 limejengwa kutatua tatizo la kweli na suluhisho la kidijitali.",
        "Fully Verified Network": "Mtandao Uliothibitishwa Kikamilifu",
        "Every worker is reviewed and approved by admin before going live on the platform.": "Kila mfanyakazi anakaguliwa na kuidhinishwa na msimamizi kabla ya kuanza kwenye jukwaa.",
        "Fast Job Matching": "Uwianishaji wa Kazi wa Haraka",
        "Clients post a job and receive a qualified, verified worker within hours.": "Wateja wanachapisha kazi na kupata mfanyakazi mwenye sifa na aliyethibitishwa ndani ya masaa machache.",
        "Agent-Powered Network": "Mtandao Unaodhibitiwa na Mawakala",
        "Agents recruit and support workers, building stronger local teams across Tanzania.": "Mawakala wanakusanya na kusaidia wafanyakazi, kujenga timu imara za ndani kote Tanzania.",
        "Mobile Ready": "Tayari kwa Simu",
        "Manage jobs, messages and requests from any device, anywhere in Tanzania.": "Simamia kazi, ujumbe na maombi kutoka kifaa chochote, popote Tanzania.",
        "Join the Platform": "Jiunge na Jukwaa",
        # About stats
        "Registered Workers": "Wafanyakazi Waliojisajili",
        "Client Satisfaction": "Kuridhika kwa Wateja",
        # App section
        "Mobile App": "Programu ya Simu",
        "Take Worker Connect": "Chukua Worker Connect",
        "Everywhere You Go": "Popote Uendapo",
        "Manage jobs, track work in real time, receive notifications and communicate with your team \u2014 all from your phone. Available free for both workers and clients.": "Simamia kazi, fuatilia kazi wakati halisi, pokea arifa na wasiliana na timu yako \u2014 yote kutoka simu yako. Inapatikana bure kwa wafanyakazi na wateja.",
        "Download on the": "Pakua kwenye",
        "App Store": "Duka la Programu",
        "Get it on": "Pata kwenye",
        "Google Play": "Google Play",
        "App coming soon \u2014 join the web platform today": "Programu inakuja hivi karibuni \u2014 jiunge na jukwaa la wavuti leo",
        # Roles section
        "One platform built for three types of users \u2014 each with their own dedicated experience.": "Jukwaa moja lililojengwa kwa aina tatu za watumiaji \u2014 kila mmoja na uzoefu wake maalum.",
        "Register, upload your documents, get verified by admin and start receiving job assignments from real clients.": "Jiandikishe, pakia hati zako, thibitishwa na msimamizi na uanze kupokea kazi kutoka kwa wateja wa kweli.",
        "Post service requests, get matched with a verified worker, and track daily progress \u2014 all in one dashboard.": "Tuma maombi ya huduma, pata mfanyakazi aliyethibitishwa, na ufuatilie maendeleo ya kila siku \u2014 yote kwenye dashibodi moja.",
        "Recruit workers, manage your team, earn commissions and grow your network through the dedicated agent portal.": "Kusanya wafanyakazi, simamia timu yako, pata kamisheni na ukue mtandao wako kupitia lango la wakala maalum.",
        # Footer
        "Tanzania's trusted platform connecting clients with verified, skilled professionals for every job \u2014 big or small.": "Jukwaa la kuaminika la Tanzania linalowasiliana wateja na wataalamu wenye ujuzi waliothshibitishwa kwa kila kazi \u2014 kubwa au ndogo.",
        "Platform": "Jukwaa",
        "Browse Services": "Angalia Huduma",
        "Browse Jobs": "Angalia Kazi",
        "Register": "Jiandikishe",
        "Join As": "Jiunge Kama",
        "Worker": "Mfanyakazi",
        "Client": "Mteja",
        "Agent": "Wakala",
        "Contact Us": "Wasiliana Nasi",
        "For Clients": "Kwa Wateja",
        "For Agents": "Kwa Mawakala",
        "Post a Job": "Chapisha Kazi",
    },
    "fr": {
        "Every worker is ID-verified and approved by our admin team before going live": "Chaque travailleur est v\u00e9rifi\u00e9 par notre \u00e9quipe avant d\u2019\u00eatre actif",
        "Workers clock in and out \u2014 clients see progress in real time": "Les travailleurs pointent \u2014 les clients voient la progression en temps r\u00e9el",
        "Clients rate workers after each job, building a trusted, safe network": "Les clients \u00e9valuent les travailleurs apr\u00e8s chaque travail, cr\u00e9ant un r\u00e9seau fiable et s\u00fbr",
        "Full mobile support \u2014 post jobs and manage requests on the go": "Support mobile complet \u2014 publiez des emplois et g\u00e9rez les demandes o\u00f9 que vous soyez",
        "From registration to review, every step is built to protect workers and clients alike.": "De l\u2019inscription \u00e0 l\u2019\u00e9valuation, chaque \u00e9tape est con\u00e7ue pour prot\u00e9ger les travailleurs et les clients.",
        "Register & Build Your Profile": "Inscrivez-vous et cr\u00e9ez votre profil",
        "Workers upload their national ID and skills. Clients set up company details. Takes just a few minutes to get started.": "Les travailleurs t\u00e9l\u00e9chargent leur pi\u00e8ce d\u2019identit\u00e9 et leurs comp\u00e9tences. Les clients configurent leurs informations d\u2019entreprise. Quelques minutes suffisent.",
        "Admin Verifies Workers": "L\u2019administrateur v\u00e9rifie les travailleurs",
        "Every worker goes through our review process before appearing as available for hire. No unverified talent on the platform.": "Chaque travailleur passe par notre processus de v\u00e9rification avant d\u2019\u00eatre disponible. Aucun talent non v\u00e9rifi\u00e9 sur la plateforme.",
        "Post a Service Request": "Publier une demande de service",
        "Clients describe the job, choose a category, set the location, date and duration \u2014 daily, monthly or custom.": "Les clients d\u00e9crivent le travail, choisissent une cat\u00e9gorie, d\u00e9finissent le lieu, la date et la dur\u00e9e \u2014 quotidien, mensuel ou personnalis\u00e9.",
        "Admin Assigns the Right Worker": "L\u2019administrateur assigne le bon travailleur",
        "Our team matches the best verified worker to your request and notifies both parties instantly.": "Notre \u00e9quipe associe le meilleur travailleur v\u00e9rifi\u00e9 \u00e0 votre demande et notifie les deux parties instantan\u00e9ment.",
        "Work Tracked Daily": "Travail suivi quotidiennement",
        "Assigned workers clock in and out each day. Progress is fully visible to clients and admin at all times.": "Les travailleurs assign\u00e9s pointent chaque jour. La progression est pleinement visible pour les clients et l\u2019admin en tout temps.",
        "Review After Completion": "\u00c9valuation apr\u00e8s ach\u00e8vement",
        "Once the job is done, clients rate the worker. Reviews help surface the best professionals on the platform.": "Une fois le travail termin\u00e9, les clients notent le travailleur. Les avis aident \u00e0 faire \u00e9merger les meilleurs professionnels.",
        "About Worker Connect": "\u00c0 propos de Worker Connect",
        "Built for Tanzania's": "Con\u00e7u pour la Tanzanie",
        "Growing Workforce": "Main-d\u2019\u0153uvre en croissance",
        "Worker Connect is Tanzania's first dedicated platform bridging the gap between skilled professionals and the clients who need them \u2014 built to solve a real problem with a real digital solution.": "Worker Connect est la premi\u00e8re plateforme d\u00e9di\u00e9e en Tanzanie comblant le foss\u00e9 entre professionnels qualifi\u00e9s et clients \u2014 con\u00e7ue pour r\u00e9soudre un probl\u00e8me r\u00e9el.",
        "Fully Verified Network": "R\u00e9seau enti\u00e8rement v\u00e9rifi\u00e9",
        "Every worker is reviewed and approved by admin before going live on the platform.": "Chaque travailleur est examin\u00e9 et approuv\u00e9 par l\u2019admin avant d\u2019\u00eatre actif sur la plateforme.",
        "Fast Job Matching": "Mise en relation rapide",
        "Clients post a job and receive a qualified, verified worker within hours.": "Les clients publient un emploi et re\u00e7oivent un travailleur qualifi\u00e9 et v\u00e9rifi\u00e9 en quelques heures.",
        "Agent-Powered Network": "R\u00e9seau propuls\u00e9 par les agents",
        "Agents recruit and support workers, building stronger local teams across Tanzania.": "Les agents recrutent et soutiennent les travailleurs, formant des \u00e9quipes locales plus fortes en Tanzanie.",
        "Mobile Ready": "Pr\u00eat pour mobile",
        "Manage jobs, messages and requests from any device, anywhere in Tanzania.": "G\u00e9rez les emplois, messages et demandes depuis n\u2019importe quel appareil, partout en Tanzanie.",
        "Join the Platform": "Rejoindre la plateforme",
        "Registered Workers": "Travailleurs inscrits",
        "Client Satisfaction": "Satisfaction client",
        "Mobile App": "Application mobile",
        "Take Worker Connect": "Emportez Worker Connect",
        "Everywhere You Go": "Partout o\u00f9 vous allez",
        "Manage jobs, track work in real time, receive notifications and communicate with your team \u2014 all from your phone. Available free for both workers and clients.": "G\u00e9rez les emplois, suivez le travail en temps r\u00e9el, recevez des notifications \u2014 tout depuis votre t\u00e9l\u00e9phone. Gratuit pour les travailleurs et les clients.",
        "Download on the": "T\u00e9l\u00e9charger sur",
        "App Store": "l\u2019App Store",
        "Get it on": "Disponible sur",
        "Google Play": "Google Play",
        "App coming soon \u2014 join the web platform today": "Application bient\u00f4t disponible \u2014 rejoignez la plateforme web aujourd\u2019hui",
        "One platform built for three types of users \u2014 each with their own dedicated experience.": "Une plateforme con\u00e7ue pour trois types d\u2019utilisateurs \u2014 chacun avec sa propre exp\u00e9rience d\u00e9di\u00e9e.",
        "Register, upload your documents, get verified by admin and start receiving job assignments from real clients.": "Inscrivez-vous, t\u00e9l\u00e9chargez vos documents, faites-vous v\u00e9rifier par l\u2019admin et commencez \u00e0 recevoir des missions de vrais clients.",
        "Post service requests, get matched with a verified worker, and track daily progress \u2014 all in one dashboard.": "Publiez des demandes de service, soyez mis en relation avec un travailleur v\u00e9rifi\u00e9 et suivez la progression quotidienne \u2014 tout sur un tableau de bord.",
        "Recruit workers, manage your team, earn commissions and grow your network through the dedicated agent portal.": "Recrutez des travailleurs, g\u00e9rez votre \u00e9quipe, gagnez des commissions et d\u00e9veloppez votre r\u00e9seau via le portail agent d\u00e9di\u00e9.",
        "Tanzania's trusted platform connecting clients with verified, skilled professionals for every job \u2014 big or small.": "La plateforme de confiance en Tanzanie connectant clients et professionnels qualifi\u00e9s v\u00e9rifi\u00e9s pour chaque travail \u2014 grand ou petit.",
        "Platform": "Plateforme",
        "Browse Services": "Parcourir les services",
        "Browse Jobs": "Parcourir les emplois",
        "Register": "S\u2019inscrire",
        "Join As": "Rejoindre en tant que",
        "Worker": "Travailleur",
        "Client": "Client",
        "Agent": "Agent",
        "Contact Us": "Nous contacter",
        "For Clients": "Pour les clients",
        "For Agents": "Pour les agents",
        "Post a Job": "Publier un emploi",
    },
    "it": {
        "Every worker is ID-verified and approved by our admin team before going live": "Ogni lavoratore \u00e8 verificato dal nostro team admin prima di essere attivo",
        "Workers clock in and out \u2014 clients see progress in real time": "I lavoratori timbrano entrata e uscita \u2014 i clienti vedono i progressi in tempo reale",
        "Clients rate workers after each job, building a trusted, safe network": "I clienti valutano i lavoratori dopo ogni lavoro, costruendo una rete affidabile e sicura",
        "Full mobile support \u2014 post jobs and manage requests on the go": "Supporto mobile completo \u2014 pubblica lavori e gestisci richieste ovunque tu sia",
        "From registration to review, every step is built to protect workers and clients alike.": "Dalla registrazione alla recensione, ogni passaggio \u00e8 progettato per proteggere lavoratori e clienti.",
        "Register & Build Your Profile": "Registrati e crea il tuo profilo",
        "Workers upload their national ID and skills. Clients set up company details. Takes just a few minutes to get started.": "I lavoratori caricano la carta d\u2019identit\u00e0 e le competenze. I clienti configurano i dati aziendali. Bastano pochi minuti.",
        "Admin Verifies Workers": "L\u2019admin verifica i lavoratori",
        "Every worker goes through our review process before appearing as available for hire. No unverified talent on the platform.": "Ogni lavoratore supera il nostro processo di verifica prima di essere disponibile. Nessun talento non verificato sulla piattaforma.",
        "Post a Service Request": "Pubblica una richiesta di servizio",
        "Clients describe the job, choose a category, set the location, date and duration \u2014 daily, monthly or custom.": "I clienti descrivono il lavoro, scelgono una categoria, impostano luogo, data e durata \u2014 giornaliera, mensile o personalizzata.",
        "Admin Assigns the Right Worker": "L\u2019admin assegna il lavoratore giusto",
        "Our team matches the best verified worker to your request and notifies both parties instantly.": "Il nostro team abbina il miglior lavoratore verificato alla tua richiesta e notifica entrambe le parti istantaneamente.",
        "Work Tracked Daily": "Lavoro monitorato quotidianamente",
        "Assigned workers clock in and out each day. Progress is fully visible to clients and admin at all times.": "I lavoratori assegnati timbrano ogni giorno. I progressi sono completamente visibili a clienti e admin in ogni momento.",
        "Review After Completion": "Recensione dopo il completamento",
        "Once the job is done, clients rate the worker. Reviews help surface the best professionals on the platform.": "Una volta terminato il lavoro, i clienti valutano il lavoratore. Le recensioni aiutano a far emergere i migliori professionisti.",
        "About Worker Connect": "Informazioni su Worker Connect",
        "Built for Tanzania's": "Costruito per la Tanzania",
        "Growing Workforce": "Forza lavoro in crescita",
        "Worker Connect is Tanzania's first dedicated platform bridging the gap between skilled professionals and the clients who need them \u2014 built to solve a real problem with a real digital solution.": "Worker Connect \u00e8 la prima piattaforma dedicata in Tanzania che colma il divario tra professionisti qualificati e clienti \u2014 costruita per risolvere un problema reale con una soluzione digitale reale.",
        "Fully Verified Network": "Rete completamente verificata",
        "Every worker is reviewed and approved by admin before going live on the platform.": "Ogni lavoratore viene esaminato e approvato dall\u2019admin prima di essere attivo sulla piattaforma.",
        "Fast Job Matching": "Corrispondenza di lavoro rapida",
        "Clients post a job and receive a qualified, verified worker within hours.": "I clienti pubblicano un lavoro e ricevono un lavoratore qualificato e verificato in poche ore.",
        "Agent-Powered Network": "Rete alimentata dagli agenti",
        "Agents recruit and support workers, building stronger local teams across Tanzania.": "Gli agenti reclutano e supportano i lavoratori, costruendo team locali pi\u00f9 forti in tutta la Tanzania.",
        "Mobile Ready": "Pronto per mobile",
        "Manage jobs, messages and requests from any device, anywhere in Tanzania.": "Gestisci lavori, messaggi e richieste da qualsiasi dispositivo, ovunque in Tanzania.",
        "Join the Platform": "Unisciti alla piattaforma",
        "Registered Workers": "Lavoratori registrati",
        "Client Satisfaction": "Soddisfazione del cliente",
        "Mobile App": "App mobile",
        "Take Worker Connect": "Porta Worker Connect",
        "Everywhere You Go": "Ovunque tu vada",
        "Manage jobs, track work in real time, receive notifications and communicate with your team \u2014 all from your phone. Available free for both workers and clients.": "Gestisci lavori, monitora il lavoro in tempo reale, ricevi notifiche e comunica con il tuo team \u2014 tutto dal tuo telefono. Disponibile gratuitamente per lavoratori e clienti.",
        "Download on the": "Scarica su",
        "App Store": "App Store",
        "Get it on": "Disponibile su",
        "Google Play": "Google Play",
        "App coming soon \u2014 join the web platform today": "App in arrivo \u2014 unisciti alla piattaforma web oggi",
        "One platform built for three types of users \u2014 each with their own dedicated experience.": "Una piattaforma costruita per tre tipi di utenti \u2014 ognuno con la propria esperienza dedicata.",
        "Register, upload your documents, get verified by admin and start receiving job assignments from real clients.": "Registrati, carica i tuoi documenti, vieni verificato dall\u2019admin e inizia a ricevere incarichi da clienti reali.",
        "Post service requests, get matched with a verified worker, and track daily progress \u2014 all in one dashboard.": "Pubblica richieste di servizio, abbinati a un lavoratore verificato e monitora i progressi giornalieri \u2014 tutto in una dashboard.",
        "Recruit workers, manage your team, earn commissions and grow your network through the dedicated agent portal.": "Recluta lavoratori, gestisci il tuo team, guadagna commissioni e fai crescere la tua rete tramite il portale agente dedicato.",
        "Tanzania's trusted platform connecting clients with verified, skilled professionals for every job \u2014 big or small.": "La piattaforma di fiducia della Tanzania che connette clienti con professionisti qualificati e verificati per ogni lavoro \u2014 grande o piccolo.",
        "Platform": "Piattaforma",
        "Browse Services": "Esplora servizi",
        "Browse Jobs": "Esplora lavori",
        "Register": "Registrati",
        "Join As": "Unisciti come",
        "Worker": "Lavoratore",
        "Client": "Cliente",
        "Agent": "Agente",
        "Contact Us": "Contattaci",
        "For Clients": "Per i clienti",
        "For Agents": "Per gli agenti",
        "Post a Job": "Pubblica un lavoro",
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
            print(f"  [{lang}] + {msgid[:70]}")
        else:
            print(f"  [{lang}] = exists: {msgid[:70]}")

    po.save(po_path)
    po.save_as_mofile(mo_path)
    print(f"  [{lang}] Saved: {added} new entries, .mo compiled.\n")


for lang, translations in NEW_TRANSLATIONS.items():
    print(f"\n=== {lang.upper()} ===")
    update_po_file(lang, translations)

print("Done! Restart the Django dev server for changes to take effect.")
