"""Paths and configuration. User data lives in %APPDATA%\\MailGuard, the program can live anywhere."""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

APP_NAME = "MailGuard"
APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
APP_DIR.mkdir(parents=True, exist_ok=True)

CONFIG = APP_DIR / "config.json"
LOG = APP_DIR / "mailguard_log.jsonl"
WATCH_LOG = APP_DIR / "app.log"
CONTACTS = APP_DIR / "contacts.json"
KNOWN = APP_DIR / "known_domains.json"
PROCESSED = APP_DIR / "processed.json"
FEEDBACK = APP_DIR / "feedback.jsonl"
SENT_INDEX = APP_DIR / "sent_index.json"

FROZEN = getattr(sys, "frozen", False)


def bundle_dir() -> Path:
    """Folder of the files shipped with the program (source tree or PyInstaller bundle)."""
    if FROZEN:
        return Path(sys._MEIPASS) / "mailguard"  # type: ignore[attr-defined]
    return Path(__file__).parent


def default_cfg() -> dict:
    return json.loads((bundle_dir() / "config.default.json").read_text(encoding="utf-8"))


def _read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_cfg() -> dict:
    base = default_cfg()
    user = _read_json(CONFIG, {})
    cfg = {**base, **user}
    for k in ("thresholds", "brands"):                       # keys added by newer versions
        cfg[k] = {**base.get(k, {}), **(user.get(k) or {})}
    cfg["_contacts"] = _read_json(CONTACTS, {})
    cfg["_known_domains"] = _read_json(KNOWN, {})
    cfg["_sent_index"] = _read_json(SENT_INDEX, {})
    cfg.setdefault("blocked_domains", [])
    cfg.setdefault("blocked_senders", [])
    cfg.setdefault("trusted_senders", [])
    from .i18n import detect_language, set_language
    if cfg.get("language") not in ("en", "it"):
        cfg["language"] = detect_language()
    set_language(cfg["language"])
    if not CONFIG.exists():
        save_cfg(cfg)
    return cfg


def save_cfg(cfg: dict):
    clean = {k: v for k, v in cfg.items() if not k.startswith("_")}
    CONFIG.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")


def exe_command() -> list[str]:
    """Command that relaunches this program (for autostart)."""
    if FROZEN:
        return [sys.executable]
    pyw = Path(sys.executable).with_name("pythonw.exe")
    return [str(pyw if pyw.exists() else sys.executable), "-m", "mailguard"]
