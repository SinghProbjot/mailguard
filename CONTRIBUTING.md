# Contributing

Thanks for taking the time. MailGuard is a small project and contributions of any size are welcome, from a typo fix to a new detection rule.

## Reporting a phishing mail that slipped through

This is the most useful kind of report. Open an issue with:

- the sender address and domain (feel free to mask the local part),
- the `reasons` and `findings` lines for that mail from `%APPDATA%\MailGuard\mailguard_log.jsonl`,
- a short description of what made it recognisable to a human.

Please never paste the full raw mail or any link from it into an issue.

## Reporting a false positive

Same as above. Before opening the issue, check whether marking the sender as trusted from the activity view solves it; if a whole category of legitimate mail is affected, that is worth a rule change.

## Code changes

1. Fork, create a branch, install the requirements: `pip install -r requirements.txt`.
2. Run `python -m mailguard test --no-model` before and after your change. The sample set in `mailguard/samples.py` must still pass; add a sample if you add a rule.
3. If you touch the scoring, run `python -m mailguard scan --last 100` on your own mailbox and look at what changed.
4. Keep rules deterministic and explainable: every finding carries a sentence the user will read in a notification.
5. Open a pull request and describe the mail pattern you are targeting.

Every user facing string lives in `mailguard/i18n.py` with an English and an Italian version. New strings need both; a new language is a third value on each entry plus its name in `LANGUAGES`.

## Style

Standard Python, type hints where they help, no framework. Comments explain why, not what.
