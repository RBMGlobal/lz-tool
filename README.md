# LZ Brief

Landing-point imagery for helicopter crews. Turns a location in whatever format it
arrived in into a wide-area-to-close-up series they can read in the cockpit, sent
over WhatsApp. One self-contained HTML file — no build step, no dependencies, no
server logic. Nothing anyone enters leaves their own device.

© 2026 RBM Global. All rights reserved. Proprietary — see `NOTICES.md`.

## Files

| File | What it is |
|---|---|
| `index.html` | The tool. Single source of truth — everything is inside it |
| `sw.js` | Offline worker, so the page opens with no signal |
| `manifest.webmanifest` | Lets the page install to a phone or tablet home screen |
| `icon-192.png`, `icon-512.png`, `apple-touch-icon.png` | Home-screen icons |
| `vendor/` | The on-device OCR engine behind *Read a screen photo* (Tesseract.js, ~7 MB) — see NOTICES.md |
| `cli/` | Python version — batch runs, GPX/TAK files, PDF output. `tests_parse.py` is the parser + OCR-repair regression sweep; run it after any parser change |
| `samples/` | Example output, so you can see what a crew receives |
| `NOTICES.md` | Imagery sources, attribution and the licensing position |

## The problem

A crew is given a landing spot by the team, usually as a zoomed-in screenshot with
no surrounding context. Under time pressure — CASEVAC, casualty recovery — that is
not enough to find it. This produces the chain of views that is missing, plus the
information needed to judge how much to trust the picture.

## What comes out

**A sequence of images, widest first, one per step.** In WhatsApp they arrive as an
album — the crew taps the first and swipes, and the swipe *is* the drill-down.

| # | | Across |
|---|---|---|
| 1 | AREA | 30 km |
| 2 | DISTRICT | 6 km |
| 3 | APPROACH | 1.5 km |
| 4 | SURROUNDS | 500 m |
| 5 | THE POINT | 150 m, with 25 m and 50 m rings |
| 6 | Detail card | grid in four formats, elevation, slope, imagery age, season note, and the key to the sequence |
| 7 | Other looks | the same spot from other captures and from Mapbox |
| 8 | Latest pass | the most recent clear Sentinel-2 image, dated, 6 km across — ground state now |

Every step carries a progress bar, the step name, the span, the grid, a scale bar and
the imagery provenance — **all of it in bars above and below the picture, never on it.**
On the imagery itself there is only the landing-point reticle, N/E/S/W at the edges,
and four thin yellow corner brackets marking exactly what the next view covers.

A **PDF** of the whole set comes out of the CLI. WhatsApp compresses photos but not
documents, so that is the route to full detail when there is time.

## The two things that decide whether the picture can be trusted

**Imagery age is stamped on every panel** from Esri's own metadata — exact capture
date, ground resolution and satellite, not "about a year old":
`12/20/2025 · 0.31 m/px · WV03`.

**Season mismatch is called out in plain words.** Age in months is the wrong question
in the tropics; season is the right one:

> Imagery is DRY season, today is WET — expect thicker vegetation, softer ground and
> standing water.

## Orientation

Every image panel carries N / E / S / W on its edges, a north arrow and a scale bar,
and each preview in the app is framed with the same four letters. **All views are
north-up**, on every panel and every image.

## Picking a point on the map

**Pick on map** opens a **satellite hybrid** map — the same imagery with roads and
place names over it, so you can navigate to the right area rather than hunting through
bare terrain. The **A** button turns the labels off when they sit over the very spot
you are picking. Drag to pan, pinch or +/− to zoom.

**Click or tap the map to choose a point.** Nothing is drawn over the imagery — the
mouse cursor is the crosshair, and the map does not jump when you click. The button
underneath then reads the grid you picked (`Use 32P LR 23669 03943`), which is the
confirmation, so no marker sits over the ground you are trying to judge.

**Live coordinates sit in the top-right corner** — MGRS, decimal degrees and
degrees-decimal-minutes. They follow the mouse pointer on a laptop (panel reads
CURSOR) and show what you picked after a tap (reads SELECTED). Scale bar and true
ground resolution are shown, so you can see the detail you are actually working with.

