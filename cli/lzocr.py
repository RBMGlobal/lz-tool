"""
Read coordinates off a photo or screenshot of a UAV ground-station screen.

Mirrors the web app. Text lines are found by shape - see osdfind - then the
picture is straightened, each line is cut out, blown up and read on its own at
several scales, and every reading is pooled. A reading that drops a decimal
point ("54491") cannot parse as a coordinate (seconds may not run into more
digits), so it falls away and a clean reading from another scale carries the
fix. TGT is preferred over ACFT.

Two things about the JOUAV OSD do the heavy lifting:

* It is always two stacked lines, aircraft above, target below. When the label
  itself cannot be read - the Chinese build writes them as CJK, which an
  English model returns as noise - the lower of the two lines is still the
  target. Without that rule a Chinese screen leaves both lines unlabelled,
  the vote ties, and the tool can hand back the AIRCRAFT's position as the
  landing point. That is the one error that matters here, so position is used
  as evidence and the reading says so.
* The aircraft's own position is never offered as the answer, however many
  passes agree on it.

Needs the Tesseract binary and `pytesseract`:
    brew install tesseract      # or: apt install tesseract-ocr
    pip install pytesseract
Without them, `read_image` raises RuntimeError with that message.
"""
from __future__ import annotations
import re
from PIL import Image, ImageOps

import lzgeo as G

TGT_RE = re.compile(r"\b(TGT|TARGET|TAR|OBJ|OBJECTIVE|POI|MARK)\b|\u76ee\u6807", re.I)
ACFT_RE = re.compile(r"\b(ACFT|AIRCRAFT|A/C|UAV|UAS|OWNSHIP|HOME|GCS|PLANE)\b|\u672c\u673a",
                     re.I)          # CJK: target position / own-aircraft position


def _engine():
    """Tesseract, plus the finder - imported here, not at the top, so that a
    machine without numpy/scipy can still run everything else in the tool."""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
    except Exception as ex:
        raise RuntimeError("OCR needs the Tesseract binary and pytesseract "
                           "(brew install tesseract / apt install tesseract-ocr; "
                           "pip install pytesseract)") from ex
    try:
        import osdfind
    except Exception as ex:
        raise RuntimeError("reading a screen photo needs numpy and scipy "
                           "(pip install numpy scipy)") from ex
    return pytesseract, osdfind


def bands(img: Image.Image):
    """(top, bottom) of dark strips carrying light pixels — the OSD banners."""
    g = img.convert("L")
    W, H = g.size
    sc = min(1.0, 1600 / max(W, H))
    t = g.resize((max(1, int(W * sc)), max(1, int(H * sc))))
    px = t.load()
    tw, th = t.size
    rows = [sum(px[x, y] for x in range(0, tw, 2)) / len(range(0, tw, 2)) for y in range(th)]
    out, y = [], 0
    while y < th:
        if rows[y] < 95:
            y0 = y
            while y < th and rows[y] < 115:
                y += 1
            if y - y0 >= max(6, th * 0.01):
                bright = n = 0
                for yy in range(y0, y, 2):
                    for x in range(0, tw, 2):
                        n += 1
                        if px[x, yy] > 170:
                            bright += 1
                if n and bright / n > 0.004:
                    out.append((y0 / sc, y / sc))
        else:
            y += 1
    return out


_DMSP = r"(\d{1,3}\s*[°º]\s*\d{1,2}\s*['′]\s*)"


