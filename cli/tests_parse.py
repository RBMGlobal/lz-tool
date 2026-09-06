#!/usr/bin/env python3
"""Regression sweep for the coordinate parser and the OCR text repairs.

Run after ANY change to lzgeo.normalise/find_all or lzocr.fix_text:

    python3 tests_parse.py

Every case here comes from something that actually broke: a field report that
used a pipe as a separator, a screen photo whose decimal point vanished, an OCR
pass that put a bracket between the latitude and the longitude. The negative
cases are the other half of the job - a tool that reads "1230 hours" as a fix
is worse than one that reads nothing.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzgeo as G
import lzocr as OCR

D = lambda d, m, s: d + m / 60 + s / 3600

# (text, expected first fix as (lat, lon) or None, note)
PARSE = [
    ("12.283314, 7.691558", (12.283314, 7.691558), "decimal degrees"),
    ("N 12 16.996 E 007 41.493", (D(12, 16.996, 0), D(7, 41.493, 0)), "DDM"),
    ('12° 16\' 59.93" N, 7° 41\' 29.61" E', (D(12, 16, 59.93), D(7, 41, 29.61)), "DMS"),
    ("... rendezvous point coordinate  12° 16' 59.93'' N | 7° 41' 29.61'' E in Matazu LGA",
     (D(12, 16, 59.93), D(7, 41, 29.61)), "pipe separator - the report that started it"),
    ("32P LU 57703 58227", (12.283305, 7.691555), "MGRS"),
    ("https://maps.google.com/?q=12.283314,7.691558", (12.283314, 7.691558), "Google link"),
    ("geo:12.283314,7.691558?z=17", (12.283314, 7.691558), "geo: link"),
    ("N12 17 E007 41", (D(12, 17, 0), D(7, 41, 0)), "degrees and whole minutes"),
    # negatives
    ("The patrol left at 1230 hours", None, "a time is not a fix"),
    ("Report dated 31st August 2026", None, "a date is not a fix"),
    ("twenty (20) personnel on site", None, "a count is not a fix"),
    ("Serial 4512 3390 issued", None, "a serial is not a fix"),
]

# OCR repairs: (raw OCR text, expected (lat, lon) or None, note)
REPAIR = [
    ('ACFT: 11°58\'16.251"N 7° 3\'42.026"E ~HMSL: 1702m_',
     (D(11, 58, 16.251), D(7, 3, 42.026)), "clean line"),
    ('11°58\'1.596"N «7° 2\'33.688"E = HMSL: 513m',
     (D(11, 58, 1.596), D(7, 2, 33.688)), "hallucinated bracket between the halves"),
    ('11°57\'22,555"N_ 7° 1\'58.684"E ©- HMSL: 513m.',
     (D(11, 57, 22.555), D(7, 1, 58.684)), "comma decimal, underscore after N"),
    ('_11°56\'17.850"N. 7° 3\'54.491"E HMSL: 514m',
     (D(11, 56, 17.850), D(7, 3, 54.491)), "full stop after N"),
    ('8°33\'29.9T9"N 5°19\'20.227°E jt 346K',
     (D(8, 33, 29.919), D(5, 19, 20.227)), "T for 1; degree mark for the second mark"),
    ('11°5725533"N 7°159.066"E',
     (D(11, 57, 25.533), D(7, 1, 59.066)), "both separators lost"),
    ('TGT: 11°56\'14.807"N 7° 4\'4.566"E',
     (D(11, 56, 14.807), D(7, 4, 4.566)), "single-digit seconds"),
    ('7° 4°22.588"E 11°55\'31.051"N', None, "longitude first - lat/lon order not assumed"),
    ('N 12° 16\' 59.93" E 7° 41\' 29.61"',
     (D(12, 16, 59.93), D(7, 41, 29.61)), "hemisphere first - the repair must not eat the separator"),
    ('N12°16\'59.93" E7°41\'29.61"',
     (D(12, 16, 59.93), D(7, 41, 29.61)), "hemisphere first, no spaces around the letters"),
    ('11°56\'17.850°N 7° 3\'54.491"E',
     (D(11, 56, 17.850), D(7, 3, 54.491)), "degree mark for the closing quote still repaired"),
    ('11°56\'17.850"N 7° 3\'54.491 \'E',
     (D(11, 56, 17.850), D(7, 3, 54.491)), "space before a wrong closing mark still repaired"),
]


def close(a, b, tol=1e-6):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def main():
    bad = 0
    for text, want, note in PARSE:
        got = G.find_all(text)
        first = (got[0].lat, got[0].lon) if got else None
        ok = (first is None and want is None) or (first and want and close(first, want, 5e-5))
        if not ok and want is None and first is not None:
            ok = False
        if not ok:
            bad += 1
            print(f"FAIL parse [{note}]\n  {text!r}\n  want {want} got {first}")
    for text, want, note in REPAIR:
        fixed = OCR.fix_text(text)
        got = G.find_all(fixed)
        first = (got[0].lat, got[0].lon) if got else None
        ok = (first is None and want is None) or (first and want and close(first, want, 5e-5))
        if not ok:
            bad += 1
            print(f"FAIL repair [{note}]\n  {text!r}\n  -> {fixed!r}\n  want {want} got {first}")

    total = len(PARSE) + len(REPAIR)
    print(f"{total - bad}/{total} pass" if bad else f"all {total} pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