It opens centred on whatever is already parsed, so it also serves to nudge a grid that
landed slightly off — read the coordinates out of the message, drag the crosshair onto
the actual clearing, build from there.

## Reading a drone screen photo

**Read a screen photo** takes a photo or screenshot of a UAV ground-station display —
the client's JOUAV GCS is the case it was built on — and reads the coordinates straight
off the on-screen data strip. Choose a photo (or take one), and a few seconds later the
target is parsed, gridded and previewed exactly as if it had been typed in. On a phone
this also accepts an image shared into the tool.

    ACFT: 11°55'31.051"N   7° 4'22.588"E   HMSL: 1650m
    TGT:  11°56'17.850"N   7° 3'54.491"E   HMSL: 514m   →  TGT is what gets selected

**How it reads.** The first version looked for a dark horizontal band and read that.
Against ten photos of the client's GCS taken at different angles, resolutions and
formats, it failed on most of them: in a real photo the screen is a bright rectangle
inside a larger frame and the OSD is a *translucent* strip over daylight imagery, so its
row average is nowhere near dark and the band is never found. What replaced it looks for
the text itself.

1. **Character-shaped blobs.** The picture is thresholded against a local background —
   both polarities, so light-on-dark and dark-on-light panels both work — and every
   connected blob is measured. A character is small, no more than about three times as
   wide as it is tall, and partly filled.
2. **Blobs chained into lines.** Blobs of matching height sitting on a common baseline,
   five or more in a row, are a line of text. The baseline is tracked as a *slope*: a
   hand-held photo is a couple of degrees off level, and over the width of an OSD line
   that is more drift than the text is tall. Vegetation makes blobs too, but it never
   makes a row of five with matching heights and even spacing.
3. **Fragments rejoined.** One OSD line is three columns with wide gaps between them, so
   the latitude, the longitude and the altitude come out as separate runs and no run
   carries a whole coordinate. Runs sharing a baseline and a text height are rejoined —
   after the shape test, not by loosening it, which would let scenery in.
4. **The picture straightened.** The tilt is measured off the best line by shearing its
   row profile until it is most sharply peaked, and if it is worth correcting the whole
   picture is rotated and detection run again. On the lowest-resolution photo in the set
   this was the difference between nothing and a clean read.
5. **Each line read on its own, three times.** Every line is cropped and blown up to 34,
   52 and 80 px of text height, then the whole block is read again as a unit. The
   recogniser is fussy about glyph size — on one photo the decimal point in the seconds
   vanished at one scale and came back at another — so no single scale decides anything.

**Which line is the target.** Labels are read where they can be read. Where they cannot,
position decides: the JOUAV OSD is always two stacked lines, aircraft above, target
below. This matters most on the Chinese build, which writes the labels as 本机位置 and
目标位置 — an English model returns those as noise, so both lines come back unlabelled,
the vote ties, and without the rule the tool could hand back the **aircraft's** position
as the landing point. A position placed this way says so: *the target line by its
position in the block — the label itself did not read*.

**Check the digits.** OCR reads a photo of a screen; it can misread. Five things make it
safe enough to use in a hurry.

- **The known mangles are repaired before parsing** — every rule below was seen on a real
  photo of this GCS: a second `°` where the minute mark is (`7° 4°22.588"`), a `"` where
  the degree mark is (`5"19'20.218`), a dropped, space-read or comma-read decimal point
  in the seconds (`54491"`, `22 588"`, `22,555"`), both separators lost at once on a
  low-resolution shot (`5725533"`), `°` or `'` where the closing `"` should be, and the
  letter-for-digit confusions `O`→0, `I`/`T`/`l`→1, `B`→8, `S`→5 *only where a digit sits
  on each side*. The rule that recovers the most readings is the last one: OCR often
  invents a character in the gap between the latitude and the longitude — a bracket, an
  underscore, a full stop — and that alone splits the pair and throws away a line where
  both halves read perfectly.
