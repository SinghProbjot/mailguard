"""Entry point for MailGuard.exe (PyInstaller) and for `python MailGuard.py`."""
import sys
from mailguard.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
