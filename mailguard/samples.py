"""Synthetic mails (invented) to exercise the pipeline without Outlook: python -m mailguard test"""
from __future__ import annotations
from .extract import Auth, Link, Mail, reg_domain


def _mk(subject, name, addr, body, links=(), atts=(), spf="pass", dkim="pass", dmarc="pass", reply_to=(), stype="SMTP"):
    ls = [Link(href=h, text=t, href_domain=reg_domain(h), text_domain=reg_domain(td) if td else "") for h, t, td in links]
    return Mail(entry_id="test", subject=subject, sender_name=name, sender_addr=addr, sender_type=stype,
                reply_to=list(reply_to), body=body, links=ls, attachments=list(atts),
                auth=Auth(spf=spf, dkim=dkim, dmarc=dmarc), received="2026-10-27T10:00")


def samples(own_domain: str, colleague: str) -> list[tuple[str, Mail]]:
    """`own_domain` is the company domain, `colleague` the lower case name of a colleague present in the contacts."""
    col_title = colleague.title()
    col_local = colleague.replace(" ", ".")
    return [
        ("PHISHING", _mk(
            "Il tuo account Microsoft 365 verra' sospeso",
            "Microsoft Support", "support@m1crosoft-verify.com",
            "Gentile utente,\nabbiamo rilevato un accesso anomalo al tuo account. Per evitare la sospensione, verifica la tua identita' "
            "entro 24 ore cliccando sul link sottostante e inserendo le tue credenziali.\nGrazie,\nMicrosoft Security Team",
            links=[("https://login.m1crosoft-verify.com/auth", "Verifica account", "")], spf="fail", dkim="none", dmarc="fail")),
        ("PHISHING", _mk(
            "Spedizione in attesa: paga le spese doganali",
            "DHL Express", "noreply@dhl-tracking-it.com",
            "La tua spedizione n. 48812993 e' bloccata in dogana. Paga 2,99 EUR entro oggi per sbloccare la consegna.",
            links=[("https://bit.ly/3xk2", "dhl.com/tracking", "dhl.com")], spf="softfail", dkim="none", dmarc="none")),
        ("PHISHING", _mk(
            "Fattura n. 2026/1187 - pagamento urgente",
            "Amministrazione", f"amministrazione@{own_domain}",
            "Buongiorno, in allegato la fattura. Vi preghiamo di pagare entro oggi sul nuovo IBAN comunicato. Cordiali saluti.",
            atts=["Fattura_1187.html"], spf="fail", dkim="none", dmarc="fail")),
        ("PHISHING", _mk(
            "Documento condiviso con te",
            "SharePoint Online", "no-reply@docs-share-online.net",
            "Hai ricevuto un documento riservato. Accedi con il tuo account aziendale per visualizzarlo.",
            links=[("https://docs-share-online.net/view?id=991", "Apri documento", "")], spf="pass", dkim="pass", dmarc="none")),
        ("PHISHING", _mk(
            "Richiesta urgente",
            col_title, f"{col_local}.ceo@gmail.com",
            "Ciao, sono in riunione e non posso parlare. Mi serve che fai un bonifico urgente a un fornitore oggi stesso. "
            "Ti mando i dati appena mi confermi. Non dirlo a nessuno per ora.",
            spf="pass", dkim="pass", dmarc="pass")),
        ("LEGIT", _mk(
            "R: Piano di consegna e call con il fornitore",
            "Luca Ferrari", "l.ferrari@acme-components.example",
            "Buongiorno,\nconfermo la call di giovedi' alle 10 per rivedere il piano di consegna del lotto 2610006/7. "
            "In allegato il programma aggiornato.\nCordiali saluti,\nLuca",
            links=[("https://www.acme-components.example", "acme-components.example", "acme-components.example")], atts=["Piano_consegna.xlsx"])),
        ("LEGIT", _mk(
            "Dettaglio ordini giornaliero",
            "Report automatico", f"report@{own_domain}",
            "Report automatico ordini del giorno in allegato.", atts=["dettaglio_ordini_gg.pdf"], spf="none", dkim="none", dmarc="none", stype="EX")),
        ("LEGIT", _mk(
            "Newsletter ottobre: novita' sui materiali compostabili",
            "Plastics Today", "newsletter@plasticstoday.com",
            "Scopri le ultime novita' del settore. Leggi l'articolo completo sul nostro sito. Per disiscriverti clicca qui.",
            links=[("https://www.plasticstoday.com/article/1", "Leggi", ""), ("https://www.plasticstoday.com/unsub", "Disiscriviti", "")])),
        ("LEGIT", _mk(
            "Conferma ordine OF0006124",
            "Giulia Conti", "g.conti@acme-components.example",
            "Buongiorno, confermiamo la ricezione dell'ordine OF0006124. La consegna e' prevista per il 15/11. Restiamo a disposizione.")),
    ]
