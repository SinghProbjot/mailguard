"""Deterministic checks: the things a model does badly (string comparisons, headers, extensions)."""
from __future__ import annotations
from dataclasses import dataclass
from .extract import Mail, reg_domain
from .i18n import t

FREEMAIL = {"gmail.com", "outlook.com", "hotmail.com", "hotmail.it", "live.com", "live.it", "yahoo.com", "yahoo.it",
            "libero.it", "virgilio.it", "tiscali.it", "alice.it", "icloud.com", "protonmail.com", "proton.me", "mail.com",
            "gmx.com", "gmx.de", "aol.com", "yandex.com", "web.de"}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "cutt.ly", "rebrand.ly", "is.gd", "ow.ly", "shorturl.at", "rb.gy", "tiny.cc", "goo.gl", "lnkd.in"}
DANGEROUS_EXT = {
    "html": 30, "htm": 30, "shtml": 30, "svg": 30, "lnk": 30, "iso": 30, "img": 30, "vhd": 30, "exe": 30, "scr": 30,
    "js": 30, "jse": 30, "vbs": 30, "wsf": 30, "hta": 30, "bat": 30, "cmd": 30, "msi": 30, "one": 25,
    "zip": 12, "rar": 12, "7z": 12, "docm": 15, "xlsm": 15, "pptm": 15,
}
LURE_WORDS = (
    # italiano
    "accedi", "verifica il tuo", "verifica la tua", "password", "credenziali", "login", "documento condiviso", "ha condiviso",
    "nuovo iban", "aggiorna i dati", "conferma il pagamento", "account sospeso", "account bloccato", "scadra'", "scadrà", "entro 24", "entro 48",
    "apri il documento", "visualizza documento", "fattura in allegato", "pagamento in sospeso",
    # english
    "sign in", "log in", "shared document", "shared a file", "documents are available", "your documents", "view document", "open files",
    "view files", "access your", "review document", "secure message", "e-sign", "esign", "verify your", "update your", "password expire",
    "mailbox", "storage full", "payment pending", "remittance", "wire transfer", "click here to view", "download attachment",
)
GENERIC_LOCALS = ("no-reply", "noreply", "no_reply", "donotreply", "notification", "notifications", "alert", "alerts", "docs", "documents",
                  "share", "sharing", "efax", "fax", "voicemail", "secure", "admin", "mailer")
_ADDR_JUNK = set("?&/%=#")


@dataclass
class Finding:
    code: str
    points: int
    reason: str      # one sentence the user will read