- **Anything still mangled cannot parse at all** (seconds may not run into further
  digits), so it drops out rather than becoming a wrong fix.
- **The passes vote.** Readings within 100 m of each other are one candidate whatever
  label they carried, the one most passes agree on wins, and the badge says so — *4 of 7
  passes agree*. Votes beat a read label on purpose: a single pass that misread a digit
  but did catch the word `TGT` must not outrank three passes that agree on the digits.
  In testing, that ordering is what stopped a `7` read as a `1` — 650 km out — from being
  offered as the answer.
- **The text it read goes into the box** above the result with an orange **verify against
  the screen** badge, and the satellite preview of the parsed point is the last check: if
  the screen shows a compound and the preview shows open bush, don't fly it.
- **The aircraft's own position is never selected for you.** It is listed when read; if
  only the ACFT line is legible the tool says so and asks for a better photo rather than
  offering the wrong point.

Scored against the ten-photo set: **nine of the nine readable photos return the correct
target as the top answer**, in 2–5 s each. The tenth is cropped so that the target's
latitude is off the edge of the picture; it returns nothing, which is the right answer.
Re-run the scoring after any change to the detector, the repairs or the ranking.

RAW (`.DNG`), video (`.MOV`) and — on Android — `.HEIC` cannot be opened by a browser at
all. Each now says which it is and what to send instead, rather than "not an image".

It is all on-device (Tesseract OCR compiled to WebAssembly, self-hosted alongside the
page, ~7 MB fetched once and kept offline) — the photo is never uploaded.

## Location formats it reads

Decimal degrees (`12.283314, 7.691558`, `12.283314N 7.691558E`, `N 12.283314 E 7.691558`) ·
labelled (`Lat 12.283314 Long 7.691558`, `LAT: .. LON: ..`, either order) ·
degrees-decimal-minutes (`N 09 04.590 E 007 23.916`) · degrees and whole minutes
(`12°17'N 7°41'E`, `N12 17 E007 41`) · DMS (`12°16'59.93"N`, `12 16 59.93 N`,
`12d16m59.93sN`) · MGRS at any precision (`32P LR 23998 03697`, `32P LR 240 037`) ·
NMEA (`0904.590N 00723.916E`) · Google and Apple Maps links · `geo:` links · GPX
(waypoints, routes, tracks) · KML/KMZ · CoT XML · **TAK data packages** (.zip).

A bare pair of numbers is only read as a coordinate when **both carry decimals** —
`14 30`, `31 08 2026` and `14.30, 12 pax` are a time, a date and a headcount, and a
whole-degree fix is no use for a landing point anyway. Minutes or seconds of 60 or
more disqualify a match.

**Text is normalised before anything is matched**, because real messages come from
phones, Word and copy-paste rather than from a form. Smart quotes (`’ ’’ ′ ″`),
non-breaking spaces, the masculine-ordinal `º` in place of `°`, en dashes, longhand
`deg / min / sec`, and a **pipe used as the separator** all parse. That last one is not
hypothetical — it is how field reporting arrives:

    ... rendezvous point coordinate  12° 16' 59.93'' N | 7° 41' 29.61'' E in Matazu LGA

**Paste the whole message.** Coordinates are pulled out of the surrounding prose, and
dates, times and headcounts are not mistaken for a fix — `1230 hours`, `31st August
2026` and `twenty (20)` are all correctly ignored.

**If a message contains more than one grid, you get all of them and pick.** Situation
reports often carry a primary and a secondary location, and silently taking the first is
how you brief the wrong point. A pair that looks like lon,lat is flagged, not silently
flipped. Files with several points work the same way.

## Exporting the waypoint

Three formats, straight from the coordinate — **no imagery needed, so they are
instant**:

| Format | For |
|---|---|
| **GPX** | Garmin, OsmAnd, aviation kit, most anything |
| **KML** | Google Earth, ArcGIS, anything that reads Google's format |
| **TAK data package** (`.zip`) | ATAK / WinTAK — **Import Manager → Local SD** |

