# The Table IPTV — Deployment & Operations Manual

*Written so a stranger with no prior context could take over running this
site. If you're reading this because something broke and the founder is
unavailable, start with "Emergency Procedures" below.*

---

## 1. What This Is

The Table IPTV (tableip.tv) is a self-hosted, 24/7 linear music video
channel for independent artists. No ads, no algorithm, no app — a real
website with a real video stream, built and run by one person.

**The stack, at a glance:**
- **ErsatzTV** — turns a folder of video files into a real, scheduled
  24/7 broadcast channel (like an old-school TV station)
- **Nginx** — web server, serves the website and proxies the video stream
- **Cloudflare** — DNS, CDN edge, and hosts a small Worker + D1 database
  for the community voting feature
- **A single VPS** (OVH, Montreal) — everything above runs on this one
  server
- **A local desktop app** (`table_config_manager.py`) — lets the founder
  edit site settings/theme/content and deploy changes without manually
  SSHing in every time

---

## 2. Where Everything Lives

| What | Where |
|---|---|
| Website files (`index.html`, `settings.json`, `theme.json`, `content.json`, `welcome.json`, `artist-links.json`, `financials.html`, `privacy.html`, `dmca.html`, `artists.html`) | `/var/www/html/` on the VPS |
| Music video library | `/opt/media/<Artist Name>/<Song Title>.mkv` (one folder per artist) |
| NFO auto-generator script | `/opt/media/generate_nfo.py`, runs via cron every 25 min |
| NFO generator logs | `/opt/media/generate_nfo.log` and `generate_nfo_cron.log` |
| ErsatzTV itself | Runs as its own service on the VPS — access its web UI directly (ask the founder for the URL/port if not already bookmarked) |
| Local config manager app | Lives on the founder's own Windows machine, not on the server. Connects over SFTP. |
| Config manager backups | `./backups/` folder next to the app itself, on the founder's local machine — **not on the server** |
| Cloudflare Worker + D1 (voting) | Managed entirely through the Cloudflare dashboard, not the VPS |

---

## 3. How to Deploy a Change

**Normal changes (settings, theme, content, artist links):**
Use the config manager app (`table_config_manager.py`) on a Windows
machine with `paramiko` installed (`pip install paramiko`). Connect via
the Connection tab, then use each tab's Load/Save buttons. **Every save
automatically backs up the current live file first** — this is a real,
built-in safety net, not optional.

**Changes to `index.html` or other static pages:**
These aren't editable through the config manager's forms — they need to
be edited directly and uploaded via SFTP (the config manager's
Connection tab establishes this same SFTP session; any SFTP client, or
this same underlying connection, can be used to upload a replacement
file to `/var/www/html/`).

**After any change that could affect the live stream specifically**
(channel number, schedule): verify by actually loading the site fresh in
a browser and confirming it plays correctly, before considering the
change done.

---

## 4. Adding New Music

1. Create/copy video files into `/opt/media/<Artist Name>/<Song Title>.mkv`
   (or `.mp4`, `.avi`, `.mov`, `.m4v`).
2. That's it — **do not manually create `.nfo` files.** A cron job runs
   `generate_nfo.py` automatically every 25 minutes, which finds any
   video missing a matching `.nfo` and creates one (with the correct
   Kodi-format metadata ErsatzTV needs for on-screen credits). It never
   touches or overwrites an existing `.nfo`, so it's always safe to
   re-run and safe to have running unattended.
3. Within ~25 minutes, the new song will have its `.nfo` file. It'll
   enter rotation on ErsatzTV's next scheduled playout rebuild (normally
   within 24 hours automatically) — or trigger "Rebuild Playout"
   manually in ErsatzTV's UI if it needs to appear sooner.

---

## 5. The Channel-Swap Pattern

This site runs **three ErsatzTV channels**, not one:

- **Channel 1** — the real, live public channel viewers actually watch
- **Channel 2** — the "off" slot in an alternating pair with Channel 1,
  swapped roughly once a year for a clean cache reset (new channel
  number = fresh URLs = no stale browser-cached segments)
- **Channel 3** — used for building/testing new programming (like a
  Top 10 or New Artists block) before it's ready to go live, and for
  personal listening while curating new content

**To cut a new build over to the public:**
1. Build and fully test the new programming on Channel 3 first —
   confirm in ErsatzTV's Preview Playout that content, order, and
   timing all look correct.
