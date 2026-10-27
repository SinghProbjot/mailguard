"""MailGuard desktop application (tkinter + tray icon)."""
from __future__ import annotations
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from .engine import Engine, install_ollama, pull_model, set_autostart, startup_shortcut
from .i18n import LANGUAGES, language, t
from .notify import read_log
from .outlook_client import Outlook
from .paths import APP_DIR, bundle_dir, save_cfg

COLORS = {"bg": "#f4f6f9", "card": "#ffffff", "ok": "#2e7d32", "warn": "#ef6c00", "bad": "#c62828", "muted": "#6b7280"}
OK_MARK, BAD_MARK = "✔", "✖"


def _icon_image():
    from PIL import Image, ImageDraw
    p = bundle_dir() / "assets" / "icon.png"
    if p.exists():
        return Image.open(p)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(32, 4), (58, 14), (54, 40), (32, 60), (10, 40), (6, 14)], fill=(31, 94, 255, 255))
    d.line([(20, 32), (29, 42), (46, 22)], fill="white", width=6)
    return img


class Worker(threading.Thread):
    """The only thread that talks to Outlook and to the model. Runs queued tasks and, when active, the watch loop."""

    def __init__(self, engine: Engine):
        super().__init__(daemon=True)
        self.engine = engine
        self.tasks: queue.Queue = queue.Queue()
        self.running = True
        self._last_step = 0.0

    def submit(self, fn, *a):
        self.tasks.put((fn, a))

    def run(self):
        import pythoncom
        pythoncom.CoInitialize()
        while self.running:
            try:
                fn, a = self.tasks.get(timeout=0.5)
                try:
                    fn(*a)
                except Exception as e:
                    self.engine.say(t("eng_error", err=e))
            except queue.Empty:
                pass
            if self.engine.watching and time.time() - self._last_step >= self.engine.cfg.get("poll_seconds", 20):
                self._last_step = time.time()
                try:
                    self.engine.watch_step()
                except Exception as e:
                    self.engine.say(t("eng_error", err=e))