def fix_text(t: str) -> str:
    """What OCR does to a coordinate line, undone. Every rule was seen on a real
    screen photo. A dropped decimal point ("54491") is the dangerous one: it still
    parses as 54" and lands 15 m out, so it is repaired, not left to the parser.
    Same rules, same order as ocrFix() in index.html."""
    t = G.normalise(t)
    # letter-for-digit confusions, but only with a digit on each side: the OSD
    # never puts a lone letter inside a number, so this is safe where a blanket
    # substitution would not be. Each was seen on a real screen photo.
    t = re.sub(r"(?<=\d)[oOQ](?=\d)", "0", t)
    t = re.sub(r"(?<=\d)[TIl](?=\d)", "1", t)                                      # 29.9T9
    t = re.sub(r"(?<=\d)[B](?=\d)", "8", t)                                        # 38.8B0
    t = re.sub(r"(?<=\d)[S](?=\d)", "5", t)
    t = re.sub(r"(\b\d{1,3})[\"\u2033](?=\d{1,2}\s*['\u2032])", r"\1°", t)                # 5"19'20.218
    t = re.sub(r"([°º]\s*\d{1,2})[°º](?=\d{2})", r"\1'", t)                        # 7° 4°22.588"
    t = re.sub(r"(['\u2032]\s*\d{1,2})['\u2032](?=\d{2,3})", r"\1.", t)                # 33'19'422"
    t = re.sub(r"(\d{1,2}),(\d{1,3})(?=\s*[\"\u2033]?\s*[NSEW](?![A-Za-z]))",
               r"\1.\2", t)                                                     # 22,555"N
    t = re.sub(_DMSP + r"(\d{2})[ ]?(\d{3})(?=\s*[\"″°º]|\s*[NSEW](?![A-Za-z]))",
               r"\1\2.\3", t)                                                     # 54491"  22 588"
    t = re.sub(r"([°º]\s*)(\d{1,2})(\d{2})[.,](\d{3})(?=\s*[\"″°º]|\s*[NSEW](?![A-Za-z]))",
               r"\1\2'\3.\4", t)                                                  # 422,588"
    # The trailing whitespace is looked past, not consumed: written hemisphere-
    # first ("N 12°16'59.93\" E 7°41'29.61\""), the letter after the seconds is
    # the NEXT half's, and eating the space glued the two halves together and
    # lost the whole line.
    t = re.sub(_DMSP + r"(\d{1,2}(?:[.,]\d+)?)\s*[°º*'′\"″´`]{1,2}(?=\s*[NSEW](?![A-Za-z]))",
               r'\1\2"', t)                                                        # 17.850°N  54.491 'E
    t = re.sub(r"(\d)\s*(?:''|´´|``)\s*(?=[NSEW]\b)", r'\1"', t)
    t = re.sub(r'(\d{1,3})\s*[°º]\s*(\d{2})(\d{2})(\d{3})\s*["″]?\s*(?=[NSEW](?![A-Za-z]))',
               '\\1°\\2\'\\3.\\4"', t)                              # 5725533"N -> 57'25.533"
    t = re.sub(r"(?<=\d)[oO](?=\d)", "0", t)
    t = re.sub(r"(?<=[NSEW]|\d)\s*[|]\s*", " ", t)
    # Whatever OCR hallucinates in the gap between the latitude and the
    # longitude - a stray bracket, an underscore, a full stop - splits the pair
    # and the whole line is lost, even though both halves read perfectly. This
    # is the single most common way a good reading is thrown away, so the gap
    # after a hemisphere letter is scrubbed back to one space.
    t = re.sub(r"(?<=[NSEW])[\s_.,;:*=+~^<>\u00ab\u00bb\u2039\u203a\u00b7\u2022-]{1,8}(?=\d)",
               " ", t)
    return t


PASSES = (
    # (target text height in px, tesseract config)
    (34, "--psm 7 -c preserve_interword_spaces=1"),
    (52, "--psm 7 -c preserve_interword_spaces=1"),
    (80, "--psm 7 -c preserve_interword_spaces=1"),
)
BLOCK_CFG = "--psm 6 -c preserve_interword_spaces=1"
MAX_BLOCKS = 3


def _labels(per_line):
    """Work out which line is the target's.

    `per_line` is {line index: (explicit label, y)} for the lines of one block
    that yielded a coordinate. An explicit label is believed. Beyond that, the
    JOUAV OSD is a fixed two-line block - aircraft first, target second - so
    when a block has exactly two coordinate-bearing lines the missing label can
    be filled in from the order. Inferred labels are marked with a trailing "?"
    so the reading can say how it knows.
    """
    out = {i: lab for i, (lab, _) in per_line.items()}
    order = sorted(per_line, key=lambda i: per_line[i][1])
    if len(order) != 2:
        return out
    a, b = order
    if out[a] == "" and out[b] == "":
        out[a], out[b] = "ACFT?", "TGT?"
    elif out[a] == "ACFT" and out[b] == "":
        out[b] = "TGT?"
    elif out[b] == "TGT" and out[a] == "":
        out[a] = "ACFT?"
    elif out[a] == "TGT" and out[b] == "":
        out[b] = "ACFT?"                      # labels the other way up
    elif out[b] == "ACFT" and out[a] == "":
        out[a] = "TGT?"
    return out


def _infer(reads):
    """Fill in the labels a block knows by position but could not read."""
    byblock = {}
    for r in reads:
        if r.bi is None or r.li is None:
            continue
        cur = byblock.setdefault(r.bi, {})
        lab, y = cur.get(r.li, ("", None))
        cur[r.li] = (r.label or lab, r.li if y is None else y)
    inferred = {bi: _labels(pl) for bi, pl in byblock.items()}
    for r in reads:
        if not r.label and r.bi in inferred:
            r.label = inferred[r.bi].get(r.li, "")


