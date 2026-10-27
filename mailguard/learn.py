"""Learns from the mailbox: internal colleagues (name -> address), habitual domains and the sent mail index (for threads)."""
from __future__ import annotations
import collections
import json
import re
from .extract import msg_ids
from .outlook_client import Outlook, PR_INTERNET_MESSAGE_ID, PR_SMTP_ADDRESS, PR_TRANSPORT_HEADERS, OL_MAIL
from .i18n import t
from .paths import CONTACTS, KNOWN, SENT_INDEX
from .rules import FREEMAIL

OL_SENT = 5


def _dom(addr: str) -> str:
    a = (addr or "").lower()
    return a.rsplit("@", 1)[1] if "@" in a else ""


def _recipients(it) -> tuple[list[str], list[str]]:
    """(internal names -> address) and recipient domains of a sent mail."""
    names, domains = [], []
    for r in it.Recipients:
        try:
            ae = r.AddressEntry
            if ae.Type == "EX":
                ex = ae.GetExchangeUser()
                addr = ex.PrimarySmtpAddress if ex else ""
                if addr:
                    names.append((r.Name.strip().lower(), addr.lower()))
            else:
                addr = ae.Address
        except Exception:
            addr = r.Address
        d = _dom(addr)
        if d:
            domains.append(d)
    return names, domains


def refresh_sent_index(ol: Outlook, limit: int = 300) -> dict:
    """Updates sent_index.json with the latest sent mail: message-id -> recipient domains."""
    try:
        index = json.loads(SENT_INDEX.read_text(encoding="utf-8"))
    except Exception:
        index = {}
    sent = ol.store.GetDefaultFolder(OL_SENT).Items
    sent.Sort("[SentOn]", True)
    n = 0
    for it in sent:
        try:
            if it.Class != OL_MAIL:
                continue
            n += 1
            if n > limit:
                break
            mid = (msg_ids([ol._prop(it, PR_INTERNET_MESSAGE_ID)]) or [""])[0]
            if not mid or mid in index:
                continue
            _, domains = _recipients(it)
            index[mid] = sorted(set(domains))
        except Exception:
            pass
    if len(index) > 6000:
        index = dict(list(index.items())[-6000:])
    SENT_INDEX.write_text(json.dumps(index), encoding="utf-8")
    return index


def learn(ol: Outlook, own: set[str], progress=None, inbox_limit: int = 2000, sent_limit: int = 1500) -> tuple[dict, dict]:
    say = progress or (lambda s: None)
    names: dict[str, str] = {}
    sent_to: collections.Counter = collections.Counter()
    recv_ok: collections.Counter = collections.Counter()

    say(t("learn_sent"))
    sent = ol.store.GetDefaultFolder(OL_SENT).Items
    sent.Sort("[SentOn]", True)
    n = 0
    for it in sent:
        try:
            if it.Class != OL_MAIL:
                continue
            n += 1
            if n > sent_limit:
                break
            nm, domains = _recipients(it)
            for name, addr in nm:
                names[name] = addr
            for d in domains:
                if d not in own:
                    sent_to[d] += 1
        except Exception:
            pass
    refresh_sent_index(ol, limit=sent_limit)

    say(t("learn_inbox"))
    inbox = ol.inbox.Items
    inbox.Sort("[ReceivedTime]", True)
    n = 0
    for it in inbox:
        try:
            if it.Class != OL_MAIL:
                continue
            n += 1
            if n > inbox_limit:
                break
            if n % 200 == 0:
                say(t("learn_inbox_n", n=n))
            addr = ol._prop(it, PR_SMTP_ADDRESS)
            if (it.SenderEmailType or "").upper() == "EX":
                nm = (it.SenderName or "").strip().lower()
                if nm and addr:
                    names[nm] = addr.lower()
                continue
            d = _dom(addr)
            if not d or d in own:
                continue
            hdr = ol._prop(it, PR_TRANSPORT_HEADERS)
            m = re.search(r"Authentication-Results: mx\.microsoft\.com.*?(?=\r?\n\S)", hdr, re.S)
            ar = m.group(0) if m else ""
            if "dmarc=pass" in ar or ("spf=pass" in ar and "dkim=pass" in ar):
                recv_ok[d] += 1
        except Exception:
            pass

    known: dict[str, dict] = {}
    for d, c in sent_to.items():
        if d not in FREEMAIL:
            known[d] = {"sent": c, "received_auth_ok": recv_ok.get(d, 0)}
    for d, c in recv_ok.items():
        if c >= 2 and d not in known and d not in FREEMAIL:
            known[d] = {"sent": 0, "received_auth_ok": c}
    known = dict(sorted(known.items(), key=lambda kv: -(kv[1]["sent"] * 3 + kv[1]["received_auth_ok"])))

    CONTACTS.write_text(json.dumps(names, ensure_ascii=False, indent=1), encoding="utf-8")
    KNOWN.write_text(json.dumps(known, ensure_ascii=False, indent=1), encoding="utf-8")
    say(t("learn_done", names=len(names), domains=len(known)))
    return names, known
