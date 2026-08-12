# The Table IPTV

Source code and tooling for [tableip.tv](https://tableip.tv) — a
self-hosted, ad-free, algorithm-free 24/7 music video channel for
independent artists. Built and run by one person.

## What's in this repo

- `index.html` — the live site itself
- `financials.html`, `privacy.html`, `dmca.html`, `artists.html` —
  policy and info pages
- `generate_nfo.py` — auto-generates the metadata files ErsatzTV needs
  for on-screen artist/song credits, runs on a cron timer on the VPS
- `table_config_manager.py` — local desktop app for editing site
  settings/theme/content over SFTP, with automatic backups before every
  save
- `DEPLOYMENT_MANUAL.md` — how the whole system actually works, written
  so a stranger could pick it up
- `QUEUED_CHANGES.md` — real, current list of what's still open

## What's *not* in this repo

`settings.json`, `theme.json`, `content.json`, `welcome.json`, and
`artist-links.json` are live configuration data, not source code — they
already have their own backup/rollback system built into the config
manager app. Tracking them here too would just create two competing
copies of the truth. See `DEPLOYMENT_MANUAL.md` for where the real,
current versions of those files actually live.

## Running the config manager

```
pip install paramiko
python table_config_manager.py
```

Connects to the VPS over SFTP — no credentials are ever saved to disk,
you enter them fresh each session.

## The model

The Table runs on donations, not ads. The full, honest financial
breakdown — real numbers, published openly — is at
[tableip.tv/financials.html](https://tableip.tv/financials.html).