**Air Navigation Pro** reads both. GPX is emitted as GPX 1.1 with the `<wpt>` children in
strict schema order and validated against the official topografix XSD, because a strict
importer rejects the file otherwise; `<cmt>` carries the grid on its own, since several
aviation apps show the comment and ignore the longer description. The KML references no
external icon, so it draws with no signal. **Open in AirNav Pro** skips files entirely —
it hands the point straight over as a direct-to via the `airnavpro://` URL scheme.

**Every export is stamped with a date-time group** — `MATAZU_LZ_311430ZAUG26.gpx` — and
the DTG is in the marker name and the first line of its description too, so repeat briefs
for the same point stay apart in the file list and in the app. The imagery filenames and
the detail card carry the same DTG. (Note DTG sorts by day, so files from different months
won't sort chronologically — say the word if you'd rather have an ISO prefix.)

Each carries the grid in MGRS, DDM and DD, plus elevation, slope, imagery date and
the season note as the marker's description, so the waypoint arrives with the same
facts as the brief rather than as a bare pin.

The TAK package is a standard Mission Package — `MANIFEST/manifest.xml` plus one
`<folder>/<folder>.cot`, waypoint CoT type `b-m-p-w`, marked in the same magenta the
imagery uses. It is written from scratch in both versions with no libraries: the web
app builds the zip itself.

**This tool stands alone.** It shares no code, no files and no state with the PED tool
— separate folder, separate page, works with the PED tool absent. The TAK layout
matches what PED writes for one reason only: markers from either tool then import the
same way, and packages from both can sit side by side without colliding (every marker
gets its own UUID). Neither needs the other.

On the CLI, `--waypoint-only` skips the imagery entirely and just writes the three
files — a couple of seconds:

    python3 lzpack.py "12° 16' 59.93'' N | 7° 41' 29.61'' E" -n "MATAZU LZ" --waypoint-only

`--no-export` leaves them out of a full run.

## Mapbox as a second look

Mapbox satellite is wired in as a comparison source. It does **not** publish a capture
date, so it never carries one — its footer says *capture date not published* rather than
borrowing Esri's. It is still worth having: a different provider flying on a different
date is another read on what the ground actually looks like, which is the whole point of
the comparison sheet.

Esri stays the primary imagery because it is the one that tells you when it was taken.
`--base mapbox` on the CLI switches that if you ever want it.

The Mapbox token sits at the top of `index.html` as `MAPBOX_TOKEN`. It is a public
(`pk.`) token, which is designed to ship in client-side code — but **restrict it to your
domain in the Mapbox account** (Account → Tokens → URL restrictions) before this goes on
a public GitHub Pages site, or anyone can spend your quota.

## The latest pass — Sentinel-2

Everything above is either years old (Esri, dated) or undated (Mapbox). The eighth image
is neither: **the most recent clear Sentinel-2 pass over the point**, from ESA's Copernicus
programme — free and open for commercial use, a new pass every 2–5 days, every scene dated,
10 m per pixel. It is drawn at the DISTRICT scale (6 km across) and labelled plainly:

    LATEST PASS · 6 km across · Sentinel-2 · 24 Aug 2026 · 8 days old · 10 m/px · cloud ~8%
    RECENT PASS — GROUND STATE, NOT DETAIL

At 10 m the landing point is one pixel; this image is for **what the ground is doing now**
— standing water, flooded fields, burnt scrub, how green the bush is, whether the dry
riverbed on the Esri capture is currently a river. It turns the season note from a rule
into a photograph. Put it next to the DISTRICT view and the difference between a
dry-season 2021 capture and this month is obvious.

