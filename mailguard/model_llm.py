"""Semantic judge: a local LLM through Ollama (http://localhost:11434). Nothing leaves the PC."""
from __future__ import annotations
import json
import urllib.request
from .extract import Mail
from .i18n import language

SCHEMA = {
    "type": "object",
    "properties": {
        "phishing_probability": {"type": "number"},
        "asks_credentials_or_payment": {"type": "boolean"},
        "pressure": {"type": "integer"},
        "impersonates": {"type": "string", "enum": ["none", "bank_or_payment", "courier", "it_service", "authority", "executive", "supplier_or_customer"]},
        "legit_business": {"type": "boolean"},
        "reasons": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["phishing_probability", "asks_credentials_or_payment", "pressure", "impersonates", "legit_business", "reasons"],
}

SYSTEM = """You are an email security analyst for a company{company}.
Decide whether the email is phishing, a scam or fraud: credential theft, fake invoices with a new IBAN, fake couriers,
fake shared documents, CEO fraud, fake Microsoft notices. Ordinary business mail (orders, quotes, delivery notes,
delivery plans, meetings, automatic reports, newsletters, Teams or SharePoint notifications from real Microsoft domains) is NOT phishing.
Consider the real sender, the link domains, the attachments and the content. Reply ONLY with the requested JSON.
The recipient also uses personal and IT services (ChatGPT, Claude, GitHub, Teams, LinkedIn, newsletters): a mail that is
"outside the company's sector" is NOT a phishing signal. An authenticated mail (dmarc=pass) whose links point to the sender's own
domain or to the official domains of its service is not phishing either: in that case phishing_probability must be <= 0.1.
Only deception counts: a domain imitating another, links to domains unrelated to the sender, requests for credentials or money.
Strong phishing signals even when SPF/DKIM pass: a generic or unknown sender (no-reply, docs-share, notifications) inviting
to "sign in with your work account" or "open a shared document" with a link to a domain that is NOT
microsoft.com/sharepoint.com/office.com; requests to change bank details; urgent payments; account verifications with a deadline.
- phishing_probability: 0.0-1.0
- asks_credentials_or_payment: asks for login/password/account verification/payment/change of bank details
- pressure: 0 normal, 1 some urgency, 2 strong pressure or threats
- impersonates: who the sender pretends to be, "none" if nobody
- legit_business: a normal business mail consistent with its sender
- reasons: at most 3 short sentences, written in {lang}, explaining the verdict"""

LANG_NAMES = {"en": "English", "it": "Italian"}


def feedback_examples(limit: int = 6) -> str:
    """Latest verdicts given by the user (feedback.jsonl), used as examples in the prompt."""
    try:
        from .paths import FEEDBACK
        rows = [json.loads(l) for l in FEEDBACK.read_text(encoding="utf-8").splitlines() if l.strip()]
    except Exception:
        return ""
    seen, out = set(), []
    for r in reversed(rows):
        key = (r.get("from"), r.get("subject"))
        if key in seen or not r.get("subject"):
            continue
        seen.add(key)
        lab = "PHISHING" if r.get("label") == "phishing" else "LEGITIMATE"
        out.append(f"- {lab}: from {r.get('from')} | subject: {str(r.get('subject'))[:70]}")
        if len(out) >= limit:
            break
    if not out:
        return ""
    return "\nExamples already judged by the user (use them as reference):\n" + "\n".join(out)


def build_prompt(m: Mail) -> str:
    links = "\n".join(f"  - text: {l.text or '-'} | destination: {l.href_domain}" for l in m.links[:20]) or "  none"
    return (
        f"SENDER: {m.sender_name} <{m.sender_addr}> (type: {'internal Exchange' if m.sender_type == 'EX' else 'external'})\n"
        f"REPLY-TO: {', '.join(m.reply_to) or '-'}\n"
        f"AUTHENTICATION: spf={m.auth.spf or '?'} dkim={m.auth.dkim or '?'} dmarc={m.auth.dmarc or '?'}\n"
        f"SUBJECT: {m.subject}\n"
        f"ATTACHMENTS: {', '.join(m.attachments) or 'none'}\n"
        f"LINKS:\n{links}\n"
        f"BODY:\n{m.body}\n"
    )


class OllamaModel:
    def __init__(self, model: str = "qwen3:4b", url: str = "http://localhost:11434", company: str = "", sector: str = ""):
        self.model = model
        self.url = url.rstrip("/")
        desc = ""
        if company or sector:
            desc = " (" + ", ".join(x for x in (company, f"sector: {sector}" if sector else "") if x) + ")"
        self.system = SYSTEM.format(company=desc, lang=LANG_NAMES.get(language(), "English"))
        # check that the server answers and the model exists
        with urllib.request.urlopen(f"{self.url}/api/tags", timeout=5) as r:
            names = [x["name"] for x in json.load(r).get("models", [])]
        if not any(n == model or n.split(":")[0] == model.split(":")[0] for n in names):
            raise RuntimeError(f"Model {model} not found in Ollama. Run: ollama pull {model}")

    def _chat(self, messages: list[dict], fmt=None, timeout: int = 180) -> str:
        payload = {"model": self.model, "stream": False, "think": False, "options": {"temperature": 0, "num_ctx": 8192}, "messages": messages}
        if fmt:
            payload["format"] = fmt
        req = urllib.request.Request(f"{self.url}/api/chat", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)["message"]["content"]

    def warmup(self):
        self._chat([{"role": "user", "content": "ok"}], timeout=300)

    def predict(self, m: Mail) -> dict:
        content = self._chat([{"role": "system", "content": self.system + feedback_examples()}, {"role": "user", "content": build_prompt(m)}], fmt=SCHEMA)
        d = json.loads(content)
        return {
            "phishing": max(0.0, min(1.0, float(d["phishing_probability"]))),
            "credentials": 1.0 if d["asks_credentials_or_payment"] else 0.0,
            "urgency": float(d["pressure"]),
            "impersonation": d["impersonates"],
            "impersonation_p": 1.0,
            "legit": 1.0 if d["legit_business"] else 0.0,
            "reasons": [str(x) for x in d.get("reasons", [])][:3],
        }
