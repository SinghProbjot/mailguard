# Security

MailGuard reads your mailbox, so it deserves scrutiny. A few facts about what it does and does not do:

- It never sends mail content, links, addresses or attachments anywhere. The only outbound connections are to `localhost:11434` (Ollama) and, if you use the guided setup, to the Ollama download servers to fetch the program and the model.
- It never opens links or attachments. Links are parsed as text and unwrapped only by string manipulation.
- It never deletes mail. The only write operations are moving a message to Junk, moving it back to the Inbox and setting an Outlook category, and the move happens only when automatic actions are explicitly enabled.
- All data it keeps lives in `%APPDATA%\MailGuard` and can be deleted at any time.

## Reporting a vulnerability

If you find a way in which MailGuard could be abused, for example a crafted mail that crashes the parser or that makes the tool take an unintended action, please open a GitHub issue with the label `security`. If the details should not be public, say so in the issue and a private channel will be arranged. Please do not include working phishing samples in public issues.