2. In the config manager's Settings tab, change `video.channelNumber`
   to match the channel you just built.
3. Either wait for a normal page reload, or use the **"Push Channel to
   Everyone"** button (Settings tab) to force every currently-connected
   viewer's browser to reload within ~2 minutes and pick up the new
   channel automatically.
4. Confirm the live site is playing correctly before considering the
   swap done. The old channel stays fully intact and untouched — if
   anything's wrong, just switch the channel number back.

---

## 6. Known ErsatzTV Quirks (Real, Confirmed, Not User Error)

These are genuine, tested issues in ErsatzTV itself, not mistakes in
this project's setup. Documented here so nobody wastes hours
re-discovering them:

- **Block-based "RandomRotation" can silently play only one item**
  instead of filling the whole block duration. Confirmed via ErsatzTV's
  own community forum — other users hit the identical bug. Workaround:
  use Classic Schedules (not Blocks) for anything needing multiple
  randomized items to fill a time span.
- **Multi Collections don't support genuine custom ordering** — only
  Shuffle-based orders, in both the Block and Classic systems. For an
  exact, hand-picked order (like a Top 10 countdown), use a **Playlist**
  instead, adding individual songs one at a time in the desired order.
- **The server's system clock and ErsatzTV's own internal scheduling
  clock are both UTC**, with no reliable timezone-conversion setting
  found. When entering a schedule time, do the UTC math by hand (e.g.,
  8:00 PM Mountain Daylight Time = 2:00 AM UTC the *next* calendar
  date) rather than trusting a "local time" field.
- **Fixed-time schedule cutovers introduce a real, consistent timing
  offset** on the website's Recently Played/Guide display for content
  right after the cutover (observed: ~50 seconds early). Root cause
  isolated to ErsatzTV's own segment generation around a forced
  mid-file cut — confirmed NOT a bug in this site's own code (ruled out
  via direct testing). Low-priority, cosmetic only.
- **Schedule item "Filler" is a random-fill pool, not a one-time
  bumper.** Adding multiple clips to a Filler slot causes ErsatzTV to
  shuffle through all of them repeatedly to fill the gap, not play one
  clip once. If a genuine single "please wait" style card is wanted, use
  the separate community tool **ErsatzTV-Filler**
  (liam8888999.github.io/ErsatzTV-Filler) instead — it's purpose-built
  for this and reads real schedule data to show the actual next show
  and start time.

---

## 7. Emergency Procedures

**Site is down / stream isn't playing:**
1. SSH into the VPS, check `htop` for obvious problems (memory, load).
2. Check ErsatzTV's own web UI — is the relevant channel's playout
   actually built and current?
3. If a recent config manager save is the likely cause, use the
   Rollback tab to restore the previous backup — every save auto-backs
   up the prior version first, so a clean restore point almost always
   exists.

**A live channel got accidentally broken while editing** (e.g., a
schedule edit meant for a test channel accidentally applied to the live
one): switch `video.channelNumber` (config manager, Settings tab) to a
different, known-good channel immediately — this takes real viewers off
the broken feed within moments. Fix the actual problem afterward, with
no live-viewer pressure.

**A takedown request comes in:** reply within 24 hours, personally —
this is a real, public promise on the site (`/dmca.html`,
`/financials.html`). Remove the specific content from `/opt/media/`
(and its `.nfo`) if the request is valid, then trigger a playout
rebuild so it stops airing.

**Full site restore needed:** the config manager's Rollback tab has a
"Backup entire site now" / "Restore selected snapshot" pair that
handles `index.html` plus every config/policy file together as one
timestamped bundle — this is the real, complete disaster-recovery path.

---

## 8. What's Deliberately Not Automated

Some things are intentionally kept manual, not automation gaps:

- **Content curation** — what actually gets added to the channel is a
  deliberate human judgment call, not a script's decision. This is
  core to what makes the channel feel curated rather than random.
- **Artist relationships and outreach** — real replies from a real
  person, always.
- **Takedown responses** — same reasoning; a bot reply would undercut
  the actual trust promise being made.

---

## 9. Open Items / Known Gaps

See `QUEUED_CHANGES.md` for the current, maintained list of what's
genuinely still open (New Artists block build-out, Nginx security
headers not yet deployed, infra backup automation, etc.) — this manual
covers *how the system works*, that file tracks *what's left to build*.

---

*This document should be updated whenever something in Sections 2-6
changes. A manual that's gone stale is worse than no manual — it gives
false confidence.*
