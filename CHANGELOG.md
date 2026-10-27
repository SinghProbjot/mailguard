# Changelog

## 1.0.0 (2026-10-27)

First public release.

- Outlook integration through COM, no server side configuration and no admin rights.
- Deterministic checks on authentication headers, sender address, display name, links, redirects and attachments.
- Trusted senders learned from the mailbox: colleagues, habitual correspondents and replies to your own threads.
- Optional local language model (Ollama, Qwen3 4B) for mails that the rules cannot settle on their own.
- Desktop application with activity view, settings, guided setup and a tray icon, in English and Italian.
- Feedback buttons that update trusted and blocked lists and feed examples back to the model.
- Windows toast notifications with the reasons behind every decision.
- Single file executable and a per-user installer with optional autostart.