How it chooses: scenes over the point from the last 60 days come from the public Earth
Search catalogue, newest first. Each candidate is judged for cloud *over the 6 km window*
using its coarsest overview (a few KB), and the newest one under 25 % cloud wins; failing
that, the least cloudy of the first six, unless even that is over 70 % — then the brief
says *No usable Sentinel-2 pass in the last 60 days (cloud)* rather than sending a picture
of cloud. Only the chosen scene has full-resolution tiles pulled, straight out of the
Cloud-Optimised GeoTIFF with range requests: typically 2–8 MB depending on where the
window falls on the imagery's internal tile grid. Always at full 10 m — the level is
chosen by resolution, never by download size. No key, no library — the
TIFF reader, the deflate + predictor decode and the UTM→Mercator warp are all inlined.

It is a checkbox above **Build the brief**, on by default and remembered per device.
Untick it on a bad connection. In the wet season expect "best pass is two weeks old, 30 %
cloud" — that is still true information. In the dry season it will be days old and clear.

Attribution, carried in the page footer and every LATEST PASS panel: *Contains modified
Copernicus Sentinel data [year]*.

## Sending it

**Images and text go as two separate sends.** WhatsApp drops attachments when they
arrive mixed with a message, so the share button hands over image files only and the
text has its own button. Each image also has a **Send just this one** button, and if
the share sheet refuses the whole set the tool falls back to sending them one at a time
and says so.

**Send as HD / original quality.** Standard quality resizes to about 1600 px on the
long edge; the ladder survives that, the close-up does not.

## Published

**Live: https://rbmglobal.co.uk/lz-tool/**

GitHub Pages from `RBMGlobal/lz-tool`, Settings → Pages → Source: Deploy from a branch
→ `main` / root — the same arrangement as the PED tool, under the apex domain held by
`RBMGlobal.github.io`.

> The Mapbox token in `index.html` is public by design (`pk.`), but **restrict it to
> rbmglobal.co.uk** in Account → Tokens → URL restrictions, or anyone reading the repo
> can spend the quota.

## Using it on a tablet

Open the URL, then **Add to Home Screen** (Safari: share button; Chrome: menu → Add to
Home screen). It launches like an app.

Offline you get the tool, the parser and the grid conversions — the imagery itself
always needs signal, and is deliberately never cached. Stale imagery presented as
current is the exact failure this tool exists to prevent.

`index.html?q=<location>` pre-fills and parses immediately, which makes an iOS Shortcut
possible: select the grid in WhatsApp → Share → Shortcut → brief already loaded.

## The command-line version

    cd cli && pip install -r requirements.txt
    python3 lzpack.py "9.0765, 7.3986" --name "CASEVAC ALPHA"
    python3 lzpack.py mission.gpx --list
    python3 lzpack.py datapackage.zip --pick 2

Flags: `-o DIR`, `--no-dates`, `--no-pdf`, `--no-terrain`, `--lonlat`, `--esri-key`,
`--mapbox-token`. Typical run 15–20 seconds.

## Updating

Replace `index.html` and commit. Everyone gets the new version the next time they open
the page with signal — the offline worker serves the cached copy only when the network
is unreachable. Bump `CACHE` in `sw.js` if a stale shell ever needs forcing out.

## Changes

**6 Sep 2026 (late)** — one repair rule was destroying hemisphere-first lines.

- **Fixed: a coordinate written hemisphere-first was thrown away by the repairs.**
  `N 12°16'59.93" E 7°41'29.61"` parses correctly as it stands, but the rule that puts
  a proper closing `"` on the seconds (`17.850°N` → `17.850"N`) was also eating the
  space after it. Written hemisphere-first the letter following the seconds is the
  *next* half's — so `59.93" E 7°…` became `59.93"E 7°…`, the two halves ran together,
  the DMS pattern lost its separator and the whole line came back as nothing. The rule
  now looks past that whitespace instead of consuming it; every case it was written for
  still repairs. Found while checking whether a repair added to the PED tool was needed
  here — it was not, but this was.
- `cli/tests_parse.py` — 24 cases now: hemisphere-first with and without spaces around
  the letters, and the two closing-mark repairs the fix had to leave working.
- `sw.js` → `lz-brief-v10`.