def _lev(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _lookalike(domain: str, targets: set[str], strict_tld: set[str] = frozenset()) -> str | None:
    """Returns the imitated domain when `domain` is similar but different (typosquatting, suffixes).
    A different TLD (company.com vs company.it) counts only for domains in `strict_tld` (our own): brands use national TLDs legitimately."""
    if not domain or domain in targets:
        return None
    base = domain.split(".")[0]
    if len(base) < 5:
        return None
    for tg in targets:
        tb = tg.split(".")[0]
        if len(tb) < 5:
            continue
        if base == tb:
            return tg if tg in strict_tld else None
        if _lev(base, tb) <= (1 if len(tb) <= 8 else 2):
            return tg
        if tb in base and base != tb and len(base) - len(tb) <= 8:   # company-portal
            return tg
    return None


def is_internal(m: Mail, cfg: dict) -> bool:
    own = {d.lower() for d in cfg["own_domains"]}
    if m.sender_type == "EX" or not m.sender_addr:      # no sender = draft or a mail written by the user
        return True
    return m.sender_domain in own and m.auth.spf in ("", "pass", "none") and m.auth.dmarc != "fail"


def thread_state(m: Mail, cfg: dict) -> str:
    """'own_thread' when replying to a mail the user sent to that domain, 'hijack' when replying to one of the user's
    threads from a domain the user never wrote to, '' otherwise."""
    index: dict = cfg.get("_sent_index", {})
    if not index or not m.in_reply_to:
        return ""
    for mid in m.in_reply_to:
        doms = index.get(mid)
        if doms is None:
            continue
        own = {d.lower() for d in cfg["own_domains"]}
        if m.sender_domain in doms or m.sender_domain in own:
            return "own_thread"
        return "hijack"
    return ""


def run_rules(m: Mail, cfg: dict) -> list[Finding]:
    f: list[Finding] = []
    own = {d.lower() for d in cfg["own_domains"]}
    trusted = {d.lower() for d in cfg.get("trusted_domains", [])}
    brands: dict[str, list[str]] = cfg.get("brands", {})
    brand_domains = {d for ds in brands.values() for d in ds}
    internal = is_internal(m, cfg)

    # --- blocked by the user ---
    if m.sender_addr.lower() in {s.lower() for s in cfg.get("blocked_senders", [])}:
        f.append(Finding("blocked_sender", 100, t("r_blocked_sender", addr=m.sender_addr)))
    elif m.sender_domain in {d.lower() for d in cfg.get("blocked_domains", [])}:
        f.append(Finding("blocked_domain", 100, t("r_blocked_domain", d=m.sender_domain)))

    # --- thread ---
    ts = thread_state(m, cfg)
    if ts == "hijack":
        f.append(Finding("thread_hijack", 30, t("r_thread_hijack", d=m.sender_domain)))

    # --- authentication ---
    if m.auth.spf in ("fail", "softfail"):
        f.append(Finding("spf_fail", 20, t("r_spf_fail", res=m.auth.spf)))
    if m.auth.dkim == "fail":
        f.append(Finding("dkim_fail", 10, t("r_dkim_fail")))
    if m.auth.dmarc == "fail":
        f.append(Finding("dmarc_fail", 25, t("r_dmarc_fail")))
    if m.auth.compauth == "fail":
        f.append(Finding("compauth_fail", 15, t("r_compauth_fail")))
    if m.sender_type != "EX" and m.sender_domain in own and m.auth.spf in ("fail", "softfail", "none") and m.auth.dmarc != "pass":
        f.append(Finding("spoof_own", 35, t("r_spoof_own", d=m.sender_domain)))

    # --- sender ---
    name_l = m.sender_name.lower()
    local = m.sender_addr.rsplit("@", 1)[0] if "@" in m.sender_addr else ""
    if local and (len(local) > 40 or any(c in _ADDR_JUNK for c in local)):
        f.append(Finding("sender_malformed", 30, t("r_sender_malformed", local=local[:30], d=m.sender_domain)))
    if m.reply_to_domains and any(d != m.sender_domain for d in m.reply_to_domains):
        f.append(Finding("replyto_mismatch", 15, t("r_replyto_mismatch", rt=", ".join(m.reply_to_domains), d=m.sender_domain)))
    if "@" in name_l:
        nd = reg_domain(name_l)
        if nd and nd != m.sender_domain:
            f.append(Finding("name_has_other_email", 20, t("r_name_has_other_email", name=name_l, addr=m.sender_addr)))
    if not internal:
        for brand, doms in brands.items():
            if brand in name_l and m.sender_domain not in doms and m.sender_domain not in own:
                f.append(Finding("brand_in_name", 25, t("r_brand_in_name", name=m.sender_name, brand=brand, d=m.sender_domain)))
                break
    la = _lookalike(m.sender_domain, own | brand_domains, strict_tld=own)
    if la:
        f.append(Finding("sender_lookalike", 35, t("r_sender_lookalike", d=m.sender_domain, target=la)))
    # colleague's name on an external address (CEO fraud, fake colleague)
    contacts: dict[str, str] = cfg.get("_contacts", {})
    if not internal and m.sender_domain not in own and contacts:
        nm = " ".join(name_l.replace(",", " ").split())
        hit = contacts.get(nm)
        if not hit:
            parts = [p for p in nm.split() if len(p) > 2]
            if len(parts) >= 2:
                for cname, caddr in contacts.items():
                    cp = set(cname.split())
                    if parts[0] in cp and parts[-1] in cp:
                        hit = caddr
                        break
        if hit:
            f.append(Finding("colleague_name_external", 40, t("r_colleague_external", name=m.sender_name, hit=hit, addr=m.sender_addr)))
    if m.sender_domain in FREEMAIL and not internal:
        corp_words = ("srl", "spa", "s.r.l", "s.p.a", "ltd", "llc", "inc", "gmbh", "ufficio", "amministrazione", "contabilit", "direzione",
                      "ceo", "support", "service", "team", "billing", "accounts", "finance", "hr")
        if any(w in name_l for w in corp_words) or any(b in name_l for b in brands):
            f.append(Finding("freemail_corporate", 15, t("r_freemail_corporate", d=m.sender_domain)))

    # --- never seen sender asking to sign in or pay ---
    known: dict = cfg.get("_known_domains", {})
    unknown = not internal and m.sender_domain not in known and m.sender_domain not in trusted and m.sender_domain not in brand_domains
    if unknown:
        txt = (m.subject + "\n" + m.body[:2000] + "\n" + " ".join(l.text for l in m.links)).lower()
        hits = [w for w in LURE_WORDS if w in txt]
        safe = set(cfg.get("safe_link_domains", [])) | brand_domains   # the unknown sender's own domain is NOT safe
        foreign_links = [d for d in m.link_domains if d not in safe]
        if hits and foreign_links:
            f.append(Finding("unknown_sender_lure", 30, t("r_unknown_lure", d=m.sender_domain, word=hits[0])))
            if any(local.lower().startswith(g) for g in GENERIC_LOCALS):
                f.append(Finding("generic_sender", 10, t("r_generic_sender", local=local)))

    # --- links ---
    for l in m.links:
        if l.text_domain and l.href_domain and l.text_domain != l.href_domain:
            f.append(Finding("link_text_mismatch", 20, t("r_link_text_mismatch", shown=l.text_domain, real=l.href_domain)))
            break
    redir = [l for l in m.links if l.redirects]
    if redir:
        l = max(redir, key=lambda x: x.redirects)
        f.append(Finding("link_open_redirect", 25, t("r_link_redirect", n=l.redirects, d=l.href_domain)))
    ip_links = [l for l in m.links if l.href_domain and l.href_domain.replace(".", "").isdigit()]
    if ip_links:
        f.append(Finding("link_ip", 15, t("r_link_ip", ip=ip_links[0].href_domain)))
    sh = [d for d in m.link_domains if d in SHORTENERS]
    if sh:
        f.append(Finding("link_shortener", 10, t("r_link_shortener", list=", ".join(sh))))
    for d in m.link_domains:
        la = _lookalike(d, own | brand_domains, strict_tld=own)
        if la:
            f.append(Finding("link_lookalike", 25, t("r_link_lookalike", d=d, target=la)))
            break
    if len(m.link_domains) > 8:
        f.append(Finding("many_domains", 5, t("r_many_domains", n=len(m.link_domains))))

    # --- attachments ---
    for a in m.attachments:
        ext = a.rsplit(".", 1)[-1].lower() if "." in a else ""
        if ext in DANGEROUS_EXT:
            f.append(Finding("attachment_" + ext, DANGEROUS_EXT[ext], t("r_attachment", name=a)))
            break

    # --- discounts ---
    if ts == "own_thread":
        f.append(Finding("own_thread", -20, t("r_own_thread")))
    if internal:
        f.append(Finding("internal_sender", -20, t("r_internal")))
    elif m.sender_domain in trusted and m.auth.dmarc == "pass":
        f.append(Finding("trusted_sender", -15, t("r_trusted", d=m.sender_domain)))
    return f
