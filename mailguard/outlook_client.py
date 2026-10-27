"""Classic Outlook access through COM (pywin32). Everything stays on the PC."""
from __future__ import annotations
from datetime import datetime, timedelta
import pythoncom
import win32com.client
from .extract import Mail, extract_links, html_to_text, msg_ids, parse_auth, parse_headers

PROPTAG = "http://schemas.microsoft.com/mapi/proptag/"
PR_SMTP_ADDRESS = PROPTAG + "0x5D01001F"
PR_TRANSPORT_HEADERS = PROPTAG + "0x007D001F"
PR_INTERNET_MESSAGE_ID = PROPTAG + "0x1035001F"
OL_MAIL = 43
OL_INBOX = 6
OL_JUNK = 23


class Outlook:
    def __init__(self, mailbox: str | None = None):
        pythoncom.CoInitialize()
        self.app = win32com.client.Dispatch("Outlook.Application")
        self.ns = self.app.GetNamespace("MAPI")
        self.mailbox = mailbox
        store = None
        if mailbox:
            store = next((s for s in self.ns.Stores if s.DisplayName.lower() == mailbox.lower()), None)
            if store is None:
                raise RuntimeError(f"Casella {mailbox} non trovata in Outlook")
        else:
            store = self.ns.GetDefaultFolder(OL_INBOX).Store
            self.mailbox = store.DisplayName
        self.store = store
        self.inbox = store.GetDefaultFolder(OL_INBOX)
        self.junk = store.GetDefaultFolder(OL_JUNK)
        self.root = store.GetRootFolder()

    @staticmethod
    def list_mailboxes() -> list[str]:
        pythoncom.CoInitialize()
        app = win32com.client.Dispatch("Outlook.Application")
        ns = app.GetNamespace("MAPI")
        out = []
        for s in ns.Stores:
            try:
                if s.ExchangeStoreType in (0, 1, 2) or "@" in s.DisplayName:
                    out.append(s.DisplayName)
            except Exception:
                pass
        return out or [s.DisplayName for s in ns.Stores]

    @property
    def address(self) -> str:
        """SMTP address of the mailbox (used to derive the company domain)."""
        for acc in self.ns.Accounts:
            try:
                if acc.DeliveryStore.StoreID == self.store.StoreID:
                    return acc.SmtpAddress
            except Exception:
                pass
        return self.mailbox if "@" in self.mailbox else ""

    # ---------- reading ----------
    def _prop(self, item, tag: str) -> str:
        try:
            return item.PropertyAccessor.GetProperty(tag) or ""
        except Exception:
            return ""

    def to_mail(self, item, max_body: int) -> Mail:
        sender_type = (item.SenderEmailType or "").upper()
        addr = self._prop(item, PR_SMTP_ADDRESS)
        if not addr:
            if sender_type == "EX":
                try:
                    addr = item.Sender.GetExchangeUser().PrimarySmtpAddress
                except Exception:
                    addr = item.SenderEmailAddress or ""
            else:
                addr = item.SenderEmailAddress or ""
        headers = parse_headers(self._prop(item, PR_TRANSPORT_HEADERS))
        reply_to = []
        try:
            reply_to = [r.Address for r in item.ReplyRecipients]
        except Exception:
            pass
        reply_to += [v for v in headers.get("reply-to", [])]
        try:
            html = item.HTMLBody or ""
        except Exception:
            html = ""
        try:
            plain = item.Body or ""
        except Exception:
            plain = ""
        body = plain if plain.strip() else html_to_text(html)
        body = body[:max_body]
        try:
            atts = [a.FileName for a in item.Attachments]
        except Exception:
            atts = []
        rt = item.ReceivedTime
        received = datetime.fromtimestamp(rt.timestamp()).isoformat(timespec="minutes") if rt else ""
        return Mail(
            entry_id=item.EntryID,
            subject=item.Subject or "",
            sender_name=item.SenderName or "",
            sender_addr=addr,
            sender_type=sender_type,
            reply_to=reply_to,
            body=body,
            links=extract_links(html, plain),
            attachments=atts,
            auth=parse_auth(headers),
            received=received,
            message_id=(msg_ids([self._prop(item, PR_INTERNET_MESSAGE_ID)]) or [""])[0],
            in_reply_to=msg_ids(headers.get("in-reply-to", []) + headers.get("references", [])),
        )

    def recent_items(self, limit: int | None = None, since: datetime | None = None, folder=None):
        """Mail items (newest first) from the folder; stops at `limit` or when ReceivedTime < since."""
        folder = folder or self.inbox
        items = folder.Items
        items.Sort("[ReceivedTime]", True)
        n = 0
        for it in items:
            try:
                if it.Class != OL_MAIL:
                    continue
                if since is not None:
                    rt = it.ReceivedTime
                    if rt and datetime.fromtimestamp(rt.timestamp()) < since:
                        break
            except Exception:
                continue
            yield it
            n += 1
            if limit and n >= limit:
                break

    def item_by_id(self, entry_id: str):
        return self.ns.GetItemFromID(entry_id)

    def folder_by_name(self, name: str):
        for f in self.root.Folders:
            if f.Name.lower() == name.lower():
                return f
        return self.root.Folders.Add(name)

    # ---------- actions ----------
    def set_category(self, item, category: str):
        cats = [c.strip() for c in (item.Categories or "").split(";") if c.strip()]
        if category not in cats:
            cats.append(category)
            item.Categories = "; ".join(cats)
            item.Save()

    def move_to_junk(self, item):
        return item.Move(self.junk)

    def move_to_inbox(self, item):
        return item.Move(self.inbox)

    def move_to_folder(self, item, name: str):
        return item.Move(self.folder_by_name(name))
