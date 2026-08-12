# The Table IPTV — Queued Changes

Updated after cleanup pass — several items below were done across recent
sessions but never marked off. This is the real, current list.

---

## Genuinely still open

1. **Nginx security headers** — written and ready, just needs deploying
   whenever the timing feels right.

2. **Build the New Artists block for real in ErsatzTV** — currently only
   a placeholder time in the website's countdown banner. Top 10 is the
   one slot that's actually confirmed working end to end.

3. **Monthly Top 10 / New Artists rotation automation** — design is
   fully worked out (see below), nothing built yet:
   - Top 10 auto-refresh: monthly cron pulls real vote data from the
     existing Worker/D1 `/api/top` endpoint, matches artist/song text
     back to files on disk, copies winners into the Top 10 folder. Real
     risk: text-matching could silently misfire on formatting
     differences (capitalization, "feat." vs "ft.") — needs careful
     design, not a quick script.
   - New Artists marker: use `^` in the folder name (e.g. `LOST FUZZ^`)
     — never `*`, that's a shell wildcard and can cause silent breakage.
   - Fair graduation timing: an artist survives through the *next full*
     reset cycle after the one they were added into (added on the 14th
     → keeps status through the rest of that month PLUS the whole
     following month), not a flat month-end cutoff. Needs a small
     manifest tracking real add-dates, since a folder name alone can't
     carry a timestamp.