def read_image(path: str, log=None):
    """
    Coordinates read off the screen, best first. Every OCR pass votes: readings
    within ~100 m of each other form a cluster, the biggest cluster wins, a
    labelled target beats one placed by position, which beats an unlabelled
    reading, and the aircraft's own position is listed but never first. Each
    Fix carries .label ("TGT"/"TGT?"/"ACFT"/"ACFT?"/""), .votes and .runs.
    """
    tess, F = _engine()
    src = ImageOps.exif_transpose(Image.open(path))
    if src.mode != "RGB":
        src = src.convert("RGB")
    img, blks, ang = F.find(src)
    if log:
        log(f"  {len(blks)} text block(s) found"
            + (f", picture straightened {ang:+.1f}\u00b0" if ang else ""))

    reads, runs = [], 0

    def harvest(text, bi, li):
        nonlocal runs
        runs += 1
        got = []
        for line in fix_text(text).splitlines():
            lab = ("TGT" if TGT_RE.search(line) else
                   "ACFT" if ACFT_RE.search(line) else "")
            for f in G.find_all(line):
                f.label, f.note, f.bi, f.li = lab, line.strip(), bi, li
                reads.append(f)
                got.append(f)
        return got

    def confident():
        """A target position two independent passes agree on. Enough to stop:
        the OSD is block one on every screen we have seen, and reading the rest
        of the picture costs a crew time it may not have."""
        seen = {}
        for r in reads:
            if r.label.startswith("TGT"):
                k = (round(r.lat, 4), round(r.lon, 4))
                seen[k] = seen.get(k, 0) + 1
        return any(v >= 2 for v in seen.values())

    for bi, b in enumerate(blks[:MAX_BLOCKS]):
        for li, ln in enumerate(b["lines"][:4]):
            for th, cfg in PASSES:
                c = F.crop(img, ln["box"], target_h=th).convert("L")
                if c.width < 30 or c.width > 12000:
                    continue
                if log:
                    log(f"  reading block {bi+1} line {li+1} at {th}px")
                harvest(tess.image_to_string(c, config=cfg), bi, li)
        if len(b["lines"]) > 1:
            # scaled per line, not per block: at a fixed 40 px a two-line
            # block gives Tesseract 20 px of text and it starts inventing digits
            c = F.crop(img, b["box"], target_h=40 * len(b["lines"])).convert("L")
            if 30 < c.width < 12000:
                harvest(tess.image_to_string(c, config=BLOCK_CFG), bi, None)
        _infer(reads)
        if confident():
            break
    if not any(r.label for r in reads):
        s = min(1.0, 2400 / max(img.size))
        im = img.convert("L").resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
        if log:
            log("  reading the whole frame")
        harvest(tess.image_to_string(im, config="--psm 11"), None, None)

    _infer(reads)

    # One cluster per position, not per position-and-label: a reading that
    # lost its label still corroborates the digits, and pooling the votes is
    # what separates a coordinate three passes agree on from a one-off. The
    # label is then decided by majority of the readings that carried one, so a
    # single misread label cannot flip a position on its own.
    clusters = []
    for r in reads:
        for c in clusters:
            if abs(c.lat - r.lat) < 0.001 and abs(c.lon - r.lon) < 0.001:
                c.votes += 1
                c.tally[r.label] = c.tally.get(r.label, 0) + 1
                break
        else:
            r.votes, r.runs = 1, runs
            r.tally = {r.label: 1}
            clusters.append(r)
    for c in clusters:
        read = {k: v for k, v in c.tally.items() if k and not k.endswith("?")}
        placed = {k: v for k, v in c.tally.items() if k.endswith("?")}
        c.label = (max(read, key=read.get) if read else
                   max(placed, key=placed.get) if placed else "")

    def rank(c):
        """Class first, then how many passes agree, and only then whether the
        label was read or placed. Votes must beat a read label: a single pass
        that misread one digit but did catch the word TGT would otherwise
        outrank three passes that agree on the digits and knew the line only by
        its position - which is exactly how a 7 became a 1 in testing."""
        cls = 3 if c.label.startswith("TGT") else 0 if c.label.startswith("ACFT") else 2
        return (cls, c.votes, 0 if c.label.endswith("?") else 1)
    clusters.sort(key=rank, reverse=True)
    for c in clusters:
        c.runs = runs
        c.source = "screen photo (OCR)"
        line, lab = c.note, c.label
        if lab.startswith("ACFT"):
            why = "the AIRCRAFT's position, not the target"
        elif lab == "TGT?":
            why = ("the target line by its position in the block - the label itself "
                   f"did not read; {c.votes} of {runs} passes agree")
        else:
            why = (f"read from a photo by OCR, {c.votes} of {runs} passes agree")
        c.note = why + " - verify the digits against the screen before you fly" \
                 + f"  [{line[:60]}]"
    return clusters
