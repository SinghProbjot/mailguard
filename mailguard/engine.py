"""MailGuard engine: status, Ollama setup, analysis, watching. Used by both the GUI and the command line."""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.request
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

from .i18n import t
from .notify import load_processed, log, save_processed, toast
from .outlook_client import Outlook
from .paths import load_cfg, save_cfg
from .scorer import Verdict, needs_model, score_mail

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


# ----------------------------------------------------------------- Ollama
def ollama_exe() -> str | None:
    cands = [Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
             Path(os.environ.get("ProgramFiles", "")) / "Ollama" / "ollama.exe"]
    for c in cands:
        if c.exists():
            return str(c)
    return shutil.which("ollama")


def ollama_running(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/api/version", timeout=3):
            return True
    except Exception:
        return False


def ollama_models(url: str) -> list[str]:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/api/tags", timeout=5) as r:
            return [x["name"] for x in json.load(r).get("models", [])]
    except Exception:
        return []


def model_present(url: str, name: str) -> bool:
    base = name.split(":")[0]
    return any(n == name or n.split(":")[0] == base for n in ollama_models(url))


def start_ollama(url: str, wait: float = 15) -> bool:
    if ollama_running(url):
        return True
    exe = ollama_exe()
    if not exe:
        return False
    try:
        subprocess.Popen([exe, "serve"], creationflags=CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return False
    t0 = time.time()
    while time.time() - t0 < wait:
        if ollama_running(url):
            return True
        time.sleep(1)
    return False


def _stream(cmd: list[str], say) -> int:
    """Runs a command showing its output line by line (also handles the \\r of progress bars)."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                         creationflags=CREATE_NO_WINDOW, bufsize=0)
    buf = ""
    last = 0.0
    while True:
        ch = p.stdout.read(1)
        if not ch:
            break
        if ch in "\r\n":
            line = buf.strip()
            buf = ""
            if line and (ch == "\n" or time.time() - last > 0.5):
                say(line)
                last = time.time()
        else:
            buf += ch
    if buf.strip():
        say(buf.strip())
    return p.wait()


def install_ollama(say) -> bool:
    if ollama_exe():
        say(t("inst_present"))
        return True
    if shutil.which("winget"):
        say(t("inst_winget"))
        rc = _stream(["winget", "install", "--id", "Ollama.Ollama", "--accept-source-agreements", "--accept-package-agreements",
                      "--silent", "--disable-interactivity"], say)
        if rc == 0 and ollama_exe():
            say(t("inst_done"))
            return True
        say(t("inst_winget_rc", rc=rc))
    say(t("inst_browser"))
    webbrowser.open("https://ollama.com/download/windows")
    return False


def pull_model(url: str, name: str, say) -> bool:
    exe = ollama_exe()
    if not exe:
        say(t("pull_no_ollama"))
        return False
    if not start_ollama(url):
        say(t("pull_no_server"))
        return False
    say(t("pull_start", name=name))
    rc = _stream([exe, "pull", name], say)
    ok = rc == 0 and model_present(url, name)
    say(t("pull_done") if ok else t("pull_fail", rc=rc))
    return ok


# ----------------------------------------------------------------- autostart
def startup_shortcut() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "MailGuard.lnk"


def set_autostart(enabled: bool):
    from .paths import exe_command
    lnk = startup_shortcut()
    if not enabled:
        lnk.unlink(missing_ok=True)
        return
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    cmd = exe_command()
    sh = win32com.client.Dispatch("WScript.Shell")
    sc = sh.CreateShortcut(str(lnk))
    sc.TargetPath = cmd[0]
    sc.Arguments = " ".join(cmd[1:] + ["--tray"])
    sc.WorkingDirectory = str(Path(cmd[0]).parent)
    sc.Description = "MailGuard"
    sc.Save()


# ----------------------------------------------------------------- engine
class Engine:
    """All work runs in the thread that calls the methods; events go out through `emit(dict)`."""

    def __init__(self, emit=None):
        self.emit = emit or (lambda ev: None)
        self.cfg = load_cfg()
        self.ol: Outlook | None = None
        self.model = None
        self._stop = threading.Event()
        self.watching = False
        self.use_model = True       # False = rules only for this session (does not touch the configuration)

    # --- helpers
    def say(self, text: str):
        self.emit({"type": "log", "text": text})

    def reload_cfg(self):
        self.cfg = load_cfg()

    def category(self, level: str) -> str:
        return self.cfg.get(f"category_{level}") or t(f"cat_{level}")

    def connect(self) -> Outlook:
        if self.ol is None:
            self.ol = Outlook(self.cfg.get("mailbox") or None)
            if not self.cfg.get("own_domains"):
                addr = self.ol.address
                if "@" in addr:
                    self.cfg["own_domains"] = [addr.rsplit("@", 1)[1].lower()]
                    save_cfg(self.cfg)
            if not self.cfg.get("mailbox"):
                self.cfg["mailbox"] = self.ol.mailbox
                save_cfg(self.cfg)
        return self.ol

    def status(self) -> dict:
        url = self.cfg.get("ollama_url", "http://localhost:11434")
        st = {"outlook": False, "outlook_msg": "", "ollama_installed": bool(ollama_exe()), "ollama_running": ollama_running(url),
              "model": False, "contacts": bool(self.cfg.get("_contacts")), "mailbox": self.cfg.get("mailbox", "")}
        if st["ollama_running"]:
            st["model"] = model_present(url, self.cfg.get("ollama_model", "qwen3:4b"))
        if os.environ.get("MAILGUARD_DEMO"):            # demo mode: no Outlook connection
            st.update(outlook=True, outlook_msg="demo@example.com", contacts=True)
            self.emit({"type": "status", **st})
            return st
        try:
            self.connect()
            st["outlook"] = True
            st["outlook_msg"] = self.ol.mailbox
        except Exception as e:
            st["outlook_msg"] = str(e)[:120]
        self.emit({"type": "status", **st})
        return st

    def load_model(self, warm: bool = True):
        kind = self.cfg.get("model", "ollama") if self.use_model else "none"
        self.model = None
        if kind == "ollama":
            url = self.cfg.get("ollama_url", "http://localhost:11434")
            name = self.cfg.get("ollama_model", "qwen3:4b")
            if not start_ollama(url):
                self.say(t("eng_ollama_not_running"))
                return None
            if not model_present(url, name):
                self.say(t("eng_model_missing", name=name))
                return None
            from .model_llm import OllamaModel
            self.model = OllamaModel(model=name, url=url, company=self.cfg.get("company_name", ""), sector=self.cfg.get("company_sector", ""))
            if warm:
                self.say(t("eng_loading_model"))
                t0 = time.time()
                try:
                    self.model.warmup()
                    self.say(t("eng_model_ready", s=f"{time.time() - t0:.0f}"))
                except Exception as e:
                    self.say(t("eng_model_failed", err=e))
                    self.model = None
        elif kind == "laya":
            from .model import LocalModel
            self.model = LocalModel()
        return self.model

    # --- analysis
    def _action(self, item, v: Verdict, apply: bool) -> tuple[str, str]:
        """Performs (or simulates) the action. Returns (description, updated entry_id)."""
        cfg = self.cfg
        eid = item.EntryID
        if v.level == "ok":
            return t("act_none"), eid
        if v.level == "phishing":
            action = cfg.get("action_phishing", "junk")
            if action == "junk":
                desc = t("act_junk")
            elif action.startswith("folder:"):
                desc = t("act_folder", f=action.split(":", 1)[1])
            else:
                desc = t("act_cat_phish")
            if apply:
                self.ol.set_category(item, self.category("phishing"))
                if action == "junk":
                    eid = self.ol.move_to_junk(item).EntryID
                elif action.startswith("folder:"):
                    eid = self.ol.move_to_folder(item, action.split(":", 1)[1]).EntryID
        else:
            desc = t("act_suspect")
            if apply:
                self.ol.set_category(item, self.category("suspect"))
        return (desc if apply else t("act_simulated", desc=desc)), eid

    def analyze_item(self, item, apply: bool, notify: bool) -> dict:
        m = self.ol.to_mail(item, self.cfg["max_body_chars"])
        model_out = None
        if self.model is not None and needs_model(m, self.cfg):
            try:
                model_out = self.model.predict(m)
            except Exception as e:
                self.say(t("eng_model_err_mail", err=e))
        v = score_mail(m, model_out, self.cfg)
        action, eid = self._action(item, v, apply)
        rec = {
            "entry_id": eid, "received": m.received, "from": f"{m.sender_name} <{m.sender_addr}>", "sender_addr": m.sender_addr,
            "sender_domain": m.sender_domain, "subject": m.subject, "score": v.score, "level": v.level, "trusted": v.trusted,
            "action": action, "reasons": v.reasons, "model": v.model, "findings": [(f.code, f.points) for f in v.findings],
            "auth": {"spf": m.auth.spf, "dkim": m.auth.dkim, "dmarc": m.auth.dmarc, "compauth": m.auth.compauth},
            "links": m.link_domains, "attachments": m.attachments,
        }
        log(rec)
        self.emit({"type": "mail", **rec})
        if notify and v.level != "ok" and self.cfg.get("notify", True):
            title = t("ntf_phish_title") if v.level == "phishing" else t("ntf_suspect_title")
            toast(title, t("ntf_body", addr=m.sender_addr, subject=m.subject[:60], action=action, why="; ".join(v.reasons[:2])))
        return rec

    def scan(self, last: int = 30, apply: bool = False, folder_name: str | None = None) -> dict:
        self.connect()
        if self.model is None:
            self.load_model()
        if not self.cfg.get("_sent_index"):
            self._refresh_sent()
        folder = self.ol.folder_by_name(folder_name) if folder_name else self.ol.inbox
        counts = {"ok": 0, "suspect": 0, "phishing": 0}
        self.say(t("eng_scan_start", n=last, folder=folder.Name))
        for item in list(self.ol.recent_items(limit=last, folder=folder)):
            if self._stop.is_set():
                break
            rec = self.analyze_item(item, apply, notify=False)
            counts[rec["level"]] += 1
        self.say(t("eng_scan_done", **counts))
        return counts

    def test_samples(self) -> int:
        from .samples import samples
        if self.model is None:
            self.load_model()
        cfg = dict(self.cfg)                        # copy: the samples need a company domain and a colleague
        if not cfg.get("own_domains"):
            cfg["own_domains"] = ["example.com"]
        own = cfg["own_domains"][0]
        contacts = dict(cfg.get("_contacts") or {})
        colleague = next(iter(contacts)) if contacts else "mario rossi"
        contacts.setdefault(colleague, f"{colleague.replace(' ', '.')}@{own}")
        cfg["_contacts"] = contacts
        errors = 0
        rows = samples(own, colleague)
        for expected, m in rows:
            out = self.model.predict(m) if (self.model and needs_model(m, cfg)) else None
            v = score_mail(m, out, cfg)
            ok = (v.level != "ok") if expected == "PHISHING" else (v.level == "ok")   # a flagged phishing sample counts, even as "to verify"
            errors += not ok
            self.emit({"type": "mail", "entry_id": "", "received": "", "from": f"{m.sender_name} <{m.sender_addr}>",
                       "sender_addr": m.sender_addr, "sender_domain": m.sender_domain, "subject": m.subject, "score": v.score,
                       "level": v.level, "trusted": v.trusted,
                       "action": t("eng_sample_action", expected=expected, result=t("result_ok") if ok else t("result_err")),
                       "reasons": v.reasons, "test": True})
        self.say(t("eng_samples_done", ok=len(rows) - errors, n=len(rows)))
        return errors

    def learn(self):
        from .learn import learn
        self.connect()
        learn(self.ol, {d.lower() for d in self.cfg["own_domains"]}, progress=self.say)
        self.reload_cfg()

    # --- watching (split into start/step so the GUI can run it in its worker thread)
    def watch_start(self, apply: bool | None = None):
        self._apply = self.cfg.get("apply_actions", False) if apply is None else apply
        self._stop.clear()
        self.connect()
        if not self.cfg.get("_contacts"):
            self.say(t("eng_first_learn"))
            self.learn()
        self.load_model()
        self._processed = load_processed()
        for it in self.ol.recent_items(limit=200):
            self._processed.add(it.EntryID)
        save_processed(self._processed)
        self._since = datetime.now() - timedelta(minutes=5)
        self._refresh_sent()
        self.watching = True
        self.emit({"type": "watch", "on": True})
        self.say(t("eng_listening", mode=t("mode_apply") if self._apply else t("mode_alert")))

    def _refresh_sent(self):
        """Refreshes the sent mail index (needed to recognise replies to your own threads)."""
        try:
            from .learn import refresh_sent_index
            self.cfg["_sent_index"] = refresh_sent_index(self.ol, limit=150)
            self._sent_refreshed = time.time()
        except Exception as e:
            self.say(t("eng_sent_index_err", err=e))

    def watch_step(self) -> int:
        """Analyses the mail that arrived since the last round. Returns how many."""
        try:
            if time.time() - getattr(self, "_sent_refreshed", 0) > 600:
                self._refresh_sent()
            new = [it for it in self.ol.recent_items(since=self._since) if it.EntryID not in self._processed]
            for item in reversed(new):
                self._processed.add(item.EntryID)
                self.analyze_item(item, self.cfg.get("apply_actions", self._apply), notify=True)
            if new:
                save_processed(self._processed)
            self._since = datetime.now() - timedelta(minutes=2)
            return len(new)
        except Exception as e:
            self.say(t("eng_loop_err", err=e))
            self.ol = None
            time.sleep(5)
            try:
                self.connect()
            except Exception:
                pass
            return 0

    def watch_stop(self):
        self.watching = False
        self.emit({"type": "watch", "on": False})
        self.say(t("eng_stopped"))

    def watch(self, apply: bool | None = None):
        """Blocking version for the command line."""
        self.watch_start(apply)
        try:
            while not self._stop.is_set():
                self.watch_step()
                self._stop.wait(self.cfg.get("poll_seconds", 20))
        finally:
            self.watch_stop()

    def stop(self):
        self._stop.set()

    # --- user feedback
    def mark_safe(self, rec: dict):
        """The user says it is legitimate: trust the sender and put the mail back in the Inbox."""
        from .notify import feedback
        from .rules import FREEMAIL
        d = rec.get("sender_domain", "")
        addr = (rec.get("sender_addr") or "").lower()
        if d in FREEMAIL or not d:
            if addr and addr not in self.cfg["trusted_senders"]:
                self.cfg["trusted_senders"].append(addr)
        elif d not in self.cfg["trusted_domains"] and d not in self.cfg["own_domains"]:
            self.cfg["trusted_domains"].append(d)
        if d in self.cfg["blocked_domains"]:
            self.cfg["blocked_domains"].remove(d)
        if addr in self.cfg["blocked_senders"]:
            self.cfg["blocked_senders"].remove(addr)
        save_cfg(self.cfg)
        feedback({"label": "legit", **{k: rec.get(k) for k in ("entry_id", "from", "subject", "score", "reasons")}})
        try:
            if rec.get("entry_id"):
                self.connect()
                item = self.ol.item_by_id(rec["entry_id"])
                if item.Parent.EntryID == self.ol.junk.EntryID:
                    item = self.ol.move_to_inbox(item)
                cats = [c.strip() for c in (item.Categories or "").split(";") if c.strip() and not c.strip().startswith("MailGuard")]
                item.Categories = "; ".join(cats)
                item.Save()
                rec["entry_id"] = item.EntryID
        except Exception as e:
            self.say(t("eng_move_err", err=e))
        self.say(t("eng_trusted_added", who=addr if (d in FREEMAIL or not d) else d))

    def mark_phishing(self, rec: dict):
        from .notify import feedback
        from .rules import FREEMAIL
        feedback({"label": "phishing", **{k: rec.get(k) for k in ("entry_id", "from", "subject", "score", "reasons")}})
        d, addr = rec.get("sender_domain", ""), (rec.get("sender_addr") or "").lower()
        brand_domains = {x for ds in self.cfg.get("brands", {}).values() for x in ds}
        if d and d not in self.cfg["own_domains"] and d not in FREEMAIL and d not in brand_domains and d not in self.cfg.get("_known_domains", {}):
            if d not in self.cfg["blocked_domains"]:
                self.cfg["blocked_domains"].append(d)
                self.say(t("eng_blocked_domain", d=d))
        elif addr and addr not in self.cfg["blocked_senders"]:
            self.cfg["blocked_senders"].append(addr)
            self.say(t("eng_blocked_sender", addr=addr))
        if d in self.cfg["trusted_domains"]:
            self.cfg["trusted_domains"].remove(d)
        save_cfg(self.cfg)
        try:
            if rec.get("entry_id"):
                self.connect()
                item = self.ol.item_by_id(rec["entry_id"])
                self.ol.set_category(item, self.category("phishing"))
                rec["entry_id"] = self.ol.move_to_junk(item).EntryID
                self.say(t("eng_moved_junk"))
        except Exception as e:
            self.say(t("eng_move_err", err=e))

    def open_in_outlook(self, entry_id: str):
        self.connect()
        self.ol.item_by_id(entry_id).Display()
