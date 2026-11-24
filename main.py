#!/usr/bin/env python3
"""news-image-20261123 -- The World in One Day: Monday 23 November 2026.

Draws a one-page newspaper front page summing up the world's news of
Monday 23 November 2026. Python standard library only (math, os, struct,
zlib). No network, no clock, no randomness, no Pillow, no system fonts.
Lettering is a hand-built vector stroke font drawn with canvas
polylines, so text stays crisp at any size. Writes entry.png
(1024x1024) to MAKEFUN_OUTPUT_DIR. Deterministic: two runs write
byte-identical output.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024


# ---------------------------------------------------------------- PNG output
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, rgb, w, h):
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    idat = zlib.compress(bytes(raw), 6)
    with open(path, "wb") as fh:
        fh.write(sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat)
                 + _chunk(b"IEND", b""))


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = color

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.w, int(x + w))
        y1 = min(self.h, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def disc(self, cx, cy, r, color):
        r = int(r)
        if r <= 0:
            self.set(int(cx), int(cy), color)
            return
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(r * r - dy * dy))
            y = int(cy) + dy
            if 0 <= y < self.h:
                x0 = max(0, int(cx) - dx)
                x1 = min(self.w - 1, int(cx) + dx)
                i = (y * self.w + x0) * 3
                self.px[i:(y * self.w + x1 + 1) * 3] = bytes(color) * (x1 - x0 + 1)

    def line(self, x0, y0, x1, y1, color, width=1):
        dx, dy = x1 - x0, y1 - y0
        dist = math.hypot(dx, dy)
        steps = max(1, int(dist * 2) + 1)
        r = max(0.5, width / 2.0)
        for s in range(steps + 1):
            t = s / steps
            self.disc(x0 + dx * t, y0 + dy * t, r, color)

    def polyline(self, pts, color, width=1, close=False):
        if len(pts) == 1:
            self.disc(pts[0][0], pts[0][1], max(0.6, width / 2.0), color)
            return
        for a, b in zip(pts, pts[1:]):
            self.line(a[0], a[1], b[0], b[1], color, width)
        if close and len(pts) > 2:
            self.line(pts[-1][0], pts[-1][1], pts[0][0], pts[0][1], color, width)

    def polygon(self, pts, color):
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(math.floor(min(ys))))
        y1 = min(self.h, int(math.ceil(max(ys))))
        n = len(pts)
        for y in range(y0, y1):
            xs = []
            for i in range(n):
                x0, yy0 = pts[i]
                x1, yy1 = pts[(i + 1) % n]
                if (yy0 <= y < yy1) or (yy1 <= y < yy0):
                    t = (y - yy0) / (yy1 - yy0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                xa = max(0, int(math.ceil(xs[j])))
                xb = min(self.w - 1, int(math.floor(xs[j + 1])))
                if xb >= xa:
                    i = (y * self.w + xa) * 3
                    self.px[i:(y * self.w + xb + 1) * 3] = bytes(color) * (xb - xa + 1)

    def circle(self, cx, cy, r, color):
        self.disc(cx, cy, r, color)

    def ring(self, cx, cy, r, color, width=2):
        steps = max(12, int(2 * math.pi * r))
        for s in range(steps):
            a = 2 * math.pi * s / steps
            self.disc(cx + r * math.cos(a), cy + r * math.sin(a),
                      max(0.6, width / 2.0), color)

    def arc(self, cx, cy, r, a0, a1, color, width=2):
        steps = max(4, int(abs(a1 - a0) * r))
        for s in range(steps + 1):
            a = a0 + (a1 - a0) * s / steps
            self.disc(cx + r * math.cos(a), cy + r * math.sin(a),
                      max(0.6, width / 2.0), color)

    def ellipse(self, cx, cy, rx, ry, color):
        for dy in range(-int(ry), int(ry) + 1):
            if ry == 0:
                continue
            t = 1.0 - (dy * dy) / (ry * ry)
            if t < 0:
                continue
            dx = int(rx * math.sqrt(t))
            y = int(cy) + dy
            if 0 <= y < self.h:
                x0 = max(0, int(cx) - dx)
                x1 = min(self.w - 1, int(cx) + dx)
                i = (y * self.w + x0) * 3
                self.px[i:(y * self.w + x1 + 1) * 3] = bytes(color) * (x1 - x0 + 1)


# ---------------------------------------------------------------- stroke font
# Grid x 0..5, y 0..8. Cap top y=0, baseline y=6, descender y=8.
# Each glyph: list of polylines; each polyline is "x,y x,y ...".
# A one-point stroke draws a dot.
GLYPHS = {
    "A": ["0,6 2.5,0 5,6", "1.2,4 3.8,4"],
    "B": ["0,6 0,0 3.5,0 5,1.5 3.5,3 5,4.5 3.5,6 0,6"],
    "C": ["5,1.5 4,0 1,0 0,1.5 0,4.5 1,6 4,6 5,4.5"],
    "D": ["0,6 0,0 3,0 5,1.5 5,4.5 3,6 0,6"],
    "E": ["5,0 0,0 0,6 5,6", "0,3 4,3"],
    "F": ["0,6 0,0 5,0", "0,3 4,3"],
    "G": ["5,1.5 4,0 1,0 0,1.5 0,4.5 1,6 4,6 5,5 5,3.5 3.5,3.5"],
    "H": ["0,0 0,6", "5,0 5,6", "0,3 5,3"],
    "I": ["2.5,0 2.5,6", "1,0 4,0", "1,6 4,6"],
    "J": ["5,0 5,5 3.5,6 1.5,6 0.5,5"],
    "K": ["0,0 0,6", "5,0 0,3", "1.5,3.5 5,6"],
    "L": ["0,0 0,6 5,6"],
    "M": ["0,6 0,0 2.5,3.5 5,0 5,6"],
    "N": ["0,6 0,0 5,6 5,0"],
    "O": ["1,0 4,0 5,1.5 5,4.5 4,6 1,6 0,4.5 0,1.5 1,0"],
    "P": ["0,6 0,0 4,0 5,1 5,2.5 4,3.5 0,3.5"],
    "Q": ["1,0 4,0 5,1.5 5,4.5 4,6 1,6 0,4.5 0,1.5 1,0", "3.5,4.5 5,6"],
    "R": ["0,6 0,0 4,0 5,1 5,2.5 4,3.5 0,3.5", "2,3.5 5,6"],
    "S": ["5,1 4,0 1,0 0,1 0,2.5 1,3.5 4,3.5 5,4.5 5,5.5 4,6 1,6 0,5"],
    "T": ["0,0 5,0", "2.5,0 2.5,6"],
    "U": ["0,0 0,5 1,6 4,6 5,5 5,0"],
    "V": ["0,0 2.5,6 5,0"],
    "W": ["0,0 1,6 2.5,2 4,6 5,0"],
    "X": ["0,0 5,6", "5,0 0,6"],
    "Y": ["0,0 2.5,3 5,0", "2.5,3 2.5,6"],
    "Z": ["0,0 5,0 0,6 5,6"],
    "a": ["0.8,4.5 1.5,2.5 3.5,2.5 4.2,4.5 3.5,6 1.5,6 0.8,4.5",
          "4.2,2.5 4.2,6"],
    "b": ["1,0 1,6", "1,3.5 2,2.5 3.5,2.5 4.2,3.5 4.2,5 3.5,6 1,6"],
    "c": ["4.2,3 3.5,2.5 1.5,2.5 0.8,3.5 0.8,5 1.5,6 3.5,6 4.2,5"],
    "d": ["0.8,3.5 1.5,2.5 3.5,2.5 4.2,3.5 4.2,5 3.5,6 1.5,6 0.8,5",
          "4.2,0 4.2,6"],
    "e": ["4.2,4.5 3.5,2.5 1.5,2.5 0.8,4 0.8,5 1.5,6 3.5,6 4.2,5",
          "0.8,4.2 4.2,4.2"],
    "f": ["3.5,6 3.5,1.5 2.5,0.5 1.8,0.5", "1,2.5 4,2.5"],
    "g": ["0.8,4.5 1.5,2.5 3.5,2.5 4.2,4.5 3.5,6 1.5,6 0.8,4.5",
          "4.2,5 4.2,7 3,8 1.5,8 1,7"],
    "h": ["1,0 1,6", "1,4 2,2.5 3.5,2.5 4.2,3.5 4.2,6"],
    "i": ["2.5,2.5 2.5,6", "2.5,0.5"],
    "j": ["3.5,2.5 3.5,7 2.5,8 1.5,8", "3.5,0.5"],
    "k": ["1,0 1,6", "4.2,2.5 1,4", "2,4.5 4.2,6"],
    "l": ["2.5,0 2.5,6"],
    "m": ["0.8,6 0.8,2.5 1.8,2.5 2.5,3.5 2.5,6",
          "2.5,3.5 3.2,2.5 4.2,2.5 4.2,6"],
    "n": ["1,6 1,2.5", "1,4 2,2.5 3.5,2.5 4.2,3.5 4.2,6"],
    "o": ["1.5,2.5 3.5,2.5 4.2,3.5 4.2,5 3.5,6 1.5,6 0.8,5 0.8,3.5 1.5,2.5"],
    "p": ["1,2.5 1,8", "1,4 2,2.5 3.5,2.5 4.2,3.5 4.2,5 3.5,6 1,6"],
    "q": ["0.8,3.5 1.5,2.5 3.5,2.5 4.2,3.5 4.2,5 3.5,6 1.5,6 0.8,5",
          "4.2,2.5 4.2,8"],
    "r": ["1,6 1,2.5", "1,4 2,2.5 3.5,2.5 4.2,3.2"],
    "s": ["4.2,3 3.5,2.5 1.5,2.5 0.8,3.2 0.8,4 1.5,4.5 3.5,4.5 4.2,5.2 "
          "4.2,5.5 3.5,6 1.5,6 0.8,5.5"],
    "t": ["2.8,0 2.8,5.5 2,6 1.2,6", "1,2.5 4.2,2.5"],
    "u": ["1,2.5 1,5 1.5,6 3.5,6 4.2,5 4.2,2.5"],
    "v": ["0.8,2.5 2.5,6 4.2,2.5"],
    "w": ["0.8,2.5 1.5,6 2.5,3.5 3.5,6 4.2,2.5"],
    "x": ["0.8,2.5 4.2,6", "4.2,2.5 0.8,6"],
    "y": ["0.8,2.5 2.5,5 4.2,2.5", "2.5,5 2.5,7 1.8,8 1,8"],
    "z": ["0.8,2.5 4.2,2.5 0.8,6 4.2,6"],
    "0": ["1,0 4,0 5,1.5 5,4.5 4,6 1,6 0,4.5 0,1.5 1,0", "1.5,4.5 3.5,1.5"],
    "1": ["2.5,0 2.5,6", "1,1.5 2.5,0", "1,6 4,6"],
    "2": ["0.5,1 1.5,0 3.5,0 4.5,1 4.5,2.5 3,4 0.5,6 4.5,6"],
    "3": ["0.5,1 1.5,0 3.5,0 4.5,1 4.5,2.5 3,3 4.5,3.5 4.5,5 3.5,6 "
          "1.5,6 0.5,5"],
    "4": ["4,0 4,6", "0,4 4.5,4", "0,4 4,0"],
    "5": ["4.5,0 0.5,0 0.5,2.5 3,2.5 4.5,3.5 4.5,5 3.5,6 1.5,6 0.5,5"],
    "6": ["4.5,1 3.5,0 1.5,0 0.5,1 0.5,4.5 1,6 3.5,6 4.5,5 4.5,3.5 "
          "3.5,2.5 1.5,2.5 0.5,3.5"],
    "7": ["0.5,0 4.5,0 2,6"],
    "8": ["1.5,0 3.5,0 4.5,1 4.5,2.5 3.5,3.5 1.5,3.5 0.5,2.5 0.5,1 1.5,0",
          "1.5,3.5 0.5,4.5 0.5,5 1.5,6 3.5,6 4.5,5 4.5,4.5 3.5,3.5"],
    "9": ["0.5,5 1.5,6 3.5,6 4.5,5 4.5,1.5 3.5,0 1.5,0 0.5,1 0.5,2.5 "
          "1.5,3.5 3.5,3.5 4.5,2.5"],
    ".": ["2.5,6"],
    ",": ["2.5,5.8 2.5,6.8 2,7.8"],
    ":": ["2.5,2", "2.5,5"],
    ";": ["2.5,2", "2.5,5 2.5,6 2,7.5"],
    "!": ["2.5,0 2.5,4.5", "2.5,6"],
    "?": ["0.8,1.5 1.5,0.5 3.5,0.5 4.2,1.5 4.2,2.5 3,3.5 2.5,4", "2.5,6"],
    "-": ["0.8,3.2 4.2,3.2"],
    "\u2013": ["0.5,3.2 4.5,3.2"],
    "\u2014": ["0,3.2 5,3.2"],
    "'": ["2.8,0 2.2,1.8"],
    "\u2019": ["2.8,0 2.2,1.8"],
    '"': ["1.5,0 1.5,1.8", "3.5,0 3.5,1.8"],
    "\u201c": ["1.5,0 1.5,1.8", "3.5,0 3.5,1.8"],
    "\u201d": ["1.5,0 1.5,1.8", "3.5,0 3.5,1.8"],
    "(": ["3.5,0 2,1.5 2,4.5 3.5,6"],
    ")": ["1.5,0 3,1.5 3,4.5 1.5,6"],
    "[": ["4,0 1,0 1,6 4,6"],
    "]": ["1,0 4,0 4,6 1,6"],
    "/": ["4.5,0 0.5,6"],
    "%": ["0.8,1 2,1 2,2.2 0.8,2.2", "4.2,0 0.8,6",
          "3,3.8 4.2,3.8 4.2,5 3,5"],
    "+": ["2.5,1 2.5,5", "0.8,3 4.2,3"],
    "=": ["0.8,2.2 4.2,2.2", "0.8,4.2 4.2,4.2"],
    "$": ["2.5,-0.5 2.5,6.5",
          "4.2,1.5 3.5,0.5 1.5,0.5 0.8,1.5 0.8,2.5 1.5,3.2 3.5,3.2 4.2,4 "
          "4.2,5 3.5,6 1.5,6 0.8,5"],
    "\u00b7": ["2.5,3.2"],
    "\u2022": ["\u25cf"],
    "~": ["0.8,4 1.8,2.8 3,4 4.2,2.8"],
    "_": ["0.5,6.5 4.5,6.5"],
    "\u00b0": ["2,0.5 3,0.5 3.5,1 3.5,1.8 3,2.3 2,2.3 1.5,1.8 1.5,1 2,0.5"],
    "\u00d7": ["1,1 4,5", "4,1 1,5"],
    "\u2192": ["0.5,3 4.5,3", "3.5,1.8 4.5,3 3.5,4.2"],
    "<": ["4,1 1,3 4,5"],
    ">": ["1,1 4,3 1,5"],
    "#": ["1.5,0 1.5,6", "3.5,0 3.5,6", "0.5,2 4.5,2", "0.5,4.2 4.5,4.2"],
    "&": ["4,5.5 3.5,6 1.5,6 0.8,5.2 0.8,4 1.5,3.2 3,3.2 4,4.2 4,5.5 "
          "3.5,6.5 2,6.5 1,5.5 1,2.5 2,0.5 3.5,0.5 4.2,1.5"],
    "\u00e9": ["0.8,4.5 1.5,2.5 3.5,2.5 4.2,4.5 3.5,6 1.5,6 0.8,4.5",
              "0.8,4.2 4.2,4.2", "2,0 3.5,0.5"],
    "\u00a3": ["4,0 1.5,0 0.5,1 0.5,3 1.5,3.5 0.5,4 0.5,5 1,6 4.5,6",
              "1.5,2.2 3.5,2.2"],
}

NARROW = set("iljtfI!'.:;,|")
WIDE = set("mwMW")
ADV = {}
for _ch in GLYPHS:
    ADV[_ch] = 3.6 if _ch in NARROW else (7.2 if _ch in WIDE else 6.0)
ADV[" "] = 4.0
ADV["\u2014"] = 7.0
ADV["\u2013"] = 5.0
ADV["\u00b7"] = 4.0
ADV["\u2022"] = 6.0

_glyph_cache = {}


def _glyph_mask(ch, size, weight, sx):
    key = (ch, size, weight, sx)
    hit = _glyph_cache.get(key)
    if hit is not None:
        return hit
    unit = size / 6.0
    adv = ADV.get(ch, 6.0) * unit * sx
    gw = max(1, int(math.ceil(adv)) + 2)
    gh = max(1, int(math.ceil(8.6 * unit)) + 2)
    mask = bytearray(gw * gh)
    strokes = GLYPHS.get(ch)
    if strokes:
        tmp = Canvas(gw, gh, b"\x00\x00\x00")
        for stroke in strokes:
            if stroke == "\u25cf":
                tmp.disc(gw / 2.0, 3.4 * unit, 1.5 * unit, b"\xff\xff\xff")
                continue
            pts = []
            for tok in stroke.split():
                xs, ys = tok.split(",")
                pts.append((float(xs) * unit * sx + 1.0,
                            float(ys) * unit + 1.0))
            tmp.polyline(pts, b"\xff\xff\xff", max(1.0, weight * unit * 0.30))
        if weight > 1.6:
            for stroke in strokes:
                if stroke == "\u25cf":
                    continue
                pts = []
                for tok in stroke.split():
                    xs, ys = tok.split(",")
                    pts.append((float(xs) * unit * sx + 1.2,
                                float(ys) * unit + 1.0))
                tmp.polyline(pts, b"\xff\xff\xff", max(1.0, weight * unit * 0.30))
        for i in range(gw * gh):
            if tmp.px[i * 3]:
                mask[i] = 255
    out = (gw, gh, mask, adv)
    _glyph_cache[key] = out
    return out


def text_width(text, size, weight=1.0, sx=0.72):
    unit = size / 6.0
    return sum(ADV.get(ch, 6.0) * unit * sx for ch in text)


def draw_text(cv, x, y, text, size, color, weight=1.0, align="left", sx=0.72):
    """Draw text; (x, y) is the baseline start (or centre/right per align)."""
    if align != "left":
        w = text_width(text, size, weight, sx)
        if align == "center":
            x -= w / 2.0
        elif align == "right":
            x -= w
    cx = x
    unit = size / 6.0
    for ch in text:
        if ch == " ":
            cx += ADV[" "] * unit * sx
            continue
        gw, gh, mask, adv = _glyph_mask(ch, size, weight, sx)
        top = int(round(y - 6 * unit - 1.0))
        left = int(round(cx - 1.0))
        for row in range(gh):
            yy = top + row
            if yy < 0 or yy >= cv.h:
                continue
            base = row * gw
            for col in range(gw):
                if mask[base + col]:
                    xx = left + col
                    if 0 <= xx < cv.w:
                        i = (yy * cv.w + xx) * 3
                        cv.px[i:i + 3] = color
        cx += adv
    return cx


def wrap_text(text, size, max_w, weight=1.0, sx=0.72):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, size, weight, sx) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_para(cv, x, y, text, size, color, max_w, weight=1.0, leading=1.45,
              sx=0.72):
    lines = wrap_text(text, size, max_w, weight, sx)
    for ln in lines:
        draw_text(cv, x, y, ln, size, color, weight, sx=sx)
        y += size * leading
    return y


# ---------------------------------------------------------------- palette
PAPER = bytes((245, 240, 227))
INK = bytes((26, 26, 26))
RED = bytes((164, 31, 31))
DARKRED = bytes((122, 18, 18))
NAVY = bytes((28, 48, 80))
TEAL = bytes((18, 92, 86))
GOLD = bytes((176, 124, 24))
GREY = bytes((110, 104, 90))
LIGHT = bytes((232, 226, 210))
WHITE = bytes((255, 255, 255))
SKY = bytes((176, 205, 225))
NIGHT = bytes((16, 24, 48))
SUN = bytes((232, 158, 44))
FLAME = bytes((232, 98, 24))
GREEN = bytes((46, 110, 58))
CHIP = bytes((118, 185, 0))

CHIP_COLORS = [NAVY, DARKRED, TEAL, GOLD, bytes((96, 48, 96)),
               bytes((60, 90, 140)), GREY, bytes((40, 90, 60))]


def _star(cv, cx, cy, r, color):
    for a in range(8):
        ang = math.pi * a / 4
        cv.line(cx - r * math.cos(ang), cy - r * math.sin(ang),
                cx + r * math.cos(ang), cy + r * math.sin(ang), color, 1)


def _waves(cv, x, y, w, color, amp=3, step=14):
    pts = []
    for xx in range(int(x), int(x + w) + 1, 4):
        pts.append((xx, y + amp * math.sin(xx / step)))
    cv.polyline(pts, color, 1.5)


def _flame(cv, cx, cy, s, color=FLAME):
    cv.polygon([(cx - 0.55 * s, cy), (cx, cy - 1.5 * s), (cx + 0.4 * s, cy - 0.5 * s),
                (cx + 0.7 * s, cy), (cx + 0.2 * s, cy + 0.5 * s),
                (cx - 0.3 * s, cy + 0.5 * s)], color)
    cv.polygon([(cx - 0.25 * s, cy), (cx, cy - 0.7 * s), (cx + 0.25 * s, cy),
                (cx, cy + 0.3 * s)], SUN)


def _smoke(cv, cx, cy, color=GREY):
    for i, r in enumerate((3, 4, 5, 6)):
        cv.disc(cx + (i % 2) * 4 - 2, cy - i * 7, r, color)


# ---------------------------------------------------------------- lead scenes
def scene_nvidia(cv, x, y, w, h):
    """Green chip, rising chart, +31% arrow."""
    cv.fill_rect(x, y, w, h, bytes((16, 24, 16)))
    cv.fill_rect(x, y + h * 0.72, w, h * 0.28, bytes((28, 44, 28)))
    # chip
    cx, cy = x + w * 0.24, y + h * 0.42
    s = h * 0.30
    cv.fill_rect(cx - s, cy - s * 0.75, s * 2, s * 1.5, bytes((24, 40, 24)))
    for k in range(3):
        cv.fill_rect(cx - s - 8, cy - s * 0.5 + k * s * 0.5, 8, 4, CHIP)
        cv.fill_rect(cx + s, cy - s * 0.5 + k * s * 0.5, 8, 4, CHIP)
        cv.fill_rect(cx - s * 0.5 + k * s * 0.5, cy - s * 0.75 - 8, 4, 8, CHIP)
        cv.fill_rect(cx - s * 0.5 + k * s * 0.5, cy + s * 0.75, 4, 8, CHIP)
    cv.fill_rect(cx - s * 0.45, cy - s * 0.32, s * 0.9, s * 0.64, CHIP)
    draw_text(cv, cx, cy + 5, "NV", 16, INK, weight=2.0, align="center")
    # rising chart line
    pts = [(x + w * 0.44, y + h * 0.62), (x + w * 0.55, y + h * 0.58),
           (x + w * 0.64, y + h * 0.64), (x + w * 0.72, y + h * 0.50),
           (x + w * 0.82, y + h * 0.52), (x + w * 0.93, y + h * 0.22)]
    cv.polyline(pts, CHIP, 3)
    cv.polygon([(x + w * 0.93, y + h * 0.22), (x + w * 0.86, y + h * 0.24),
                (x + w * 0.92, y + h * 0.32)], CHIP)
    draw_text(cv, x + w * 0.56, y + h * 0.16, "+31%", 22, CHIP, weight=2.0)


def scene_merkury(cv, x, y, w, h):
    """Sea at dusk: warship listing, drones overhead, smoke."""
    cv.fill_rect(x, y, w, h, bytes((214, 176, 130)))
    cv.fill_rect(x, y + h * 0.55, w, h * 0.45, bytes((30, 68, 104)))
    _waves(cv, x, y + h * 0.62, w, bytes((120, 170, 210)), 3, 12)
    _waves(cv, x, y + h * 0.80, w, bytes((90, 140, 185)), 3, 10)
    cv.circle(x + w * 0.86, y + h * 0.18, h * 0.11, bytes((240, 220, 180)))
    # listing warship
    cv.polygon([(x + w * 0.10, y + h * 0.46), (x + w * 0.86, y + h * 0.58),
                (x + w * 0.78, y + h * 0.72), (x + w * 0.18, y + h * 0.62)],
               bytes((96, 96, 100)))
    cv.fill_rect(x + w * 0.30, y + h * 0.36, w * 0.26, h * 0.12,
                 bytes((200, 200, 196)))
    cv.fill_rect(x + w * 0.40, y + h * 0.26, w * 0.05, h * 0.12,
                 bytes((60, 60, 60)))
    cv.polygon([(x + w * 0.55, y + h * 0.40), (x + w * 0.58, y + h * 0.44),
                (x + w * 0.55, y + h * 0.50), (x + w * 0.70, y + h * 0.44)],
               bytes((200, 40, 40)))
    _flame(cv, x + w * 0.60, y + h * 0.34, 10)
    _smoke(cv, x + w * 0.60, y + h * 0.16)
    # sea drones: small boats with wakes
    for dx in (0.14, 0.34, 0.52):
        bx = x + w * dx
        by = y + h * 0.78
        cv.polygon([(bx, by), (bx + 18, by), (bx + 14, by + 6), (bx + 4, by + 6)],
                   bytes((220, 220, 215)))
        cv.line(bx, by + 8, bx - 16, by + 12, WHITE, 1.5)
        cv.line(bx, by + 8, bx - 12, by + 14, WHITE, 1.5)
    # drone in the sky
    cv.disc(x + w * 0.72, y + h * 0.14, 3, INK)
    cv.line(x + w * 0.66, y + h * 0.14, x + w * 0.78, y + h * 0.14, INK, 2)


def scene_cop31(cv, x, y, w, h):
    """Dawn over Antalya: sun, skyline, empty chairs, globe."""
    cv.fill_rect(x, y, w, h, bytes((252, 226, 180)))
    cv.fill_rect(x, y, w, h * 0.42, bytes((250, 196, 130)))
    cv.circle(x + w * 0.74, y + h * 0.30, h * 0.16, SUN)
    cv.ring(x + w * 0.74, y + h * 0.30, h * 0.22, SUN, 2)
    cv.fill_rect(x, y + h * 0.62, w, h * 0.38, bytes((58, 52, 66)))
    for i, bh in enumerate((0.22, 0.34, 0.16, 0.30, 0.20)):
        bx = x + w * (0.04 + i * 0.19)
        cv.fill_rect(bx, y + h * 0.62 - h * bh, w * 0.13, h * (bh + 0.38),
                     bytes((38, 34, 46)))
        for wy in range(3):
            cv.fill_rect(bx + 4, y + h * 0.62 - h * bh + 5 + wy * 8, 3, 4, SUN)
    cx, cy, r = x + w * 0.24, y + h * 0.34, h * 0.24
    cv.circle(cx, cy, r, bytes((94, 140, 190)))
    cv.ellipse(cx, cy, r * 0.45, r, bytes((46, 110, 58)))
    cv.line(cx - r, cy, cx + r, cy, bytes((210, 225, 240)), 1.5)
    cv.line(cx, cy - r, cx, cy + r, bytes((210, 225, 240)), 1.5)
    # empty chairs row (no deal: nobody sits)
    for i in range(4):
        bx = x + w * (0.55 + i * 0.11)
        cv.fill_rect(bx, y + h * 0.80, w * 0.07, h * 0.10, bytes((120, 110, 100)))
        cv.fill_rect(bx, y + h * 0.72, w * 0.07, h * 0.08, bytes((120, 110, 100)))


# ---------------------------------------------------------------- feature scenes
def scene_collapse(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, bytes((210, 200, 180)))
    cv.fill_rect(x + w * 0.12, y + h * 0.30, w * 0.60, h * 0.55,
                 bytes((150, 140, 126)))
    for i in range(3):
        for j in range(2):
            cv.fill_rect(x + w * (0.18 + i * 0.19), y + h * (0.38 + j * 0.24),
                         w * 0.10, h * 0.12, bytes((40, 40, 46)))
    cv.polygon([(x + w * 0.72, y + h * 0.30), (x + w * 0.86, y + h * 0.42),
                (x + w * 0.72, y + h * 0.55), (x + w * 0.60, y + h * 0.45)],
               bytes((120, 110, 96)))
    cv.line(x + w * 0.60, y + h * 0.45, x + w * 0.86, y + h * 0.42, INK, 2)
    _smoke(cv, x + w * 0.76, y + h * 0.22)
    cv.polygon([(x + w * 0.10, y + h * 0.85), (x + w * 0.30, y + h * 0.85),
                (x + w * 0.26, y + h * 0.78), (x + w * 0.14, y + h * 0.78)],
               bytes((110, 100, 86)))


def scene_khartoum(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, bytes((238, 214, 170)))
    cv.fill_rect(x, y + h * 0.60, w, h * 0.40, bytes((120, 96, 66)))
    for i, bh in enumerate((0.24, 0.36, 0.18, 0.30)):
        bx = x + w * (0.06 + i * 0.23)
        cv.fill_rect(bx, y + h * 0.60 - h * bh, w * 0.16, h * (bh + 0.40),
                     bytes((90, 74, 54)))
    cv.disc(x + w * 0.78, y + h * 0.24, 2.5, INK)
    cv.line(x + w * 0.72, y + h * 0.24, x + w * 0.84, y + h * 0.24, INK, 2)
    cv.line(x + w * 0.78, y + h * 0.24, x + w * 0.70, y + h * 0.42, RED, 1.5)
    _flame(cv, x + w * 0.42, y + h * 0.52, 8)
    _smoke(cv, x + w * 0.42, y + h * 0.34)


def scene_factory(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, bytes((238, 232, 216)))
    cv.fill_rect(x + w * 0.12, y + h * 0.46, w * 0.76, h * 0.34,
                 bytes((150, 96, 80)))
    cv.polygon([(x + w * 0.12, y + h * 0.46), (x + w * 0.30, y + h * 0.28),
                (x + w * 0.48, y + h * 0.46), (x + w * 0.66, y + h * 0.28),
                (x + w * 0.84, y + h * 0.46)], bytes((120, 70, 58)))
    cv.fill_rect(x + w * 0.78, y + h * 0.18, w * 0.07, h * 0.30,
                 bytes((110, 104, 96)))
    _flame(cv, x + w * 0.42, y + h * 0.34, 10)
    _smoke(cv, x + w * 0.80, y + h * 0.10)
    for i in range(3):
        cv.fill_rect(x + w * (0.20 + i * 0.20), y + h * 0.56, w * 0.10,
                     h * 0.12, SUN)


def scene_plane(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, SKY)
    cv.fill_rect(x + w * 0.10, y + h * 0.66, w * 0.80, h * 0.06,
                 bytes((90, 90, 96)))
    cv.ellipse(x + w * 0.50, y + h * 0.42, w * 0.34, h * 0.14, WHITE)
    cv.polygon([(x + w * 0.78, y + h * 0.42), (x + w * 0.92, y + h * 0.34),
                (x + w * 0.92, y + h * 0.50)], WHITE)
    cv.polygon([(x + w * 0.44, y + h * 0.34), (x + w * 0.52, y + h * 0.20),
                (x + w * 0.58, y + h * 0.34)], bytes((180, 30, 30)))
    cv.polygon([(x + w * 0.44, y + h * 0.50), (x + w * 0.52, y + h * 0.64),
                (x + w * 0.58, y + h * 0.50)], bytes((180, 30, 30)))
    for i in range(4):
        cv.fill_rect(x + w * (0.30 + i * 0.10), y + h * 0.38, w * 0.04,
                     h * 0.06, NAVY)
    cv.line(x + w * 0.08, y + h * 0.42, x + w * 0.16, y + h * 0.42, RED, 3)


def scene_tanker(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, bytes((250, 200, 140)))
    cv.fill_rect(x, y + h * 0.60, w, h * 0.40, bytes((38, 90, 128)))
    _waves(cv, x, y + h * 0.68, w, WHITE, 2, 10)
    cv.polygon([(x + w * 0.12, y + h * 0.50), (x + w * 0.88, y + h * 0.50),
                (x + w * 0.80, y + h * 0.70), (x + w * 0.20, y + h * 0.70)],
               bytes((40, 40, 44)))
    cv.fill_rect(x + w * 0.30, y + h * 0.32, w * 0.34, h * 0.18,
                 bytes((220, 220, 215)))
    _flame(cv, x + w * 0.62, y + h * 0.34, 9)
    _smoke(cv, x + w * 0.62, y + h * 0.18)
    cv.line(x + w * 0.18, y + h * 0.20, x + w * 0.30, y + h * 0.34, RED, 2)
    cv.disc(x + w * 0.16, y + h * 0.18, 3, RED)


def scene_stadium(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, bytes((214, 232, 196)))
    cv.fill_rect(x, y + h * 0.68, w, h * 0.32, bytes((90, 150, 70)))
    cv.ellipse(x + w * 0.50, y + h * 0.52, w * 0.42, h * 0.18,
               bytes((240, 240, 235)))
    cv.ellipse(x + w * 0.50, y + h * 0.50, w * 0.30, h * 0.12,
               bytes((120, 170, 90)))
    cv.line(x + w * 0.50, y + h * 0.38, x + w * 0.50, y + h * 0.62, WHITE, 2)
    cv.circle(x + w * 0.50, y + h * 0.50, h * 0.05, WHITE)
    cv.ring(x + w * 0.50, y + h * 0.50, h * 0.05, WHITE, 1.5)
    cv.polygon([(x + w * 0.14, y + h * 0.30), (x + w * 0.20, y + h * 0.18),
                (x + w * 0.26, y + h * 0.30)], RED)
    cv.polygon([(x + w * 0.74, y + h * 0.30), (x + w * 0.80, y + h * 0.18),
                (x + w * 0.86, y + h * 0.30)], RED)


def scene_fbi(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, bytes((226, 232, 240)))
    for i in range(3):
        cv.fill_rect(x + w * 0.16, y + h * (0.16 + i * 0.22), w * 0.34,
                     h * 0.14, NAVY if i % 2 == 0 else bytes((52, 84, 130)))
        cv.fill_rect(x + w * 0.20, y + h * (0.20 + i * 0.22), w * 0.26,
                     h * 0.03, WHITE)
        cv.fill_rect(x + w * 0.20, y + h * (0.25 + i * 0.22), w * 0.18,
                     h * 0.03, WHITE)
    cv.ring(x + w * 0.68, y + h * 0.40, h * 0.20, INK, 3)
    cv.line(x + w * 0.80, y + h * 0.54, x + w * 0.92, y + h * 0.72, INK, 4)
    cv.fill_rect(x + w * 0.60, y + h * 0.32, w * 0.16, h * 0.03, RED)
    cv.fill_rect(x + w * 0.60, y + h * 0.38, w * 0.10, h * 0.03, RED)


def scene_chart(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, bytes((238, 240, 236)))
    for i in range(4):
        cv.line(x + w * 0.14, y + h * (0.20 + i * 0.20),
                x + w * 0.86, y + h * (0.20 + i * 0.20),
                bytes((200, 205, 200)), 1)
    cv.polyline([(x + w * 0.16, y + h * 0.72), (x + w * 0.30, y + h * 0.66),
                 (x + w * 0.44, y + h * 0.70), (x + w * 0.56, y + h * 0.52),
                 (x + w * 0.70, y + h * 0.56), (x + w * 0.84, y + h * 0.30)],
                GREEN, 3)
    cv.disc(x + w * 0.84, y + h * 0.30, 4, GREEN)
    cv.circle(x + w * 0.50, y + h * 0.34, h * 0.13, bytes((240, 170, 40)))
    draw_text(cv, x + w * 0.50, y + h * 0.40, "B", 13, bytes((150, 95, 0)),
              weight=2.0, align="center")


def scene_baseball(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, bytes((214, 232, 196)))
    cv.fill_rect(x, y + h * 0.70, w, h * 0.30, bytes((120, 160, 90)))
    cv.polygon([(x + w * 0.30, y + h * 0.14), (x + w * 0.42, y + h * 0.14),
                (x + w * 0.48, y + h * 0.58), (x + w * 0.34, y + h * 0.58)],
               bytes((196, 164, 110)))
    cv.line(x + w * 0.36, y + h * 0.14, x + w * 0.30, y + h * 0.02,
            bytes((120, 90, 60)), 3)
    cv.circle(x + w * 0.72, y + h * 0.24, h * 0.10, WHITE)
    cv.arc(x + w * 0.72, y + h * 0.24, h * 0.07, 0.6, 2.2, RED, 1.5)
    cv.arc(x + w * 0.72, y + h * 0.24, h * 0.07, 3.7, 5.3, RED, 1.5)
    for i in range(3):
        cv.line(x + w * (0.60 + i * 0.06), y + h * 0.70,
                x + w * (0.60 + i * 0.06), y + h * 0.44, SUN, 2)


def scene_flag(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, bytes((238, 232, 216)))
    cv.line(x + w * 0.30, y + h * 0.12, x + w * 0.30, y + h * 0.88,
            bytes((90, 70, 40)), 3)
    cv.polygon([(x + w * 0.30, y + h * 0.12), (x + w * 0.78, y + h * 0.24),
                (x + w * 0.30, y + h * 0.38)], bytes((255, 153, 51)))
    cv.polygon([(x + w * 0.30, y + h * 0.38), (x + w * 0.78, y + h * 0.50),
                (x + w * 0.30, y + h * 0.62)], WHITE)
    cv.polygon([(x + w * 0.30, y + h * 0.62), (x + w * 0.78, y + h * 0.74),
                (x + w * 0.30, y + h * 0.86)], bytes((19, 136, 8)))
    cv.circle(x + w * 0.52, y + h * 0.50, h * 0.07, NAVY)
    cv.ring(x + w * 0.52, y + h * 0.50, h * 0.07, NAVY, 1.5)


# ---------------------------------------------------------------- world map
# Rough continent outlines (lon, lat) for a small equirectangular map.
CONTINENTS = [
    [(-168, 66), (-140, 70), (-120, 71), (-95, 69), (-82, 66), (-75, 62),
     (-65, 60), (-55, 52), (-60, 46), (-70, 42), (-75, 35), (-80, 26),
     (-84, 30), (-90, 21), (-97, 26), (-105, 22), (-110, 24), (-117, 33),
     (-124, 40), (-125, 49), (-135, 58), (-155, 58), (-165, 60)],
    [(-78, 9), (-72, 12), (-62, 9), (-52, 5), (-44, -3), (-35, -8),
     (-38, -15), (-41, -23), (-48, -28), (-58, -35), (-65, -41),
     (-70, -52), (-73, -44), (-73, -30), (-77, -12), (-80, 0), (-77, 7)],
    [(-17, 15), (-17, 28), (-10, 31), (-5, 35), (10, 37), (20, 32),
     (32, 31), (35, 28), (43, 12), (48, 11), (51, 12), (44, -1), (40, -10),
     (36, -18), (32, -26), (26, -34), (18, -35), (15, -27), (12, -18),
     (13, -10), (9, 4), (-8, 5), (-13, 8)],
    [(-10, 36), (-9, 43), (-2, 44), (-1, 46), (-4, 48), (0, 51), (5, 53),
     (8, 57), (12, 56), (18, 56), (21, 55), (24, 59), (28, 60), (30, 62),
     (28, 70), (40, 68), (45, 60), (38, 47), (30, 46), (28, 41), (23, 40),
     (19, 42), (12, 44), (8, 44), (3, 42), (-1, 38)],
    [(30, 62), (40, 68), (55, 68), (70, 72), (100, 77), (130, 72),
     (160, 69), (178, 65), (162, 60), (158, 52), (142, 50), (135, 43),
     (127, 40), (122, 31), (120, 22), (110, 20), (105, 9), (100, 7),
     (97, 16), (92, 22), (88, 22), (80, 13), (77, 8), (72, 20), (66, 25),
     (61, 25), (57, 26), (52, 28), (48, 30), (44, 29), (40, 32), (36, 36),
     (30, 36), (27, 40), (30, 46), (35, 50), (40, 55), (35, 60)],
    [(114, -22), (122, -14), (132, -12), (137, -15), (142, -11),
     (146, -19), (150, -23), (153, -27), (150, -37), (146, -39),
     (140, -38), (135, -35), (129, -32), (124, -33), (115, -35),
     (113, -26)],
    [(133, -12), (136, -15), (136, -22), (132, -32), (129, -31),
     (126, -32), (124, -33), (123, -34), (118, -35), (115, -33),
     (114, -30), (114, -22)],
]


def draw_map(cv, x, y, w, h, pins):
    cv.fill_rect(x, y, w, h, bytes((206, 224, 238)))
    for poly in CONTINENTS:
        pts = []
        for lon, lat in poly:
            px = x + (lon + 180.0) / 360.0 * w
            py = y + (90.0 - lat) / 180.0 * h
            pts.append((px, py))
        cv.polygon(pts, bytes((228, 214, 178)))
        cv.polyline(pts, bytes((170, 156, 120)), 1, close=True)
    for num, lon, lat in pins:
        px = x + (lon + 180.0) / 360.0 * w
        py = y + (90.0 - lat) / 180.0 * h
        cv.disc(px, py, 7, RED)
        cv.ring(px, py, 7, WHITE, 1.5)
        draw_text(cv, px, py + 3.2, str(num), 9, WHITE, weight=2.0,
                  align="center")


# ---------------------------------------------------------------- the news
SUBHEAD = ("Huang is back at Nvidia \u00b7 Ukraine sinks a Russian warship "
           "off Libya \u00b7 COP31 ends with no deal")

NUMBERS = [
    ("+31%", "NVIDIA SHARES IN A DAY"),
    ("+$950B", "NVIDIA VALUE ADDED"),
    ("7", "SEA DRONES VS MERKURY"),
    ("11", "DEAD IN DYMER STRIKE"),
    ("24", "DEAD IN BANTEN FIRE"),
    ("130", "PARTIES REJECTED COP31 TEXT"),
]

CHIPS = [("EUROPE", 12), ("MIDDLE EAST", 5), ("AMERICAS", 6),
         ("SOUTH ASIA", 4), ("ASIA-PACIFIC", 2), ("AFRICA", 2),
         ("MARKETS & SPORT", 3), ("WORLD", 1)]

UTC_STRIP = ("THE DAY IN UTC \u2014 14:00 Nvidia reinstates Huang \u00b7 "
             "15:20 US strike reported off Qeshm Island \u00b7 21:00 Wall "
             "Street closes: Nasdaq +6.5%, S&P +4.7%")

LEADS = [
    dict(scene=scene_nvidia, num=1, place="SANTA CLARA, USA",
         beat="TECH", tag="CONFIRMED",
         head="Huang is back: Nvidia reinstates its CEO after 11 days",
         body=("The board restores Jensen Huang as CEO, president and "
               "director, 11 days after he resigned. Shares jump 31% "
               "\u2014 best day since 2003 \u2014 adding about $950bn."),
         src="Sources: Reuters \u00b7 WSJ \u00b7 CNN"),
    dict(scene=scene_merkury, num=2, place="OFF BENGHAZI, LIBYA",
         beat="WAR AT SEA", tag="CONFIRMED",
         head="Ukraine says its sea drones sank the Russian corvette Merkury",
         body=("President Zelensky says seven sea drones sank the "
               "Merkury off Libya and hit a second vessel. The Kremlin "
               "warns of escalation; Albania denies the launch."),
         src="Sources: Reuters \u00b7 BBC"),
    dict(scene=scene_cop31, num=3, place="ANTALYA, TURKIYE",
         beat="CLIMATE", tag="FALLOUT",
         head="COP31 ends with no deal \u2014 now the blame and the reform calls",
         body=("The summit closed with no approved text after the draft "
               "dropped any mention of moving away from fossil fuels. "
               "Calls grow for urgent reform of the UN climate talks."),
         src="Sources: The Guardian \u00b7 BBC \u00b7 Reuters"),
]

FEATURES = [
    dict(scene=scene_collapse, num=4, place="DYMER, UKRAINE", beat="WAR",
         head="Drone collapses block of flats; 11 dead",
         body=("A five-storey block partly collapses; a boy is pulled "
               "alive after 14 hours."),
         src="Reuters"),
    dict(scene=scene_khartoum, num=5, place="KHARTOUM, SUDAN", beat="WAR",
         head="Drone strikes hit homes and UN site; 4 die",
         body=("Strikes hit homes and a UN compound near Khartoum; fears "
               "grow for civilians."),
         src="Reuters"),
    dict(scene=scene_factory, num=6, place="CIKANDE, INDONESIA", beat="FIRE",
         head="Search goes on for dozens missing after fire",
         body=("At least 24 dead at the Fonusa Agung Mulia candy plant; "
               "dozens still missing."),
         src="Detiknews \u00b7 AP"),
    dict(scene=scene_plane, num=7, place="BRUSSELS, BELGIUM", beat="STRIKE",
         head="Belgium strike grounds flights, halts trains",
         body=("An anti-austerity strike disrupts flights and trains "
               "across Belgium."),
         src="BBC"),
    dict(scene=scene_tanker, num=8, place="TEHRAN / D.C.",
         beat="GULF",
         head="Trump warns Iran of \u2018very traumatic\u2019 outcome",
         body=("Trump may send a second carrier to the Gulf; Iran vows "
               "to use \u2018all means\u2019."),
         src="Al Jazeera \u00b7 Reuters"),
    dict(scene=scene_stadium, num=9, place="LONDON, UK", beat="POLITICS",
         head="UK to host the 2035 Women\u2019s World Cup",
         body=("FIFA confirms the UK as 2035 host; Burnham defends the "
               "new EU agreement."),
         src="BBC"),
    dict(scene=scene_fbi, num=10, place="WASHINGTON, USA", beat="CYBER",
         head="FBI probes hack of its crime database",
         body=("The FBI investigates an apparent hack of the National "
               "Crime Information Center."),
         src="BBC \u00b7 AP"),
    dict(scene=scene_chart, num=11, place="NEW YORK, USA", beat="MARKETS",
         head="Bitcoin rebounds from two-year low to $61,000",
         body=("Bitcoin bounces back as Wall Street futures recover "
               "after Friday\u2019s plunge."),
         src="CoinDesk"),
    dict(scene=scene_baseball, num=12, place="NEW YORK, USA", beat="SPORT",
         head="Skubal agrees $450m Mets deal, pitcher record",
         body=("Two-time Cy Young winner Tarik Skubal agrees a nine-year, "
               "$450m Mets deal."),
         src="AP"),
    dict(scene=scene_flag, num=13, place="NEW DELHI", beat="DIPLOMACY",
         head="Modi offers Nepal an offshore IIT campus",
         body=("Modi announces an offshore IIT campus in Nepal and "
               "closer ties on the PM\u2019s visit."),
         src="Indian media"),
]

ALSO = [
    (14, "ROSTOV", "Ukraine hits Russian oil sites", "Reuters"),
    (15, "BALTIC", "Sparta II on fire after drone hit", "AP"),
    (16, "SAUDI", "Houthi missiles hit power plant", "Reuters"),
    (17, "HORMUZ", "Tanker hit, fire, no casualties", "UKMTO"),
    (18, "QESHM", "US strike reported off island", "Reports"),
    (19, "BERLIN", "Germany pledges $300m aid to Kyiv", "Reuters"),
    (20, "KYIV", "Patriot interceptors exhausted", "Reports"),
    (21, "SENEGAL", "Migrant boat capsizes, 4 dead", "AP"),
    (22, "YEREVAN", "Draft constitution aids peace", "Reports"),
    (23, "LOUISIANA", "Amtrak Sunset Limited derails", "AP"),
    (24, "BRUSSELS", "EU plans 3% tax on Big Tech", "Reports"),
    (25, "TOKYO", "SoftBank to invest $2bn in Intel", "Reports"),
    (26, "DHAKA", "Bangladesh starts mass typhoid jabs", "Reports"),
    (27, "HIMALAYAS", "Scores missing after flood", "Reports"),
    (28, "INDIA", "Ex-MP Revanna sentenced to life", "Reports"),
    (29, "USA", "Two die in varsity shooting", "Reports"),
    (30, "USA", "New citizenship test, H-1B changes", "Reports"),
    (31, "USA", "Democrats unveil 2028 primary plan", "Reports"),
    (32, "WASHINGTON", "Trump limits Congress data demands", "AP"),
    (33, "GAZA", "Oxfam: Gaza now a \u2018toxic wasteland\u2019", "Oxfam"),
    (34, "MANCHESTER", "Co-op Live evacuated", "BBC"),
    (35, "LONDON", "AI screening trial invites 700,000", "NHS"),
]

DATE_CHECK = ("DATE CHECK \u00b7 Left out on purpose, first reported before "
              "Monday: ICJ Myanmar genocide ruling (19 Nov) \u00b7 Kerch "
              "Bridge strike (17 Nov) \u00b7 Shenzhen summit (19 Nov) \u00b7 "
              "Nvidia CEO resigns (12 Nov) \u00b7 Peru 6.7 quake (20 Nov) \u00b7 "
              "Alcaraz wins ATP Finals (22 Nov) \u00b7 COP31 collapse (22 Nov "
              "\u2014 only the fallout is Monday\u2019s news).")

PINS = [(1, -122.0, 37.4), (2, 20.1, 32.1), (3, 30.7, 36.9),
        (4, 30.8, 50.9), (5, 32.5, 15.6), (6, 106.1, -6.2),
        (7, 4.35, 50.85), (8, 51.4, 35.7), (9, -0.1, 51.5),
        (10, -77.0, 38.9), (11, -74.0, 40.7), (12, -73.2, 41.3),
        (13, 77.2, 28.6)]


def rule(cv, y, color=INK, width=2):
    cv.fill_rect(24, y, W - 48, width, color)


def draw():
    cv = Canvas(W, H, PAPER)
    # top strip
    draw_text(cv, 24, 24, "THE WORLD IN ONE DAY", 12, RED, weight=2.0)
    draw_text(cv, W - 24, 24,
              "35 STORIES \u00b7 8 REGIONS \u00b7 EVERY ONE DATED MONDAY 23 NOVEMBER 2026",
              10, INK, weight=1.4, align="right")
    rule(cv, 30, INK, 2)
    # masthead
    draw_text(cv, W / 2, 96, "Monday 23 November 2026", 62, INK, weight=1.5,
              align="center", sx=0.58)
    draw_text(cv, W / 2, 122, SUBHEAD, 14, RED, weight=1.3, align="center")
    rule(cv, 128, INK, 3)
    # numbers band
    bw = (W - 48) / 6.0
    for i, (big, label) in enumerate(NUMBERS):
        cx = 24 + bw * (i + 0.5)
        draw_text(cv, cx, 164, big, 26, RED, weight=2.0, align="center",
                  sx=0.8)
        draw_text(cv, cx, 180, label, 9, INK, weight=1.3, align="center")
        if i:
            cv.fill_rect(24 + int(bw * i), 136, 1, 48, LIGHT)
    rule(cv, 186, INK, 1)
    # region chips
    nchip = len(CHIPS)
    cw = (W - 48 - (nchip - 1) * 4) / float(nchip)
    for i, (name, n) in enumerate(CHIPS):
        x = 24 + i * (cw + 4)
        cv.fill_rect(x, 192, cw, 18, CHIP_COLORS[i % len(CHIP_COLORS)])
        draw_text(cv, x + cw / 2, 206, "%s %d" % (name, n), 9, WHITE,
                  weight=1.6, align="center")
    # UTC strip
    cv.fill_rect(24, 216, W - 48, 16, NAVY)
    draw_text(cv, W / 2, 229, UTC_STRIP, 9.5, WHITE, weight=1.3,
              align="center")
    # lead cards
    lw = (W - 48 - 2 * 12) / 3.0
    for i, lead in enumerate(LEADS):
        x = 24 + i * (lw + 12)
        lead["scene"](cv, x, 238, lw, 104)
        cv.fill_rect(x, 342, lw, 2, INK)
        tag = "%d \u00b7 %s \u00b7 %s" % (lead["num"], lead["place"], lead["beat"])
        draw_text(cv, x, 356, tag, 10, RED, weight=2.0)
        tw = text_width(tag, 10, 2.0)
        cv.fill_rect(x + tw + 6, 347, 54, 13, RED)
        draw_text(cv, x + tw + 33, 357, lead["tag"], 9, WHITE, weight=2.0,
                  align="center")
        y = 380
        for ln in wrap_text(lead["head"], 16, lw, 2.0)[:3]:
            draw_text(cv, x, y, ln, 16, INK, weight=2.0)
            y += 19.5
        y += 4
        y = draw_para(cv, x, y, lead["body"], 10.5, INK, lw, leading=1.35)
        draw_text(cv, x, y + 8, lead["src"], 8.5, GREY, weight=1.2)
    # the day in ten
    rule(cv, 522, INK, 2)
    draw_text(cv, 24, 538, "THE DAY IN TEN", 13, INK, weight=2.0)
    draw_text(cv, W - 24, 538, "THE STORIES THAT MOVED THE WORLD TODAY", 9,
              GREY, weight=1.3, align="right")
    fw = (W - 48 - 4 * 8) / 5.0
    for idx, feat in enumerate(FEATURES):
        col, row = idx % 5, idx // 5
        x = 24 + col * (fw + 8)
        y0 = 544 + row * 127
        feat["scene"](cv, x, y0, fw, 40)
        y = y0 + 50
        draw_text(cv, x, y, "%d \u00b7 %s \u00b7 %s" % (feat["num"], feat["place"],
                                                       feat["beat"]),
                  8, RED, weight=2.0)
        y += 11
        for ln in wrap_text(feat["head"], 11, fw, 2.0)[:2]:
            draw_text(cv, x, y, ln, 11, INK, weight=2.0)
            y += 12.5
        y += 1
        for ln in wrap_text(feat["body"], 8.5, fw, 1.0)[:3]:
            draw_text(cv, x, y, ln, 8.5, INK, weight=1.0)
            y += 10.5
    # map + also
    rule(cv, 800, INK, 2)
    draw_text(cv, 24, 816, "WHERE IT HAPPENED \u2014 PINS MATCH STORY NUMBERS",
              10, INK, weight=2.0)
    draw_map(cv, 24, 822, 300, 112, PINS)
    draw_text(cv, 24, 946, "Red numbers mark stories 1\u201313 on the map.",
              8.5, GREY, weight=1.2)
    ax = 348
    draw_text(cv, ax, 816, "ALSO ON MONDAY 23 NOVEMBER \u2014 22 MORE STORIES",
              12, INK, weight=2.0)
    colw = (W - 24 - ax - 12) / 2.0
    for j, (num, place, text, src) in enumerate(ALSO):
        col, row = j % 2, j // 2
        x = ax + col * (colw + 12)
        y = 834 + row * 12
        line = "%d %s \u2014 %s (%s)" % (num, place, text, src)
        draw_text(cv, x, y, line, 8, INK, weight=1.0)
    # date check
    cv.fill_rect(24, 958, W - 48, 2, RED)
    cv.fill_rect(24, 958, 2, 34, RED)
    cv.fill_rect(W - 26, 958, 2, 34, RED)
    cv.fill_rect(24, 990, W - 48, 2, RED)
    y = 970
    for ln in wrap_text(DATE_CHECK, 8.5, W - 48 - 16, 1.2)[:2]:
        draw_text(cv, 32, y, ln, 8.5, DARKRED, weight=1.2)
        y += 12
    # footer
    draw_text(cv, W / 2, 1006,
              "Every story here happened, or was first reported, on Monday 23 "
              "November 2026 in at least one time zone. Claims are attributed, "
              "not stated as fact.", 8.5, INK, weight=1.2, align="center")
    draw_text(cv, W / 2, 1019,
              "Sources: Reuters \u00b7 AP \u00b7 BBC \u00b7 Al Jazeera \u00b7 The "
              "Guardian \u00b7 CNN \u00b7 WSJ \u00b7 UKMTO \u00b7 Detiknews. Original "
              "vector drawings.", 8.5, INK, weight=1.2, align="center")
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/tmp/out")
    os.makedirs(out_dir, exist_ok=True)
    cv = draw()
    write_png(os.path.join(out_dir, "entry.png"), bytes(cv.px), W, H)


if __name__ == "__main__":
    main()
