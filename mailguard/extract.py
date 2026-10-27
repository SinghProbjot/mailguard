"""Turns a mail into features: sender, headers, links, attachments."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse, parse_qs, unquote
import tldextract

_REWRITERS = ("safelinks.protection.outlook.com", "urldefense.com", "urldefense.proofpoint.com", "url.emailprotection.link")
_GOOGLE_HOST = re.compile(r"(^|\.)google\.[a-z.]+$")


def unwrap_url(href: str) -> tuple[str, int]:
    """Strips security wrappers (Safe Links, Proofpoint) and open redirects (google.*/url?q=...).
    Returns (final url, number of suspicious redirects crossed)."""
    hops = 0
    try:
        for _ in range(6):
            p = urlparse(href)
            host = (p.hostname or "").lower()
            qs = parse_qs(p.query)
            if any(host.endswith(r) for r in _REWRITERS):
                inner = qs.get("url", qs.get("u", [None]))[0]
                if not inner:
                    break
                href = unquote(inner)
                if "urldefense" in host and not href.startswith("http"):
                    break
                continue
            if _GOOGLE_HOST.search(host) and p.path.rstrip("/") == "/url":
                inner = qs.get("q", qs.get("url", [None]))[0]
                hops += 1
                if not inner:
                    break
                inner = unquote(unquote(inner))
                if not inner.lower().startswith(("http://", "https://")):
                    break
                href = inner
                continue
            break
    except Exception:
        pass
    return href, hops
from bs4 import BeautifulSoup

_tld = tldextract.TLDExtract(suffix_list_urls=(), fallback_to_snapshot=True)  # offline


def reg_domain(host_or_email: str) -> str:
    """Registered domain (e.g. 'mail.dhl.com' -> 'dhl.com', 'a@b.it' -> 'b.it')."""
    if not host_or_email:
        return ""
    s = host_or_email.strip().lower()
    if s.startswith("http"):
        s = urlparse(s).hostname or ""
    elif "@" in s:
        s = s.rsplit("@", 1)[1]
    s = s.strip("<>[]() ")
    ext = _tld(s)
    if ext.suffix and ext.domain:
        return f"{ext.domain}.{ext.suffix}"
    parts = [p for p in s.split(".") if p]
    if len(parts) >= 2 and not parts[-1].isdigit():      # unknown suffix (e.g. .example, .local): keep the last two labels
        return ".".join(parts[-2:])
    return s


@dataclass
class Link:
    href: str
    text: str
    href_domain: str
    text_domain: str = ""
    redirects: int = 0      # open redirects crossed (google.*/url?q=...) to hide the destination


@dataclass
class Auth:
    spf: str = ""
    dkim: str = ""
    dmarc: str = ""
    compauth: str = ""
    header_from: str = ""
    raw: str = ""


@dataclass
class Mail:
    entry_id: str
    subject: str
    sender_name: str
    sender_addr: str
    sender_type: str          # "EX" = internal Exchange, "SMTP" = external
    reply_to: list[str]
    body: str
    links: list[Link]
    attachments: list[str]
    auth: Auth
    received: str
    message_id: str = ""
    in_reply_to: list[str] = field(default_factory=list)   # In-Reply-To + References
    sender_domain: str = ""
    reply_to_domains: list[str] = field(default_factory=list)
    link_domains: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.sender_domain = reg_domain(self.sender_addr)
        self.reply_to_domains = sorted({reg_domain(r) for r in self.reply_to if r})
        self.link_domains = sorted({l.href_domain for l in self.links if l.href_domain})


_HDR_UNFOLD = re.compile(r"\r?\n[ \t]+")


def parse_headers(raw: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not raw:
        return out
    unfolded = _HDR_UNFOLD.sub(" ", raw)
    for line in unfolded.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        out.setdefault(k.strip().lower(), []).append(v.strip())
    return out


def parse_auth(headers: dict[str, list[str]]) -> Auth:
    a = Auth()
    ars = headers.get("authentication-results", [])
    # Microsoft adds several Authentication-Results headers; keep the one from mx.microsoft.com when present
    chosen = next((x for x in ars if "mx.microsoft.com" in x or "protection.outlook.com" in x), ars[0] if ars else "")
    a.raw = chosen
    for key in ("spf", "dkim", "dmarc", "compauth"):
        m = re.search(rf"\b{key}=(\w+)", chosen)
        if m:
            setattr(a, key, m.group(1).lower())
    m = re.search(r"header\.from=([\w.-]+)", chosen)
    if m:
        a.header_from = m.group(1).lower()
    return a


_MSGID = re.compile(r"<([^<>\s]+)>")


def msg_ids(values: list[str]) -> list[str]:
    out = []
    for v in values:
        out += [x.lower() for x in _MSGID.findall(v)]
    return out


_DOMAIN_IN_TEXT = re.compile(r"\b((?:[a-z0-9-]+\.)+(?:[a-z]{2,}))\b", re.I)
_URL_IN_TEXT = re.compile(r"https?://[^\s<>\"')\]]+", re.I)


def extract_links(html: str, plain: str) -> list[Link]:
    links: list[Link] = []
    seen = set()
    if html:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href, hops = unwrap_url(a["href"].strip())
            if not href.lower().startswith(("http://", "https://")):
                continue
            text = " ".join(a.get_text(" ", strip=True).split())
            hd = reg_domain(href)
            td = ""
            m = _DOMAIN_IN_TEXT.search(text)
            if m:
                td = reg_domain(m.group(1))
            key = (href, text)
            if key in seen:
                continue
            seen.add(key)
            links.append(Link(href=href, text=text[:120], href_domain=hd, text_domain=td, redirects=hops))
    if not links and plain:
        for u in _URL_IN_TEXT.findall(plain):
            u, hops = unwrap_url(u)
            if u not in seen:
                seen.add(u)
                links.append(Link(href=u, text="", href_domain=reg_domain(u), redirects=hops))
    return links


def html_to_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "head"]):
        t.decompose()
    txt = soup.get_text("\n")
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n\s*\n+", "\n", txt)
    return txt.strip()