4. **Whole-infrastructure backup automation** (deferred, "all at once,
   later") — three separate jobs, not one feature:
   - Nginx config + ErsatzTV settings → fits the config manager pattern
   - Music library → needs rclone or similar, not SFTP-app scale
   - Cloudflare DNS/cache rules, Worker, D1 → need Cloudflare's own tools

5. **Report two confirmed ErsatzTV bugs to their community forum** —
   decided this was worth doing, never actually done:
   - Block RandomRotation silently playing only one item (another user
     independently hit the same bug — real, confirmed, not user error)
   - The ~50s Recently Played timing drift tied specifically to
     Fixed-time schedule cutovers (isolated via Channel 1 vs Channel 3
     comparison — see DEPLOYMENT_MANUAL.md Section 6 for full writeup)

6. **"Channel-Offline" bumper via ErsatzTV-Filler** (new idea) — a real,
   purpose-built community tool that auto-generates a "please wait" card
   using actual XMLTV data (real next-show name + start time), replacing
   the current blank-flicker gap before Fixed-time cutovers. Needs one
   schedule item with custom title exactly `Channel-Offline`.
   https://liam8888999.github.io/ErsatzTV-Filler/filler-types/channel-offline/

7. **Mystery report-only CSP header** — still untraced. Currently
   harmless (report-only), but worth finding the source eventually.

---

## Recently completed (moved out of "open")

- ✅ `generate_nfo.py` — real Artist/song.mkv structure, cron-automated
  every 25 min, tested and confirmed running on real content
- ✅ Config manager's full-site backup — was silently missing every
  page/asset added since the tool was first built; fixed and verified
- ✅ `DEPLOYMENT_MANUAL.md` — full operations manual written
- ✅ `artists.html` — dedicated artist-facing landing page, linked from
  the Menu
- ✅ `financials.html` doc link fixed to `.pdf` (was `.docx`)
- ✅ Recently Played ~50s drift — root cause isolated (ErsatzTV
  server-side, not fixable in site code), no longer an open mystery,
  just an open "report it upstream" item (see #5 above)

---

## Explicitly decided AGAINST (context, not action items)

- Local SQLite votes instead of Cloudflare Worker/D1
- Bunny CDN re-enable before sustained 100+ concurrent for 15+ min
- Shortening the 24h ErsatzTV playout rebuild window

---

*No code needed until requested.*

## Production-readiness gaps — identified, partially addressed

Real self-assessment against "would a genuine production system ship
with these gaps" — started closing them Aug 12.

1. **✅ DONE — ErsatzTV admin has zero authentication.** Real risk was
   lower than first assessed (Tailscale-only access, not public
   internet) but still worth defense-in-depth. Nginx `auth_basic` added
   in front of the ErsatzTV proxy location on the VPS.

2. **✅ DONE — No automated monitoring/alerting.** Every real bug so far
   was caught by a human noticing something felt off. Built and
   logic-tested `health_check.sh`: checks the stream actually returns a
   valid HLS manifest (not just "is nginx up"), disk space, and whether
   the NFO cron log is still fresh (proof the automation is alive).
   Pings healthchecks.io on success; healthchecks.io alerts
   automatically if the VPS ever stops checking in. Needs: real
   healthchecks.io account + UUID, upload, cron entry.

3. **Open — No staging environment for the website itself.** Channel 3
   already serves this role for ErsatzTV content/schedule changes — the
   real gap is narrower than it first sounds: `index.html` and config
   files have only one live target, no safe place to test a change
   before it hits the real domain. Real fix: a staging subdomain or path
   pointing at a separate copy of the site files.

4. **Open — No automated tests.** Not "test everything" — the real
   value is specifically covering logic that's already caused hard-to-find
   bugs: the EPG timestamp matching (the whole Guide saga), the countdown
   timezone math (verified once by hand, no ongoing protection against
   silent regression), and the NFO generator's edge cases (already
   manually tested, never locked in as automatic checks). Real, ongoing
   maintenance cost, not a one-time task — worth deciding deliberately
   before starting, not just because "tests are best practice."


## Additional real gaps — high-level list, Aug 12 pass

More items surfaced when pushed past the first pass. Keeping the honest
distinction: these split into two different axes — "protects the
project over time" (invisible to visitors) vs. "affects how the site
actually feels to someone visiting" (visible). Both matter, different
reasons.

**Invisible / operational:**
5. Log rotation — `generate_nfo.log` / `generate_nfo_cron.log` grow
   forever, nothing truncates them. Not hypothetical — will eventually
   become a real disk problem if left alone long enough.
6. OS security patches — 28 updates sitting on the VPS as of Aug 12
   (10 flagged security-specific), no established regular process for
   applying them.
7. Backup restore has never actually been tested end-to-end — the
   system works and has been used for individual file restores, but a
   real "VPS is gone, rebuild from nothing but backups + the manual"
   drill has never been run. Classic gap: backups feel safe until the
   one time they're actually needed.
8. Rate limiting on the voting API — genuinely unverified either way
   whether anything stops vote spam from one source.

**Visible / how the site actually feels to a visitor:**
9. Custom 404 page — currently unknown whether a mistyped URL shows
   real branding or a raw Nginx default error page. Real, classic
   "polished vs. thrown-together" tell.
10. Every Menu link walked through fresh, confirming no dead ends.
11. Console checked for errors on a clean page load — worth being
    clean for anyone technically curious enough to open DevTools.
12. Real mobile device testing, not just emulator — actual touch
    behavior, actual on-device rendering.


## Resolved on review — Aug 12

- **Backup VPS / redundancy** — conscious, accepted risk, already known.
  Not an action item, just documented as a deliberate tradeoff.
- **Age verification** — already exists (welcome screen entry gate).
  Non-issue.
- **Explicit content labeling** — Parental Advisory burned into every
  video's on-screen credits, regardless of individual track content.
  Non-issue, already handled uniformly.
- **SSL certs** — Cloudflare-issued origin certificate, valid until
  2031. Fully explains the long window — Cloudflare origin certs are
  commonly issued with multi-year (up to 15-year) validity by design,
  a genuinely different and normal mechanism from Let's Encrypt's
  short-lived auto-renewing certs. Resolved, nothing unusual.

## Still open, separate from the cert question above

13. **Domain registration auto-renewal** — different system than the
    SSL cert, can fail independently (expired card on file with the
    registrar being the classic real failure mode). Not yet confirmed
    either way.


## Resolved — account security, Aug 12

- **2FA on Cloudflare, VPS provider (OVH), and GitHub** — confirmed
  already enabled on all three. Non-issue.
- **OVH additionally sends a real-time email on every dashboard login**
  — an extra, genuine layer beyond 2FA alone; would catch unauthorized
  access even if 2FA were somehow bypassed. Worth knowing whether
  Cloudflare/GitHub have an equivalent login-notification setting too,
  just for parity — not urgent, both already have 2FA as the real gate.

## Still open — new items, Aug 12

14. **Cloudflare Worker/D1 free-tier usage limits** — real, not
    hypothetical given Sept 1. Unknown whether there's a request/storage
    ceiling the voting feature could hit under real traffic, and what
    actually happens if it does (silent failure vs. clear error).

15. **Formal DMCA agent registration** (US Copyright Office) — genuinely
    different from having a takedown policy page. Provides stronger
    legal safe-harbor protection than a good-faith policy alone.
    Unknown whether this applies to the current setup or has been done.

16. **Personal liability / business structure** — currently unknown
    whether there's any legal separation between the founder personally
    and the project (e.g. sole proprietorship vs. something else). Real
    money and real copyright exposure now flow through this. Worth being
    a conscious, known state either way, not an unexamined one.


## Resolved — voting system data/privacy, Aug 12

- **What the voting system stores**: anonymous, no raw IP retained per
  the founder's description — enforced via a per-browser unique ID that
  resets roughly every 24 hours, giving a real one-vote-per-24h limit
  under normal use.
- **Worth being aware of, not urgent**: this is a soft, honest-use
  deterrent, not a hard technical barrier — clearing cookies, an
  incognito window, or a different browser would trivially reset the ID
  and allow another vote immediately. Not likely to matter at current
  real scale, but worth knowing the actual mechanism's real limits
  rather than assuming it's airtight, especially since Community Top 10
  already feeds into real, visible programming.
- **Still worth a quick check sometime**: confirm the Privacy Policy's
  actual wording accurately matches this real mechanism.


## Resolved — financials.pdf content review, Aug 12

Actually checked, not assumed. Confirmed clean — only shows the real
$18 VPS charge for July. No accidental salary figures or other
sensitive detail slipped through from the earlier HTML-side scrubbing
work. This was the single item on the whole review list worth calling
a genuine real risk if left unchecked; now resolved.


---

# Remaining Open Items — Ordered by Actual Ease (Aug 12 pass)

**"Done" means: done identifying and closing every gap known right
now — not a guarantee no more exist. New ones will surface over time;
that's expected, not a failure of this review.**

## Tier 1 — Minutes, single action, no real decision needed

1. **Domain registration auto-renewal** — log into the registrar,
   confirm the setting and that a valid card is on file.
2. **Walk every Menu link fresh** on the live site — confirm nothing's
   dead.
3. **Check DevTools console** on a clean page load — confirm no errors.
4. **Apply the pending OS security patches** — `sudo apt update &&
   sudo apt upgrade` on the VPS.
5. **Trace the mystery CSP header** — check Cloudflare's Web Analytics
   settings for a related option (likely bundled with the beacon script
   found earlier).

## Tier 2 — One real action, maybe an account/signup involved

6. **Deploy the health-check script** — real healthchecks.io signup,
   drop in the real UUID, upload, add the cron entry. (Script itself is
   already built and logic-tested — this is just wiring it up live.)
7. **Report the 2 confirmed ErsatzTV bugs** to their community forum —
   writing, not building.
8. **Check Cloudflare Worker/D1 free-tier limits** — a documentation/
   dashboard look, know the real ceiling before Sept 1 traffic tests it.
9. **Confirm Privacy Policy wording matches the real voting mechanism**
   — a read-through and edit if needed.

## Tier 3 — Bounded, single well-defined build

10. **Custom 404 page** — genuinely quick to build, matching branding.
11. **Set up log rotation** for `generate_nfo.log` / `generate_nfo_cron.log`
    — standard Linux tooling (`logrotate`), well-established pattern.
12. **Real mobile device test pass** — an actual phone, clicking
    through for real, not an emulator.

## Tier 4 — Needs a deliberate plan, more moving parts

13. **Test the backup restore end-to-end**, for real — needs a safe,
    deliberate testing approach so the test itself can't cause harm.
14. **Formal DMCA agent registration** (US Copyright Office) — not
    technically hard, but a real external administrative step (a form,
    a small fee) — worth deciding whether it applies here first.
15. **Set up a staging environment** for the website (subdomain/path +
    server config) — real setup, then an ongoing habit to actually use it.

## Tier 5 — Real, substantial, multi-step projects

16. **Build the New Artists block** in ErsatzTV (workflow doc is ready
    to follow, this is real content/schedule work).
17. **Automated tests** for EPG matching, countdown math, NFO edge
    cases — real, ongoing maintenance commitment, not one-time.
18. **Whole-infrastructure backup automation** — three genuinely
    separate jobs (Nginx/ErsatzTV config, music library via rclone,
    Cloudflare exports).
19. **Monthly Top 10 / New Artists rotation automation** — design's
    done, real scripting + the text-matching risk still needs careful
    handling.

## Tier 6 — Needs real outside expertise, not really "ease"-rankable

20. **Personal liability / business structure** — the one item on this
    whole list most likely to genuinely need professional advice rather
    than DIY research. Worth flagging honestly as the hardest, not
    because it's complex to research, but because getting it wrong has
    real consequences a web search can't fully protect against.

