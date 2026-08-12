# ErsatzTV Content Workflow — Repeatable Process

*A real, step-by-step SOP for adding content to The Table IPTV — not
architecture, just "what do I actually click, in order, every time."
Companion to DEPLOYMENT_MANUAL.md, which covers how the system works.*

---

## First question, every time: does this need exact order?

This decides everything downstream. Get this right first.

**No, random/shuffle is fine** (e.g. general rotation additions)
→ Go to **Workflow A**

**Yes, this needs a specific hand-picked order** (e.g. a Top 10
countdown, a curated block)
→ Go to **Workflow B**

---

## Workflow A — Adding to normal rotation (the common case)

1. Copy video file(s) into `/opt/media/<Artist Name>/<Song Title>.mkv`
2. That's it. **Do not manually create `.nfo` files.** The cron job
   (`generate_nfo.py`, runs every 25 min) handles this automatically —
   it only creates NFOs for videos missing one, never touches existing
   ones. Safe, hands-off.
3. New content enters rotation on ErsatzTV's next automatic playout
   rebuild (within 24h) — or trigger "Rebuild Playout" manually in
   ErsatzTV's UI if it needs to appear sooner.

Nothing else needed. No schedule changes, no order to manage.

---

## Workflow B — Building an exact-order block (e.g. a Top 10)

### Step 1 — Build the Playlist (not a Collection, not a Multi Collection)

- Confirmed via real testing: only a **Playlist** actually preserves
  custom order. Collections only offer Chronological/Shuffle. Multi
  Collections don't preserve order either, in either the Block or
  Classic system.
- In ErsatzTV: create a new Playlist. Add each song **individually, one
  at a time, in the exact order you want them to play.** Row order in
  the Playlist *is* the playback order — nothing else to configure for
  ordering.

### Step 2 — Convert your intended air time to UTC by hand

- Confirmed: ErsatzTV's server clock and its own internal scheduling
  clock are both UTC. No reliable "local time" setting has been found.
  **Always enter times in UTC, converted by hand.**
- Formula: `UTC time = local time + your UTC offset`
  (Mountain Daylight Time, MDT, is UTC−6 in summer → add 6 hours.
  Mountain Standard Time, MST, is UTC−7 in winter → add 7 hours.)
- Example: 8:00 PM MDT tonight = **2:00 AM UTC tomorrow's date.** Watch
  the date rollover — this is the easiest part to get wrong.

### Step 3 — Add it as a Classic Schedule Item (not a Block)

- Confirmed real bug: Block-based RandomRotation can silently play only
  one item instead of filling its duration (confirmed by another user
  independently on ErsatzTV's own forum). **Use Classic Schedules for
  anything like this.**
- Add the Playlist as a **new item in the same schedule your normal
  360 rotation already uses** — don't build a separate schedule.
  - Your existing rotation item: leave it exactly as-is (Dynamic start,
    Flood playout mode — this is what makes it flow continuously and
    resume automatically after the new block ends).
  - New item: **Start Type = Fixed**, time = the UTC value from Step 2,
    Collection Type = **Playlist**, **Playout Mode = Multiple**, Count =
    however many songs are actually in the Playlist. **Never use
    Playout Mode "One"** — confirmed bug, plays only the first song.

### Step 4 — Verify in Preview Playout before trusting it

- Set rows-per-page to 100 so you can actually see enough of the
  schedule to check it properly.
- Confirm, scrolling through a real stretch of time:
  - [ ] The block starts at the correct real-world moment (double-check
        your UTC math against what actually shows)
  - [ ] All songs play in the intended order
  - [ ] No "UNSCHEDULED" gaps anywhere near the transition
  - [ ] It hands off cleanly back into normal rotation afterward
- If anything's off, fix it and re-check. Don't trust a single glance —
  scroll through multiple real transitions.

### Step 5 — Build and test on the *unused* channel first, never live

- This project runs 3 channels specifically for this reason (see
  DEPLOYMENT_MANUAL.md Section 5). Build and fully verify the new
  programming on whichever channel isn't currently public.
- Only once Step 4's checklist is fully clean, move to the actual cutover.

### Step 6 — Cut over using the blue-green swap

1. Config manager → Settings tab → change `video.channelNumber` to the
   now-tested channel.
2. Either let it take effect naturally on the next page load, or use
   **"Push Channel to Everyone"** to force it within ~2 minutes.
3. Load the live site fresh yourself and confirm it's actually playing
   the right thing before considering it done.
4. The old channel stays fully intact — if anything's wrong after
   cutover, just switch the channel number back. Real, instant
   rollback, no rebuilding required.

---

## Quick reference — things that look like bugs but are known ErsatzTV quirks

| Symptom | Real cause | Fix |
|---|---|---|
| Only one track plays instead of filling the block | Block-based RandomRotation bug | Use Classic Schedules, not Blocks |
| Custom order doesn't stick | Multi Collection / plain Collection, not a Playlist | Use a Playlist, one song at a time |
| Time entered doesn't match when it actually airs | Both clocks are UTC, no real conversion setting | Convert by hand every time (Step 2 above) |
| Only the first song of a Playlist plays | Playout Mode set to "One" | Set to "Multiple", with the real Count |
| A pile of clips loop randomly instead of playing once | "Filler" is a random-fill pool, not a bumper | Don't use Filler for a one-time bumper — see the ErsatzTV-Filler tool idea in QUEUED_CHANGES.md instead |
| Recently Played shows the wrong title for a few minutes right after a Fixed cutover | Real, isolated ErsatzTV server-side timing quirk — not fixable on the website side | Known, cosmetic, low-priority — see DEPLOYMENT_MANUAL.md Section 6 |

---

*Update this file the moment a new real quirk gets discovered — that's
the whole point of it existing.*