**6 Sep 2026 (evening)** — screen-photo reading rebuilt against a ten-photo set.
Rob reported it "didn't work a lot of the time" and supplied ten photos of the client's
GCS at different angles, resolutions and formats. It read three of them. It now reads
**nine of the nine that are readable**, in 2–5 s each; the tenth is cropped so the
target's latitude is off the picture and it correctly returns nothing.

- **The band finder is gone.** Looking for a dark horizontal strip only works when the
  OSD spans the whole picture. In a real photo the screen is a bright rectangle inside a
  larger frame and the OSD is *translucent* over daylight imagery, so its row average is
  never dark. Replaced with character-shaped-blob detection chained into text lines —
  see *Reading a drone screen photo*. A second attempt, scoring rows by bright-stroke
  density, is also recorded there: it drowned in vegetation on two photos.
- **Baselines are tracked as slopes.** A hand-held photo runs a couple of degrees off
  level, which over the width of an OSD line is more drift than the text is tall. With a
  fixed test the line broke in the middle and handed `TGT:` to the row above — so the
  target line came back unlabelled and the aircraft's line came back labelled `TGT`.
- **The picture is straightened before reading.** The tilt is measured off the best text
  line by shearing its row profile until it is most sharply peaked. On the lowest-
  resolution photo in the set this was the difference between nothing and a clean read.
- **Fragments are rejoined.** An OSD line is three widely spaced columns; each came out
  as its own run, so no run carried a whole lat/lon pair and nothing parsed at all.
- **The target is identified by position where the label cannot be read.** The OSD is
  always aircraft above, target below. On the Chinese build (本机位置 / 目标位置) an
  English model returns the labels as noise, both lines come back unlabelled, the vote
  ties — and the tool could hand back the **aircraft's** position as the landing point.
  Positions placed this way say so in the reading.
- **Votes now beat a read label.** A single pass that misread a digit but did catch the
  word `TGT` used to outrank three passes that agreed on the digits. That is how a `7`
  read as a `1` — 650 km out — was briefly the top answer in testing.
- **The block-level pass is scaled per line, not per block.** At a fixed 40 px a two-line
  block gave the recogniser 20 px of text and it started inventing digits.
- **More repairs, all from these photos**: `"` read as the degree mark (`5"19'20.218`),
  comma decimals (`22,555"`), both separators lost at once (`5725533"`), `B`→8 and
  `S`→5 between digits, and — the one that recovers the most readings — scrubbing the
  character OCR invents in the gap between the latitude and the longitude, which alone
  used to throw away a line where both halves read perfectly.
- **Stops early** once two passes agree on a target, so a typical photo is 7 OCR passes
  rather than 26.
- **RAW, video and HEIC now say what they are** and what to send instead, rather than
  "not an image". Eight `.DNG` and one `.MOV` in the supplied folder were part of the
  original complaint.
- **`cli/tests_parse.py`** — the parser and repair sweep is now a file that ships with
  the tool instead of something re-typed each time. 20 cases, every one from something
  that actually broke. Run it after any parser or repair change.
- Detection is identical in the browser and the CLI: both were run over all ten photos
  and agreed on skew angle and text blocks on every one.
- `sw.js` → `lz-brief-v9`. The Tesseract engine and worker stay self-hosted in
  `vendor/` — they were briefly base64-inlined into `index.html` to work around
  GitHub refusing `worker.min.js`, but it accepts the file now and 270 KB of
  base64 on every page load is a poor trade for crews who never touch OCR.

**5 Sep 2026** — latest pass sharpness fix.
- **Fixed: the LATEST PASS image could come out heavily blurred.** The level chooser
  capped the download at two tiles; when the 6 km window straddled a corner of the
  imagery's internal 10.24 km tile grid, both sharp levels needed four tiles, so it
  silently fell back to a 40–80 m overview — a 10–19× upscale. Levels are now chosen
  by resolution only: the panel is always full 10 m, whatever the tile count
  (worst case ≈8 MB instead of ≈3 MB). Sharpness is the point; it is never traded
  for download size again.

