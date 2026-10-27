"""MailGuard, usage:

  python -m mailguard                            open the desktop application
  python -m mailguard --tray                     start minimised to the tray with protection on
  python -m mailguard scan  --last 50            analyse the last 50 mails (report only, nothing is moved)
  python -m mailguard scan  --last 50 --apply    ... and apply the actions (Junk / category)
  python -m mailguard watch                      watch the Inbox from the command line (alerts only)
  python -m mailguard watch --apply              ... and really move phishing to Junk
  python -m mailguard test                       run the built in samples through the pipeline
  python -m mailguard learn                      re-read the mailbox to learn colleagues and correspondents

Options: --no-model (rules only)  --folder "Folder name"  (scan another folder, e.g. Deleted Items)
"""
from __future__ import annotations
import argparse
import sys

from .i18n import t

ICON = {"ok": "  ", "suspect": "?!", "phishing": "XX"}


def _print_event(ev: dict):
    kind = ev.get("type")
    if kind == "log":
        print(ev["text"])
    elif kind == "mail":
        tag = " (trusted)" if ev.get("trusted") else ""
        when = t("sample_time") if ev.get("test") else ev["received"][5:16]
        print(f"{ICON[ev['level']]} {ev['score']:3d}  {when:<11}  {ev['sender_addr'][:38]:<38}  {ev['subject'][:55]}{tag}")
        for r in ev.get("reasons", []):
            print(f"        - {r}")
        if ev["level"] != "ok":
            print(f"        => {ev['action']}")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0].startswith("--"):
        from .gui import run
        return run(tray="--tray" in argv)

    p = argparse.ArgumentParser(prog="mailguard", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("scan", "watch", "test", "learn"):
        sp = sub.add_parser(name)
        sp.add_argument("--apply", action="store_true", help="really apply the actions (default: report only)")
        sp.add_argument("--no-model", action="store_true", help="rules only, without the model")
        sp.add_argument("--folder", default=None, help="folder to analyse (default: Inbox)")
        if name == "scan":
            sp.add_argument("--last", type=int, default=30)
    args = p.parse_args(argv)

    from .engine import Engine
    eng = Engine(emit=_print_event)
    if args.no_model:
        eng.use_model = False
    if args.cmd == "scan":
        eng.scan(args.last, apply=args.apply, folder_name=args.folder)
    elif args.cmd == "watch":
        try:
            eng.watch(apply=args.apply)
        except KeyboardInterrupt:
            eng.stop()
    elif args.cmd == "test":
        return eng.test_samples()
    elif args.cmd == "learn":
        eng.learn()


if __name__ == "__main__":
    sys.exit(main())
