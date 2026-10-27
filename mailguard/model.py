"""Optional backend: the Laya decision model (Apache 2.0). No network calls after the first download of the weights.
Zero shot it is not accurate enough for this task; kept for experiments with fine tuning on feedback.jsonl."""
from __future__ import annotations
from .extract import Mail

QUESTIONS = {
    "phishing": {
        "type": "noul",
        "instructions": "Is this email a phishing, scam or fraud attempt that tries to deceive the recipient?",
    },
    "credentials": {
        "type": "noul",
        "instructions": "Does the email ask the recipient to log in, verify an account, enter a password, open a shared document, or update payment or bank details?",
    },
    "urgency": {
        "type": "score",
        "instructions": "How much pressure or urgency does the email put on the recipient?",
        "criteria": [
            "no pressure, normal tone",
            "some urgency or a deadline",
            "strong pressure or threat: account blocked, legal action, payment due within hours",
        ],
    },
    "impersonation": {
        "type": "choice",
        "instructions": "Who does the sender claim or appear to be?",
        "criteria": {
            "none": "a normal person or company writing about ordinary business",
            "bank_or_payment": "a bank, PayPal, payment or invoice service",
            "courier": "a courier or shipping company (DHL, UPS, BRT, Poste)",
            "it_service": "Microsoft, Google, IT support, email provider, document sharing service",
            "authority": "government, tax agency, police, legal office",
            "executive": "the recipient's boss, CEO or colleague asking for a favor or payment",
        },
    },
    "legit": {
        "type": "noul",
        "instructions": "Is this a normal business email (order, quote, invoice, delivery plan, meeting, newsletter, internal communication) consistent with its sender?",
    },
}


def build_state(m: Mail) -> dict:
    links = "; ".join(f"{l.text or '-'} -> {l.href_domain}" for l in m.links[:15]) or "nessuno"
    return {
        "from": f"{m.sender_name} <{m.sender_addr}>",
        "reply_to": ", ".join(m.reply_to) or "-",
        "subject": m.subject,
        "attachments": ", ".join(m.attachments) or "nessuno",
        "links": links,
        "body": m.body,
    }


class LocalModel:
    def __init__(self, device: str | None = None):
        import laya
        kw = {"device": device} if device else {}
        self.agent = laya.load("convaiinnovations/laya-multilingual", **kw)

    def predict(self, m: Mail) -> dict:
        res = self.agent.predict(build_state(m), QUESTIONS, max_len=1024)
        ans = res["answers"]
        return {
            "phishing": float(ans["phishing"]["noul"]),
            "credentials": float(ans["credentials"]["noul"]),
            "urgency": float(ans["urgency"]["score"]),
            "impersonation": ans["impersonation"]["choice"],
            "impersonation_p": float(ans["impersonation"]["probabilities"].get(ans["impersonation"]["choice"], 0)),
            "legit": float(ans["legit"]["noul"]),
        }
