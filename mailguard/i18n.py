"""User facing strings in English and Italian. Call t(key, **values); set_language("en"|"it") switches at runtime."""
from __future__ import annotations

LANGUAGES = {"en": "English", "it": "Italiano"}
_current = "en"

STRINGS: dict[str, dict[str, str]] = {
    # ---------------------------------------------------------------- GUI
    "app_title": {"en": "MailGuard", "it": "MailGuard"},
    "tagline": {"en": "Checks incoming mail on your PC.\nNothing leaves this machine.",
                "it": "Analizza la posta in arrivo sul tuo PC.\nNessun dato esce da qui."},
    "outlook_unreachable": {"en": "not reachable", "it": "non raggiungibile"},
    "model_prefix": {"en": "AI model: ", "it": "Modello AI: "},
    "model_ready": {"en": "AI model ready", "it": "modello AI pronto"},
    "model_missing": {"en": "model not downloaded: rules only", "it": "modello non scaricato: solo regole"},
    "ollama_missing": {"en": "Ollama not installed: rules only", "it": "Ollama non installato: solo regole"},
    "btn_start": {"en": "Start protection", "it": "Avvia protezione"},
    "btn_stop": {"en": "Stop protection", "it": "Ferma protezione"},
    "btn_starting": {"en": "Starting...", "it": "Avvio in corso..."},
    "chk_apply": {"en": "Move phishing to Junk automatically\n(otherwise notify only)",
                  "it": "Sposta automaticamente in Posta indesiderata\n(altrimenti avvisa soltanto)"},
    "tab_activity": {"en": "  Activity  ", "it": "  Attivita'  "},
    "tab_settings": {"en": "  Settings  ", "it": "  Impostazioni  "},
    "tab_setup": {"en": "  Setup  ", "it": "  Installazione  "},
    "btn_scan50": {"en": "Analyse the last 50 mails", "it": "Analizza le ultime 50 mail"},
    "btn_samples": {"en": "Try with phishing samples", "it": "Prova con esempi di phishing"},
    "scan_hint": {"en": "(analysis moves nothing and sends no alerts)", "it": "(l'analisi non sposta nulla e non manda avvisi)"},
    "btn_clear": {"en": "Clear list", "it": "Svuota elenco"},
    "col_time": {"en": "Time", "it": "Ora"},
    "col_score": {"en": "Score", "it": "Punti"},
    "col_level": {"en": "Result", "it": "Esito"},
    "col_sender": {"en": "Sender", "it": "Mittente"},
    "col_subject": {"en": "Subject", "it": "Oggetto"},
    "col_action": {"en": "Action", "it": "Azione"},
    "level_ok": {"en": "ok", "it": "ok"},
    "level_suspect": {"en": "TO VERIFY", "it": "DA VERIFICARE"},
    "level_phishing": {"en": "PHISHING", "it": "PHISHING"},
    "sample_time": {"en": "sample", "it": "esempio"},
    "detail_frame": {"en": "Details and reasons", "it": "Dettaglio e motivi"},
    "btn_open": {"en": "Open in Outlook", "it": "Apri in Outlook"},
    "btn_safe": {"en": "Not phishing: trust this sender", "it": "Non e' phishing: fidati di questo mittente"},
    "btn_phish": {"en": "Phishing: move to Junk", "it": "E' phishing: sposta in spam"},
    "det_from": {"en": "From", "it": "Da"},
    "det_subject": {"en": "Subject", "it": "Oggetto"},
    "det_score": {"en": "Score", "it": "Punteggio"},
    "det_auth": {"en": "Authentication", "it": "Autenticazione"},
    "det_links": {"en": "Links to", "it": "Link verso"},
    "det_reasons": {"en": "Reasons:", "it": "Motivi:"},
    "det_trusted": {"en": "Trusted sender (colleague or habitual correspondent).", "it": "Mittente fidato (collega o corrispondente abituale)."},
    "set_mailbox": {"en": "Mailbox to protect", "it": "Casella di posta da proteggere"},
    "set_own": {"en": "Company domains (comma separated)", "it": "Domini aziendali (separati da virgola)"},
    "set_lists": {"en": "Domains or addresses, one per line\n(also filled by the buttons\n'Not phishing' / 'Phishing')",
                  "it": "Domini o indirizzi, uno per riga\n(si riempiono anche con i pulsanti\n'Non e' phishing' / 'E' phishing')"},
    "set_trusted": {"en": "Trusted (never flagged when authenticated)", "it": "Fidati (mai segnalati se autenticati)"},
    "set_blocked": {"en": "Blocked (always Junk)", "it": "Bloccati (sempre spam)"},
    "set_thresholds": {"en": "Score thresholds (0-100)", "it": "Soglie del punteggio (0-100)"},
    "set_suspect": {"en": "to verify >=", "it": "da verificare >="},
    "set_phishing": {"en": "phishing >=", "it": "phishing >="},
    "set_notify": {"en": "Windows notifications", "it": "Notifiche Windows"},
    "set_notify_chk": {"en": "show an alert when a mail is flagged", "it": "mostra un avviso quando una mail viene segnalata"},
    "set_analysis": {"en": "Analysis", "it": "Analisi"},
    "set_model_ollama": {"en": "Rules + local AI model (recommended)", "it": "Regole + modello AI locale (consigliato)"},
    "set_model_none": {"en": "Rules only (faster, less accurate)", "it": "Solo regole (piu' veloce, meno preciso)"},
    "set_ollama_model": {"en": "Ollama model name", "it": "Nome del modello Ollama"},
    "set_company": {"en": "Company name (helps the model know\nwhat normal mail looks like for you)",
                    "it": "Nome azienda (aiuta il modello a capire\nquali mail sono normali per voi)"},
    "set_sector": {"en": "  sector:", "it": "  settore:"},
    "set_language": {"en": "Language", "it": "Lingua"},
    "set_autostart": {"en": "Autostart", "it": "Avvio automatico"},
    "set_autostart_chk": {"en": "start MailGuard at Windows logon (minimised to the tray)",
                          "it": "avvia MailGuard all'accesso a Windows (ridotto a icona)"},
    "btn_save": {"en": "Save settings", "it": "Salva impostazioni"},
    "btn_learn": {"en": "Re-read colleagues and correspondents from the mailbox", "it": "Rileggi colleghi e corrispondenti dalla casella"},
    "data_dir": {"en": "Data and log are in: {dir}", "it": "I dati e il registro sono in: {dir}"},
    "saved": {"en": "Settings saved.", "it": "Impostazioni salvate."},
    "autostart_title": {"en": "Autostart", "it": "Avvio automatico"},
    "autostart_err": {"en": "Cannot create the shortcut: {err}", "it": "Non riesco a creare il collegamento: {err}"},
    "setup_title": {"en": "Guided setup", "it": "Installazione guidata"},
    "setup_intro": {"en": "MailGuard works right away with rules only. The smart analysis needs Ollama (free) and a local model.",
                    "it": "MailGuard funziona subito con le sole regole. Per l'analisi intelligente serve Ollama (gratuito) e un modello locale."},
    "step_outlook": {"en": "1. Classic Outlook open with the mailbox configured", "it": "1. Outlook classico aperto con la casella configurata"},
    "step_ollama": {"en": "2. Ollama installed (engine for local AI models)", "it": "2. Ollama installato (motore per modelli AI locali)"},
    "step_model": {"en": "3. AI model downloaded (about 2.5 GB, once)", "it": "3. Modello AI scaricato (circa 2,5 GB, una volta sola)"},
    "step_contacts": {"en": "4. Colleagues and correspondents learned from the mailbox", "it": "4. Colleghi e corrispondenti imparati dalla casella"},
    "btn_install_ollama": {"en": "Install Ollama", "it": "Installa Ollama"},
    "btn_pull": {"en": "Download the model", "it": "Scarica il modello"},
    "btn_learn_now": {"en": "Learn now", "it": "Impara ora"},
    "btn_recheck": {"en": "Check again", "it": "Ricontrolla"},
    "progress": {"en": "Progress", "it": "Avanzamento"},
    "ready": {"en": "Ready.", "it": "Pronto."},
    "apply_on": {"en": "Mails flagged as phishing will be moved to Junk.", "it": "Le mail segnalate come phishing verranno spostate in Posta indesiderata."},
    "apply_off": {"en": "Alerts only: no mail is moved.", "it": "Modalita' solo avvisi: nessuna mail viene spostata."},
    "tray_hidden": {"en": "MailGuard keeps working from the tray icon.", "it": "MailGuard continua a lavorare dall'icona nella barra di sistema."},
    "confirm_safe_title": {"en": "Trusted sender", "it": "Mittente fidato"},
    "confirm_safe": {"en": "Add {who} to the trusted list and move the mail back to the Inbox?",
                     "it": "Aggiungere {who} ai fidati e rimettere la mail in Posta in arrivo?"},
    "confirm_phish_title": {"en": "Phishing", "it": "Phishing"},
    "confirm_phish": {"en": "Move this mail to Junk?", "it": "Spostare questa mail in Posta indesiderata?"},
    "action_user_trusted": {"en": "trusted by user", "it": "fidato dall'utente"},
    "action_user_moved": {"en": "moved by user", "it": "spostata dall'utente"},
    "tray_open": {"en": "Open MailGuard", "it": "Apri MailGuard"},
    "tray_quit": {"en": "Quit", "it": "Esci"},
    "tray_active": {"en": "MailGuard, protection active", "it": "MailGuard, protezione attiva"},
    "tray_paused": {"en": "MailGuard, paused", "it": "MailGuard, in pausa"},
    "outlook_err": {"en": "Outlook not reachable: {err}", "it": "Outlook non raggiungibile: {err}"},
    "restart_hint": {"en": "Language changes apply after restarting MailGuard.", "it": "La lingua cambia al prossimo avvio di MailGuard."},
    # ---------------------------------------------------------------- engine
    "eng_ollama_not_running": {"en": "Ollama is not running: using rules only.", "it": "Ollama non e' in esecuzione: uso solo le regole."},
    "eng_model_missing": {"en": "Model {name} not downloaded: using rules only (see Setup).", "it": "Modello {name} non scaricato: uso solo le regole (vai in Installazione)."},
    "eng_loading_model": {"en": "Loading the model into memory (the first time can take 1-2 minutes)...", "it": "Carico il modello in memoria (la prima volta puo' richiedere 1-2 minuti)..."},
    "eng_model_ready": {"en": "Model ready ({s}s).", "it": "Modello pronto ({s}s)."},
    "eng_model_failed": {"en": "Model not responding: {err}. Using rules only.", "it": "Modello non risponde: {err}. Uso solo le regole."},
    "eng_model_err_mail": {"en": "Model unavailable on this mail: {err}", "it": "Modello non disponibile su questa mail: {err}"},
    "eng_scan_start": {"en": "Analysing the last {n} mails in '{folder}'...", "it": "Analizzo le ultime {n} mail di '{folder}'..."},
    "eng_scan_done": {"en": "Done: {ok} ok, {suspect} to verify, {phishing} phishing.", "it": "Fatto: {ok} ok, {suspect} da verificare, {phishing} phishing."},
    "eng_samples_done": {"en": "Samples: {ok}/{n} correct.", "it": "Esempi: {ok}/{n} corretti."},
    "eng_sample_action": {"en": "expected {expected} -> {result}", "it": "atteso {expected} -> {result}"},
    "result_ok": {"en": "OK", "it": "OK"},
    "result_err": {"en": "ERROR", "it": "ERRORE"},
    "eng_first_learn": {"en": "First run: learning colleagues and correspondents from the mailbox...", "it": "Prima volta: imparo colleghi e corrispondenti dalla casella..."},
    "eng_listening": {"en": "Listening for new mail ({mode}).", "it": "In ascolto sulle nuove mail ({mode})."},
    "mode_apply": {"en": "moving phishing to Junk", "it": "sposto in spam"},
    "mode_alert": {"en": "alerts only", "it": "solo avvisi"},
    "eng_stopped": {"en": "Listening stopped.", "it": "Ascolto fermato."},
    "eng_loop_err": {"en": "Error in the loop, retrying: {err}", "it": "Errore nel ciclo, riprovo: {err}"},
    "eng_sent_index_err": {"en": "Sent mail index not updated: {err}", "it": "Indice posta inviata non aggiornato: {err}"},
    "eng_move_err": {"en": "Cannot move the mail: {err}", "it": "Non riesco a spostare la mail: {err}"},
    "eng_trusted_added": {"en": "Ok: {who} added to the trusted list.", "it": "Ok: {who} aggiunto ai fidati."},
    "eng_blocked_domain": {"en": "Domain {d} blocked: future mail from it goes straight to Junk.", "it": "Dominio {d} bloccato: le prossime mail da li' vanno dritte in spam."},
    "eng_blocked_sender": {"en": "Sender {addr} blocked.", "it": "Mittente {addr} bloccato."},
    "eng_moved_junk": {"en": "Moved to Junk.", "it": "Spostata in Posta indesiderata."},
    "eng_error": {"en": "Error: {err}", "it": "Errore: {err}"},
    "act_none": {"en": "none", "it": "nessuna"},
    "act_junk": {"en": "moved to Junk", "it": "spostata in Posta indesiderata"},
    "act_folder": {"en": "moved to '{f}'", "it": "spostata in '{f}'"},
    "act_cat_phish": {"en": "phishing category", "it": "categoria phishing"},
    "act_suspect": {"en": "marked to verify", "it": "segnata da verificare"},
    "act_simulated": {"en": "alert only ({desc})", "it": "solo avviso ({desc})"},
    "ntf_phish_title": {"en": "MailGuard: PHISHING blocked", "it": "MailGuard: PHISHING bloccato"},
    "ntf_suspect_title": {"en": "MailGuard: mail to verify", "it": "MailGuard: mail da verificare"},
    "ntf_body": {"en": "From: {addr}\nSubject: {subject}\n{action}\nWhy: {why}", "it": "Da: {addr}\nOggetto: {subject}\n{action}\nPerche': {why}"},
    "cat_suspect": {"en": "MailGuard: to verify", "it": "MailGuard: da verificare"},
    "cat_phishing": {"en": "MailGuard: phishing", "it": "MailGuard: phishing"},
    "inst_present": {"en": "Ollama is already installed.", "it": "Ollama e' gia' installato."},
    "inst_winget": {"en": "Installing Ollama with winget (this can take a few minutes)...", "it": "Installo Ollama con winget (puo' richiedere qualche minuto)..."},
    "inst_done": {"en": "Ollama installed.", "it": "Ollama installato."},
    "inst_winget_rc": {"en": "winget returned {rc}.", "it": "winget ha restituito {rc}."},
    "inst_browser": {"en": "Opening the Ollama download page: install it, then press the button again.", "it": "Apro la pagina di download di Ollama: installalo e poi premi di nuovo il pulsante."},
    "pull_no_ollama": {"en": "Ollama not found.", "it": "Ollama non trovato."},
    "pull_no_server": {"en": "Cannot start the Ollama server.", "it": "Non riesco ad avviare il server Ollama."},
    "pull_start": {"en": "Downloading model {name} (about 2.5 GB, only once)...", "it": "Scarico il modello {name} (circa 2,5 GB, solo la prima volta)..."},
    "pull_done": {"en": "Model ready.", "it": "Modello pronto."},
    "pull_fail": {"en": "Download failed (code {rc}).", "it": "Download non riuscito (codice {rc})."},
    "learn_sent": {"en": "Reading sent mail...", "it": "Leggo la posta inviata..."},
    "learn_inbox": {"en": "Reading received mail...", "it": "Leggo la posta ricevuta..."},
    "learn_inbox_n": {"en": "Reading received mail... {n}", "it": "Leggo la posta ricevuta... {n}"},
    "learn_done": {"en": "Learned {names} colleagues and {domains} habitual domains", "it": "Imparati {names} colleghi e {domains} domini abituali"},
    # ---------------------------------------------------------------- rules and scorer (reasons shown to the user)
    "r_blocked_sender": {"en": "Sender {addr} reported as phishing by you", "it": "Mittente {addr} segnalato come phishing dall'utente"},
    "r_blocked_domain": {"en": "Domain {d} reported as phishing by you", "it": "Dominio {d} segnalato come phishing dall'utente"},
    "r_thread_hijack": {"en": "Replies to one of your conversations but from a domain ({d}) you never wrote to",
                        "it": "Risponde a una tua conversazione ma da un dominio ({d}) a cui non avevi scritto"},
    "r_spf_fail": {"en": "SPF {res}: the sending server is not authorised for the domain", "it": "SPF {res}: il server che ha inviato la mail non e' autorizzato per il dominio"},
    "r_dkim_fail": {"en": "DKIM failed: the mail signature does not match", "it": "DKIM fallito: la firma della mail non corrisponde"},
    "r_dmarc_fail": {"en": "DMARC failed: the sender does not pass its own domain checks", "it": "DMARC fallito: il mittente non supera i controlli del suo dominio"},
    "r_compauth_fail": {"en": "Microsoft (compauth) reports failed composite authentication", "it": "Microsoft (compauth) segnala autenticazione composita fallita"},
    "r_spoof_own": {"en": "Pretends to come from our domain {d} but arrives from outside without authentication",
                    "it": "Finge di arrivare dal nostro dominio {d} ma viene da fuori senza autenticazione"},
    "r_sender_malformed": {"en": "Obfuscated or malformed sender address ({local}...@{d})", "it": "Indirizzo mittente offuscato o malformato ({local}...@{d})"},
    "r_replyto_mismatch": {"en": "Reply-To points to a different domain ({rt}) than the sender {d}", "it": "Reply-To verso dominio diverso ({rt}) rispetto al mittente {d}"},
    "r_name_has_other_email": {"en": "The display name contains an address ({name}) different from the real sender {addr}",
                               "it": "Il nome visualizzato contiene un indirizzo ({name}) diverso dal mittente reale {addr}"},
    "r_brand_in_name": {"en": "The name '{name}' evokes {brand} but the sender is {d}", "it": "Il nome '{name}' richiama {brand} ma il mittente e' {d}"},
    "r_sender_lookalike": {"en": "Sender domain {d} imitates {target}", "it": "Dominio mittente {d} imita {target}"},
    "r_colleague_external": {"en": "The name '{name}' belongs to a colleague ({hit}) but the mail comes from {addr}",
                             "it": "Il nome '{name}' e' di un collega ({hit}) ma la mail arriva da {addr}"},
    "r_freemail_corporate": {"en": "Free mail address ({d}) with a name that looks corporate or institutional",
                             "it": "Indirizzo gratuito ({d}) con nome che sembra aziendale/istituzionale"},
    "r_unknown_lure": {"en": "Never seen sender ({d}) asking to sign in, verify or pay ('{word}') with a link",
                       "it": "Mittente mai visto ({d}) che chiede di accedere/verificare/pagare ('{word}') con un link"},
    "r_generic_sender": {"en": "Generic automated address ({local}) from an unknown domain", "it": "Indirizzo automatico generico ({local}) da un dominio sconosciuto"},
    "r_link_text_mismatch": {"en": "Link shows '{shown}' but leads to {real}", "it": "Link mostra '{shown}' ma porta a {real}"},
    "r_link_redirect": {"en": "Link goes through {n} Google redirect(s) to hide the real destination ({d})",
                        "it": "Link che passa da {n} redirect di Google per nascondere la destinazione reale ({d})"},
    "r_link_ip": {"en": "Link to a raw IP address ({ip})", "it": "Link verso un indirizzo IP ({ip})"},
    "r_link_shortener": {"en": "Shortened links ({list}): the real destination is hidden", "it": "Link accorciati ({list}): la destinazione reale e' nascosta"},
    "r_link_lookalike": {"en": "Link to {d} which imitates {target}", "it": "Link verso {d} che imita {target}"},
    "r_many_domains": {"en": "{n} different domains in the links", "it": "{n} domini diversi nei link"},
    "r_attachment": {"en": "Potentially dangerous attachment: {name}", "it": "Allegato potenzialmente pericoloso: {name}"},
    "r_own_thread": {"en": "Reply to a mail you sent to this domain", "it": "Risposta a una mail che avevi inviato tu a questo dominio"},
    "r_internal": {"en": "Authenticated internal sender", "it": "Mittente interno autenticato"},
    "r_trusted": {"en": "Trusted domain ({d}) with DMARC ok", "it": "Dominio fidato ({d}) con DMARC ok"},
    "s_model_prob": {"en": "The model estimates a {p} probability of phishing or scam", "it": "Il modello stima {p} di probabilita' che sia phishing/truffa"},
}


def set_language(code: str):
    global _current
    _current = code if code in LANGUAGES else "en"


def language() -> str:
    return _current


def t(key: str, **kw) -> str:
    entry = STRINGS.get(key)
    if not entry:
        return key
    s = entry.get(_current) or entry.get("en") or key
    try:
        return s.format(**kw) if kw else s
    except (KeyError, IndexError):
        return s


def detect_language() -> str:
    """Language chosen by the installer (registry), otherwise the Windows UI language."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\MailGuard") as k:
            val, _ = winreg.QueryValueEx(k, "Language")
            if val in LANGUAGES:
                return val
    except Exception:
        pass
    try:
        import ctypes
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
        return "it" if lang_id == 0x10 else "en"
    except Exception:
        return "en"
