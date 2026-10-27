"""Combines deterministic rules and the model verdict into a 0-100 score with explanations."""
from __future__ import annotations
from dataclasses import dataclass, field
from .extract import Mail
from .i18n import t
from .rules import FREEMAIL, Finding, run_rules, is_internal, thread_state

BRAND_FOR_CHOICE = {
    "bank_or_payment": ["paypal", "intesa", "unicredit"],
    "courier": ["dhl", "ups", "fedex", "poste", "brt", "gls"],
    "it_service": ["microsoft", "google", "docusign", "adobe", "aruba"],
    "authority": ["agenzia entrate", "inps"],
}
# "Hard" rules that still count for internal or known senders (compromised accounts)
HARD_CODES = {"attachment_", "link_lookalike", "link_ip", "spoof_own", "dmarc_fail", "spf_fail", "colleague_name_external",
              "blocked_", "thread_hijack"}


@dataclass
class Verdict:
    score: int
    level: str                      # "ok" | "suspect" | "phishing"
    reasons: list[str] = field(default_factory=list)
    model: dict = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    trusted: bool = False           # internal sender or habitual correspondent: the model is not needed


def is_known(m: Mail, cfg: dict) -> bool:
    """Habitual correspondent: a domain the user writes to or receives authenticated mail from."""
    known: dict = cfg.get("_known_domains", {})
    auth_ok = m.auth.dmarc == "pass" or (m.auth.spf == "pass" and m.auth.dkim != "fail")
    if m.sender_addr.lower() in {s.lower() for s in cfg.get("trusted_senders", [])} and auth_ok:
        return True
    if m.sender_domain in FREEMAIL:
        return False
    brand_domains = {d for ds in cfg.get("brands", {}).values() for d in ds}
    if m.sender_domain in brand_domains and auth_ok:          # Microsoft, Teams, the real DHL, etc.
        return True
    if m.sender_domain in {d.lower() for d in cfg.get("trusted_domains", [])} and auth_ok:
        return True
    info = known.get(m.sender_domain)
    if not info:
        return False
    return (info.get("sent", 0) >= 1 and m.auth.dmarc != "fail") or (info.get("received_auth_ok", 0) >= 2 and auth_ok)


def is_coherent(m: Mail, cfg: dict) -> bool:
    """Authenticated sender whose links only point to its own or well known domains: the normal pattern of legitimate services."""
    auth_ok = m.auth.dmarc == "pass" or (m.auth.spf == "pass" and m.auth.dkim == "pass")
    if not auth_ok:
        return False
    safe = set(cfg.get("safe_link_domains", [])) | {d for ds in cfg.get("brands", {}).values() for d in ds}
    recognised = safe | set(cfg.get("_known_domains", {})) | {d.lower() for d in cfg.get("trusted_domains", [])}
    if m.sender_domain not in recognised:      # a never seen domain is not "coherent" just because it links to itself
        return False
    return all(d in safe | {m.sender_domain} for d in m.link_domains)


def needs_model(m: Mail, cfg: dict) -> bool:
    """Internal senders, habitual correspondents and replies to the user's own mail skip the model: hard rules only."""
    if m.sender_addr.lower() in {s.lower() for s in cfg.get("blocked_senders", [])} or m.sender_domain in {d.lower() for d in cfg.get("blocked_domains", [])}:
        return False
    return not (is_internal(m, cfg) or is_known(m, cfg) or thread_state(m, cfg) == "own_thread")


def score_mail(m: Mail, model_out: dict | None, cfg: dict) -> Verdict:
    findings = run_rules(m, cfg)
    trusted = not needs_model(m, cfg)
    if trusted:
        findings = [f for f in findings if any(f.code.startswith(h) for h in HARD_CODES)]
    pts = sum(f.points for f in findings)
    reasons = [f.reason for f in findings if f.points > 0]

    if model_out and not trusted:
        p = model_out["phishing"]
        coherent = is_coherent(m, cfg)
        rules_hit = any(f.points > 0 for f in findings)
        # The model alone (no rule triggered) cannot reach the "to verify" threshold: this avoids the false positives
        # of a small model that finds everything outside the company's sector suspicious.
        weight = 20 if coherent else (45 if rules_hit else 35)
        pts += int(p * weight)
        if coherent and not rules_hit:
            pts -= 10
        if p >= 0.5:
            reasons.append(t("s_model_prob", p=f"{p:.0%}"))
            reasons += [r for r in model_out.get("reasons", []) if r]
            if model_out["credentials"] >= 0.6:
                pts += 10
            if model_out["urgency"] >= 1.5:
                pts += 10
            imp = model_out["impersonation"]
            if imp not in ("none", "supplier_or_customer"):
                brand_doms = {d for b in BRAND_FOR_CHOICE.get(imp, []) for d in cfg["brands"].get(b, [])}
                if m.sender_domain not in brand_doms:
                    pts += 10
        elif model_out["legit"] >= 0.5 and p < 0.3:
            pts -= 10

    score = max(0, min(100, pts))
    th = cfg["thresholds"]
    level = "phishing" if score >= th["phishing"] else "suspect" if score >= th["suspect"] else "ok"
    return Verdict(score=score, level=level, reasons=reasons, model=model_out or {}, findings=findings, trusted=trusted)