**6 Sep 2026** — screen-photo reading hardened.
- OCR repairs for the misreads seen on the client's photo (second `°` as minute mark,
  dropped/space decimal point in the seconds, `°`/`'` for the closing quote) and
  **voting across the four passes** — the fix most passes agree on wins and the badge
  reports the count. ACFT is never auto-selected; an ACFT-only read is refused with a
  retake prompt. Verified on the original 4032 px photo (3 of 4 agree, 6.6 s) and on a
  WhatsApp-compressed 1600 px copy (4 of 4, 4.6 s), in the browser and in the CLI.

**5 Sep 2026 (evening)** — read a drone screen photo.
- **Read a screen photo**: OCR the coordinates off a photo/screenshot of a UAV ground
  station, TGT preferred over ACFT. On-device (Tesseract.js, self-hosted in `vendor/`,
  ~7 MB, cached offline after first fetch). Verified on the client's JOUAV GCS photo:
  `TGT 11°56'17.850"N 7°3'54.491"E` read exactly, in about 6 s. CLI: pass the image
  path (`lzpack.py photo.jpg`); needs `tesseract` + `pytesseract` installed.
- Parser hardening from the same work: a sexagesimal seconds or decimal-minutes group
  may not be followed by another digit, so a mangled reading fails to parse rather than
  parsing wrongly.

**5 Sep 2026 (later)** — reticle, and an imagery-honesty fix.
- **The landing point is now marked with a thin open-centre red reticle** —
  telescopic-sight style, four short arms that stop well short of the centre — in
  place of the magenta dot. Nothing is drawn over the exact point at all; the ground
  under it stays completely clean. Requested from the field.
- **Fixed (CLI): the close-up could render entirely as Esri "map data not yet
  available" filler.** The zoom probe correctly detected where real imagery stops,
  but the published max-zoom figure was allowed to override it upward. The probe is
  now authoritative in both directions. The web app never had this fault.

**1 Sep 2026 (later)** — the latest pass.
- New eighth image: the most recent clear **Sentinel-2** pass over the point, dated, 10 m,
  6 km across, with cloud percentage. Free and open; no key. See *The latest pass* above.
  CLI: on by default, `--no-sentinel` to skip. Web: checkbox, remembered per device.
- Google satellite considered and declined on licensing grounds — see NOTICES.md.

**1 Sep 2026** — review pass after first publish.
- **Fixed: footer scale bar was mislabelled on five of the six image types.** The bar
  was clamped to 21 % of the map width but labelled with a round value that spanned
  33 % — "10 km" drawn at 6.3 km on the AREA view. It is now drawn at the exact length
  its label says. If you have briefs built before this date, the scale bars on them
  are wrong; the grid, rings and MGRS were unaffected.
- Parser: degrees-and-whole-minutes (`12°17'N 7°41'E`), labelled `Lat .. Long ..`,
  hemisphere-first decimals (`N 12.28 E 7.69`) and ASCII `d m s` now read. `N12 17
  E007 41` used to come out as 12°N 17°E — a wrong fix rather than no fix.
- Parser: bare number pairs need decimals on both sides; minutes/seconds must be under
  60. Stops times, dates and headcounts becoming a landing point.
- Roughly half the tile requests per brief (native-resolution cap 2.2× → 1.5×; the
  difference vanishes under JPEG and WhatsApp resizing). Wayback probes go six at a
  time instead of 48 at once. Failed tiles are retried on the next build rather than
  remembered as failed.
- Season rule follows latitude in the tropics: Katsina (12°N) is wet June–September,
  Port Harcourt (4°N) April–October. Previously one May–October rule for both.
- "Other looks" no longer includes the capture already used for the main sequence.
- Sharing one-at-a-time now reports how many actually went.

## What it does not do

- **No obstacle detection.** Wires, masts and single trees are exactly what kills
  helicopters and none of them are reliably visible from above. It supports the recce;
  it does not replace it.
- **No live conditions.** Cloud, smoke, flooding and last week's construction are not in it.
- **Slope is SRTM at 30 m.** Good for "is this a hillside", useless for "is this pad level".