class App:
    def __init__(self, root: tk.Tk, tray: bool):
        self.root = root
        self.q: queue.Queue = queue.Queue()
        self.engine = Engine(emit=self.q.put)
        self.cfg = self.engine.cfg
        self.worker = Worker(self.engine)
        self.records: dict[str, dict] = {}
        self.tray_icon = None
        self._build()
        self.worker.start()
        self.root.after(150, self._poll)
        self.worker.submit(self.engine.status)
        self.worker.submit(self._load_mailboxes)
        for rec in read_log(200):
            self._add_row(rec, scroll=False)
        if tray:
            self.root.withdraw()
        self._start_tray()
        if self.cfg.get("auto_watch", True) and not os.environ.get("MAILGUARD_DEMO"):
            self.toggle_watch()
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

    # ------------------------------------------------------------------ UI
    def _build(self):
        r = self.root
        r.title(t("app_title"))
        r.geometry("1060x680")
        r.minsize(860, 560)
        r.configure(bg=COLORS["bg"])
        try:
            r.iconphoto(True, tk.PhotoImage(file=str(bundle_dir() / "assets" / "icon.png")))
        except Exception:
            pass
        style = ttk.Style(r)
        try:
            style.theme_use("vista")
        except Exception:
            style.theme_use("clam")
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), background=COLORS["bg"])
        style.configure("Sub.TLabel", foreground=COLORS["muted"], background=COLORS["bg"])
        style.configure("Status.TLabel", font=("Segoe UI", 10), background=COLORS["bg"])
        style.configure("Big.TButton", font=("Segoe UI", 11, "bold"), padding=8)
        style.configure("Treeview", rowheight=24, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

        head = ttk.Frame(r, padding=(16, 12, 16, 6))
        head.pack(fill="x")
        ttk.Label(head, text="MailGuard", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(head, text=t("tagline"), style="Sub.TLabel").grid(row=1, column=0, sticky="w")
        self.lbl_outlook = ttk.Label(head, text="Outlook: ...", style="Status.TLabel")
        self.lbl_ollama = ttk.Label(head, text=t("model_prefix") + "...", style="Status.TLabel")
        self.lbl_outlook.grid(row=0, column=1, padx=24, sticky="w")
        self.lbl_ollama.grid(row=1, column=1, padx=24, sticky="w")
        self.btn_watch = ttk.Button(head, text=t("btn_start"), style="Big.TButton", command=self.toggle_watch)
        self.btn_watch.grid(row=0, column=2, rowspan=2, padx=(24, 8))
        self.var_apply = tk.BooleanVar(value=self.cfg.get("apply_actions", False))
        ttk.Checkbutton(head, text=t("chk_apply"), variable=self.var_apply, command=self._apply_changed).grid(row=0, column=3, rowspan=2, sticky="w")
        head.columnconfigure(0, weight=1)

        nb = self.nb = ttk.Notebook(r)
        nb.pack(fill="both", expand=True, padx=12, pady=(4, 10))
        self.tab_activity = ttk.Frame(nb, padding=8)
        self.tab_settings = ttk.Frame(nb, padding=16)
        self.tab_setup = ttk.Frame(nb, padding=16)
        nb.add(self.tab_activity, text=t("tab_activity"))
        nb.add(self.tab_settings, text=t("tab_settings"))
        nb.add(self.tab_setup, text=t("tab_setup"))
        self._build_activity()
        self._build_settings()
        self._build_setup()

        self.statusbar = ttk.Label(r, text=t("ready"), style="Sub.TLabel", padding=(16, 2))
        self.statusbar.pack(fill="x", side="bottom")

    def _build_activity(self):
        f = self.tab_activity
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Button(bar, text=t("btn_scan50"), command=lambda: self._bg(self.engine.scan, 50, False)).pack(side="left")
        ttk.Button(bar, text=t("btn_samples"), command=lambda: self._bg(self.engine.test_samples)).pack(side="left", padx=6)
        ttk.Label(bar, text=t("scan_hint"), style="Sub.TLabel").pack(side="left", padx=6)
        ttk.Button(bar, text=t("btn_clear"), command=self._clear).pack(side="right")

        cols = ("time", "score", "level", "sender", "subject", "action")
        tf = ttk.Frame(f)
        tf.pack(side="top", fill="both", expand=True)
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="browse")
        widths = {"time": 90, "score": 50, "level": 105, "sender": 230, "subject": 330, "action": 200}
        for c in cols:
            self.tree.heading(c, text=t("col_" + c))
            self.tree.column(c, width=widths[c], anchor="w", stretch=(c in ("subject", "sender")))
        self.tree.tag_configure("phishing", background="#fde8e8", foreground=COLORS["bad"])
        self.tree.tag_configure("suspect", background="#fff3e0", foreground=COLORS["warn"])
        self.tree.tag_configure("trusted", foreground=COLORS["muted"])
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._show_detail)

        det = ttk.LabelFrame(f, text=t("detail_frame"), padding=8)
        det.pack(fill="both", pady=(8, 0))
        self.detail = tk.Text(det, height=7, wrap="word", font=("Segoe UI", 9), relief="flat", bg=COLORS["card"])
        self.detail.pack(fill="both", expand=True)
        self.detail.configure(state="disabled")
        btns = ttk.Frame(det)
        btns.pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text=t("btn_open"), command=self._open).pack(side="left")
        ttk.Button(btns, text=t("btn_safe"), command=self._mark_safe).pack(side="left", padx=6)
        ttk.Button(btns, text=t("btn_phish"), command=self._mark_phishing).pack(side="left")

    def _build_settings(self):
        f = self.tab_settings
        self.vars = {}

        def row(i, label, widget):
            ttk.Label(f, text=label).grid(row=i, column=0, sticky="nw", pady=6, padx=(0, 12))
            widget.grid(row=i, column=1, sticky="we", pady=6)

        self.cb_mailbox = ttk.Combobox(f, values=[self.cfg.get("mailbox", "")], state="readonly")
        self.cb_mailbox.set(self.cfg.get("mailbox", ""))
        row(0, t("set_mailbox"), self.cb_mailbox)
        self.vars["own"] = tk.StringVar(value=", ".join(self.cfg.get("own_domains", [])))
        row(1, t("set_own"), ttk.Entry(f, textvariable=self.vars["own"]))
        lists = ttk.Frame(f)
        self.txt_trusted = tk.Text(lists, height=5, width=40, font=("Segoe UI", 9))
        self.txt_trusted.insert("1.0", "\n".join(self.cfg.get("trusted_domains", []) + self.cfg.get("trusted_senders", [])))
        self.txt_blocked = tk.Text(lists, height=5, width=40, font=("Segoe UI", 9))
        self.txt_blocked.insert("1.0", "\n".join(self.cfg.get("blocked_domains", []) + self.cfg.get("blocked_senders", [])))
        ttk.Label(lists, text=t("set_trusted")).grid(row=0, column=0, sticky="w")
        ttk.Label(lists, text=t("set_blocked")).grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.txt_trusted.grid(row=1, column=0, sticky="we")
        self.txt_blocked.grid(row=1, column=1, sticky="we", padx=(12, 0))
        lists.columnconfigure(0, weight=1)
        lists.columnconfigure(1, weight=1)
        row(2, t("set_lists"), lists)
        th = ttk.Frame(f)
        self.vars["suspect"] = tk.IntVar(value=self.cfg["thresholds"]["suspect"])
        self.vars["phishing"] = tk.IntVar(value=self.cfg["thresholds"]["phishing"])
        ttk.Label(th, text=t("set_suspect")).pack(side="left")
        ttk.Spinbox(th, from_=10, to=90, width=5, textvariable=self.vars["suspect"]).pack(side="left", padx=(4, 16))
        ttk.Label(th, text=t("set_phishing")).pack(side="left")
        ttk.Spinbox(th, from_=30, to=100, width=5, textvariable=self.vars["phishing"]).pack(side="left", padx=4)
        row(3, t("set_thresholds"), th)
        self.vars["notify"] = tk.BooleanVar(value=self.cfg.get("notify", True))
        row(4, t("set_notify"), ttk.Checkbutton(f, text=t("set_notify_chk"), variable=self.vars["notify"]))
        self.vars["model"] = tk.StringVar(value=self.cfg.get("model", "ollama"))
        mf = ttk.Frame(f)
        ttk.Radiobutton(mf, text=t("set_model_ollama"), value="ollama", variable=self.vars["model"]).pack(anchor="w")
        ttk.Radiobutton(mf, text=t("set_model_none"), value="none", variable=self.vars["model"]).pack(anchor="w")
        row(5, t("set_analysis"), mf)
        self.vars["ollama_model"] = tk.StringVar(value=self.cfg.get("ollama_model", "qwen3:4b"))
        row(6, t("set_ollama_model"), ttk.Entry(f, textvariable=self.vars["ollama_model"]))
        cf = ttk.Frame(f)
        self.vars["company"] = tk.StringVar(value=self.cfg.get("company_name", ""))
        self.vars["sector"] = tk.StringVar(value=self.cfg.get("company_sector", ""))
        ttk.Entry(cf, textvariable=self.vars["company"], width=28).pack(side="left")
        ttk.Label(cf, text=t("set_sector")).pack(side="left")
        ttk.Entry(cf, textvariable=self.vars["sector"], width=24).pack(side="left", padx=4)
        row(7, t("set_company"), cf)
        self.cb_lang = ttk.Combobox(f, values=list(LANGUAGES.values()), state="readonly", width=20)
        self.cb_lang.set(LANGUAGES.get(language(), "English"))
        row(8, t("set_language"), self.cb_lang)
        self.vars["autostart"] = tk.BooleanVar(value=startup_shortcut().exists())
        row(9, t("set_autostart"), ttk.Checkbutton(f, text=t("set_autostart_chk"), variable=self.vars["autostart"]))
        bb = ttk.Frame(f)
        ttk.Button(bb, text=t("btn_save"), style="Big.TButton", command=self._save_settings).pack(side="left")
        ttk.Button(bb, text=t("btn_learn"), command=lambda: self._bg(self.engine.learn)).pack(side="left", padx=8)
        bb.grid(row=10, column=0, columnspan=2, sticky="w", pady=(16, 0))
        ttk.Label(f, text=t("data_dir", dir=APP_DIR), style="Sub.TLabel").grid(row=11, column=0, columnspan=2, sticky="w", pady=(16, 0))
        f.columnconfigure(1, weight=1)

    def _build_setup(self):
        f = self.tab_setup
        ttk.Label(f, text=t("setup_title"), font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(f, text=t("setup_intro"), style="Sub.TLabel").pack(anchor="w", pady=(0, 10))
        steps = ttk.Frame(f)
        steps.pack(fill="x")
        self.lbl_step = {}
        for i, (key, text, btn, cmd) in enumerate([
            ("outlook", t("step_outlook"), None, None),
            ("ollama", t("step_ollama"), t("btn_install_ollama"), lambda: self._bg(install_ollama, self.engine.say)),
            ("model", t("step_model"), t("btn_pull"), self._pull),
            ("contacts", t("step_contacts"), t("btn_learn_now"), lambda: self._bg(self.engine.learn)),
        ]):
            self.lbl_step[key] = ttk.Label(steps, text="?  " + text, font=("Segoe UI", 10))
            self.lbl_step[key].grid(row=i, column=0, sticky="w", pady=4)
            if btn:
                ttk.Button(steps, text=btn, command=cmd).grid(row=i, column=1, padx=12)
        ttk.Button(steps, text=t("btn_recheck"), command=lambda: self._bg(self.engine.status)).grid(row=0, column=1, padx=12)
        ttk.Label(f, text=t("progress"), style="Sub.TLabel").pack(anchor="w", pady=(14, 2))
        self.setup_log = tk.Text(f, height=12, font=("Consolas", 9), relief="flat", bg=COLORS["card"])
        self.setup_log.pack(fill="both", expand=True)
        self.setup_log.configure(state="disabled")

    # ------------------------------------------------------------------ actions
    def _bg(self, fn, *a):
        self.worker.submit(fn, *a)

    def _load_mailboxes(self):
        if os.environ.get("MAILGUARD_DEMO"):
            return
        try:
            boxes = Outlook.list_mailboxes()
            self.q.put({"type": "mailboxes", "boxes": boxes})
        except Exception as e:
            self.engine.say(t("outlook_err", err=e))

    def _pull(self):
        self.cfg["ollama_model"] = self.vars["ollama_model"].get().strip() or "qwen3:4b"
        self._bg(pull_model, self.cfg.get("ollama_url", "http://localhost:11434"), self.cfg["ollama_model"], self.engine.say)
        self._bg(self.engine.status)

    def toggle_watch(self):
        if self.engine.watching:
            self.btn_watch.configure(text=t("btn_start"))
            self._bg(self.engine.watch_stop)
        else:
            self.btn_watch.configure(text=t("btn_starting"))
            self._bg(self.engine.watch_start)

    def _apply_changed(self):
        self.cfg["apply_actions"] = self.var_apply.get()
        save_cfg(self.cfg)
        self._status_text(t("apply_on") if self.cfg["apply_actions"] else t("apply_off"))

    def _save_settings(self):
        c = self.cfg
        c["mailbox"] = self.cb_mailbox.get()
        c["own_domains"] = [d.strip().lower() for d in self.vars["own"].get().split(",") if d.strip()]
        trusted = [d.strip().lower() for d in self.txt_trusted.get("1.0", "end").splitlines() if d.strip()]
        blocked = [d.strip().lower() for d in self.txt_blocked.get("1.0", "end").splitlines() if d.strip()]
        c["trusted_domains"] = [d for d in trusted if "@" not in d]
        c["trusted_senders"] = [d for d in trusted if "@" in d]
        c["blocked_domains"] = [d for d in blocked if "@" not in d]
        c["blocked_senders"] = [d for d in blocked if "@" in d]
        c["thresholds"] = {"suspect": int(self.vars["suspect"].get()), "phishing": int(self.vars["phishing"].get())}
        c["notify"] = self.vars["notify"].get()
        c["model"] = self.vars["model"].get()
        c["ollama_model"] = self.vars["ollama_model"].get().strip() or "qwen3:4b"
        c["company_name"] = self.vars["company"].get().strip()
        c["company_sector"] = self.vars["sector"].get().strip()
        new_lang = next((code for code, name in LANGUAGES.items() if name == self.cb_lang.get()), language())
        lang_changed = new_lang != c.get("language")
        c["language"] = new_lang
        save_cfg(c)
        try:
            set_autostart(self.vars["autostart"].get())
        except Exception as e:
            messagebox.showwarning(t("autostart_title"), t("autostart_err", err=e))
        self.engine.ol = None
        self.engine.model = None
        self._status_text(t("saved") + ("  " + t("restart_hint") if lang_changed else ""))
        if self.engine.watching:
            self._bg(self.engine.watch_stop)
            self._bg(self.engine.watch_start)

    def _selected(self) -> dict | None:
        sel = self.tree.selection()
        return self.records.get(sel[0]) if sel else None

    def _open(self):
        rec = self._selected()
        if rec and rec.get("entry_id"):
            self._bg(self.engine.open_in_outlook, rec["entry_id"])

    def _mark_safe(self):
        rec = self._selected()
        if not rec:
            return
        who = rec.get("sender_addr") or rec.get("sender_domain") or ""
        if messagebox.askyesno(t("confirm_safe_title"), t("confirm_safe", who=who)):
            self._bg(self.engine.mark_safe, rec)
            self.tree.item(self.tree.selection()[0], values=self._values({**rec, "level": "ok", "action": t("action_user_trusted")}), tags=("trusted",))

    def _mark_phishing(self):
        rec = self._selected()
        if not rec:
            return
        if messagebox.askyesno(t("confirm_phish_title"), t("confirm_phish")):
            self._bg(self.engine.mark_phishing, rec)
            self.tree.item(self.tree.selection()[0], values=self._values({**rec, "level": "phishing", "action": t("action_user_moved")}), tags=("phishing",))

    def _clear(self):
        self.tree.delete(*self.tree.get_children())
        self.records.clear()

    # ------------------------------------------------------------------ engine events
    def _values(self, rec: dict):
        if rec.get("test"):
            when = t("sample_time")
        else:
            when = rec.get("received", "")
            when = when[5:16].replace("T", " ") if len(when) > 15 else when
        return (when, rec.get("score", 0), t("level_" + rec.get("level", "ok")), rec.get("sender_addr", rec.get("from", "")),
                rec.get("subject", ""), rec.get("action", ""))

    def _add_row(self, rec: dict, scroll: bool = True):
        tags = ()
        if rec.get("level") in ("phishing", "suspect"):
            tags = (rec["level"],)
        elif rec.get("trusted"):
            tags = ("trusted",)
        iid = self.tree.insert("", 0, values=self._values(rec), tags=tags)
        self.records[iid] = rec
        if len(self.records) > 500:
            old = self.tree.get_children()[-1]
            self.tree.delete(old)
            self.records.pop(old, None)
        if scroll:
            self.tree.see(iid)

    def _show_detail(self, _=None):
        rec = self._selected()
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        if rec:
            lines = [f"{t('det_from')}: {rec.get('from')}", f"{t('det_subject')}: {rec.get('subject')}",
                     f"{t('det_score')}: {rec.get('score')}  |  {t('level_' + rec.get('level', 'ok'))}  |  {rec.get('action')}"]
            a = rec.get("auth") or {}
            if a:
                lines.append(f"{t('det_auth')}: SPF={a.get('spf') or '?'} DKIM={a.get('dkim') or '?'} DMARC={a.get('dmarc') or '?'}")
            if rec.get("links"):
                lines.append(f"{t('det_links')}: " + ", ".join(rec["links"][:10]))
            if rec.get("reasons"):
                lines.append(t("det_reasons"))
                lines += [f"  - {x}" for x in rec["reasons"]]
            elif rec.get("trusted"):
                lines.append(t("det_trusted"))
            self.detail.insert("1.0", "\n".join(lines))
        self.detail.configure(state="disabled")

    def _status_text(self, text: str):
        self.statusbar.configure(text=text)

    def _setup_log(self, text: str):
        self.setup_log.configure(state="normal")
        self.setup_log.insert("end", text + "\n")
        self.setup_log.see("end")
        self.setup_log.configure(state="disabled")

    def _poll(self):
        try:
            while True:
                ev = self.q.get_nowait()
                kind = ev.get("type")
                if kind == "mail":
                    self._add_row(ev)
                elif kind == "log":
                    self._status_text(ev["text"])
                    self._setup_log(ev["text"])
                elif kind == "status":
                    self.lbl_outlook.configure(text=f"Outlook: {OK_MARK + ' ' + ev['outlook_msg'] if ev['outlook'] else BAD_MARK + ' ' + t('outlook_unreachable')}",
                                               foreground=COLORS["ok"] if ev["outlook"] else COLORS["bad"])
                    if ev["model"]:
                        mtxt, col = f"{OK_MARK} {t('model_ready')}", COLORS["ok"]
                    elif ev["ollama_installed"]:
                        mtxt, col = f"{BAD_MARK} {t('model_missing')}", COLORS["warn"]
                    else:
                        mtxt, col = f"{BAD_MARK} {t('ollama_missing')}", COLORS["warn"]
                    self.lbl_ollama.configure(text=t("model_prefix") + mtxt, foreground=col)
                    for key, val in (("outlook", ev["outlook"]), ("ollama", ev["ollama_installed"]), ("model", ev["model"]), ("contacts", ev["contacts"])):
                        lbl = self.lbl_step[key]
                        lbl.configure(text=(OK_MARK if val else BAD_MARK) + lbl.cget("text")[1:], foreground=COLORS["ok"] if val else COLORS["bad"])
                elif kind == "watch":
                    self.btn_watch.configure(text=t("btn_stop") if ev["on"] else t("btn_start"))
                    self._update_tray()
                elif kind == "mailboxes":
                    self.cb_mailbox.configure(values=ev["boxes"])
                    if not self.cb_mailbox.get() and ev["boxes"]:
                        self.cb_mailbox.set(ev["boxes"][0])
        except queue.Empty:
            pass
        self.root.after(150, self._poll)

    # ------------------------------------------------------------------ tray
    def _start_tray(self):
        try:
            import pystray
        except Exception:
            return
        self.pystray = pystray
        self.tray_icon = pystray.Icon("MailGuard", _icon_image(), "MailGuard", menu=self._tray_menu())
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _tray_menu(self):
        ps = self.pystray
        return ps.Menu(
            ps.MenuItem(t("tray_open"), lambda: self.root.after(0, self.show), default=True),
            ps.MenuItem(lambda item: t("btn_stop") if self.engine.watching else t("btn_start"), lambda: self.root.after(0, self.toggle_watch)),
            ps.Menu.SEPARATOR,
            ps.MenuItem(t("tray_quit"), lambda: self.root.after(0, self.quit)),
        )

    def _update_tray(self):
        if self.tray_icon:
            self.tray_icon.title = t("tray_active") if self.engine.watching else t("tray_paused")
            try:
                self.tray_icon.update_menu()
            except Exception:
                pass

    def show(self):
        self.root.deiconify()
        self.root.lift()

    def hide(self):
        if self.tray_icon:
            self.root.withdraw()
            self._status_text(t("tray_hidden"))
        else:
            self.quit()

    def quit(self):
        self.worker.running = False
        self.engine.stop()
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.root.destroy()


def run(tray: bool = False):
    root = tk.Tk()
    App(root, tray=tray)
    root.mainloop()
    return 0
