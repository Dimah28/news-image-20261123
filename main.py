#!/usr/bin/env python3
"""The World in One Day -- Monday 23 November 2026 (news-image-20261123).

One 1024x1024 newspaper front page, drawn from scratch with nothing but
the Python standard library. The program paints 35 verified stories from
Monday 23 November 2026 -- three illustrated leads, ten feature cards, a
pinned world map, 22 one-line stories and a date-check strip -- into a
single PNG and writes it to $MAKEFUN_OUTPUT_DIR/entry.png.

Everything is deterministic: no clock, no randomness, no network, no
system fonts, no Pillow. Lettering comes from a small vector font defined
below as integer polylines on a 5-wide grid. Running the program twice
produces byte-identical output.
"""

import math
import os
import struct
import zlib

PAGE_W = 1024
PAGE_H = 1024


def png_bytes(rgb, width, height):
    """Encode raw RGB bytes as a PNG file."""
    def block(kind, payload):
        head = struct.pack(">I", len(payload)) + kind + payload
        return head + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    scanlines = bytearray()
    row_len = width * 3
    for row in range(height):
        scanlines.append(0)
        scanlines += rgb[row * row_len:(row + 1) * row_len]
    body = zlib.compress(bytes(scanlines), 6)
    return (b"\x89PNG\r\n\x1a\n" + block(b"IHDR", header)
            + block(b"IDAT", body) + block(b"IEND", b""))


class Page:
    """A flat RGB canvas with a few drawing primitives."""

    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.buf = bytearray(background) * (width * height)

    def px(self, x, y, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            at = (y * self.width + x) * 3
            self.buf[at:at + 3] = colour

    def box(self, x, y, w, h, colour):
        left = max(0, int(x))
        top = max(0, int(y))
        right = min(self.width, int(x + w))
        bottom = min(self.height, int(y + h))
        if right <= left or bottom <= top:
            return
        strip = bytes(colour) * (right - left)
        for yy in range(top, bottom):
            at = (yy * self.width + left) * 3
            self.buf[at:at + len(strip)] = strip

    def dot(self, cx, cy, radius, colour):
        radius = int(radius)
        if radius <= 0:
            self.px(int(cx), int(cy), colour)
            return
        for dy in range(-radius, radius + 1):
            half = int(math.sqrt(radius * radius - dy * dy))
            y = int(cy) + dy
            if 0 <= y < self.height:
                left = max(0, int(cx) - half)
                right = min(self.width - 1, int(cx) + half)
                at = (y * self.width + left) * 3
                self.buf[at:(y * self.width + right + 1) * 3] = \
                    bytes(colour) * (right - left + 1)

    def seg(self, x0, y0, x1, y1, colour, thick=1):
        """Bresenham line, thickened by stamping dots along it."""
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for n in range(steps + 1):
            f = n / steps
            self.dot(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f,
                     max(0.5, thick / 2.0), colour)

    def path(self, points, colour, thick=1, shut=False):
        if len(points) == 1:
            self.dot(points[0][0], points[0][1], max(0.6, thick / 2.0),
                     colour)
            return
        for first, second in zip(points, points[1:]):
            self.seg(first[0], first[1], second[0], second[1], colour,
                     thick)
        if shut and len(points) > 2:
            self.seg(points[-1][0], points[-1][1], points[0][0],
                     points[0][1], colour, thick)

    def fill(self, points, colour):
        """Scanline fill for a simple polygon."""
        if len(points) < 3:
            return
        top = max(0, int(math.floor(min(p[1] for p in points))))
        bottom = min(self.height,
                     int(math.ceil(max(p[1] for p in points))))
        count = len(points)
        for y in range(top, bottom):
            cuts = []
            for k in range(count):
                ax, ay = points[k]
                bx, by = points[(k + 1) % count]
                if (ay <= y < by) or (by <= y < ay):
                    cuts.append(ax + (y - ay) / (by - ay) * (bx - ax))
            cuts.sort()
            for j in range(0, len(cuts) - 1, 2):
                left = max(0, int(math.ceil(cuts[j])))
                right = min(self.width - 1, int(math.floor(cuts[j + 1])))
                if right >= left:
                    at = (y * self.width + left) * 3
                    self.buf[at:(y * self.width + right + 1) * 3] = \
                        bytes(colour) * (right - left + 1)

    def oval(self, cx, cy, rx, ry, colour):
        for dy in range(-int(ry), int(ry) + 1):
            if ry == 0:
                continue
            frac = 1.0 - (dy * dy) / (ry * ry)
            if frac < 0:
                continue
            half = int(rx * math.sqrt(frac))
            y = int(cy) + dy
            if 0 <= y < self.height:
                left = max(0, int(cx) - half)
                right = min(self.width - 1, int(cx) + half)
                at = (y * self.width + left) * 3
                self.buf[at:(y * self.width + right + 1) * 3] = \
                    bytes(colour) * (right - left + 1)

    def ring(self, cx, cy, radius, colour, thick=2):
        turns = max(12, int(2 * math.pi * radius))
        for n in range(turns):
            ang = 2 * math.pi * n / turns
            self.dot(cx + radius * math.cos(ang),
                     cy + radius * math.sin(ang),
                     max(0.6, thick / 2.0), colour)

    def arc(self, cx, cy, radius, start, stop, colour, thick=2):
        turns = max(4, int(abs(stop - start) * radius))
        for n in range(turns + 1):
            ang = start + (stop - start) * n / turns
            self.dot(cx + radius * math.cos(ang),
                     cy + radius * math.sin(ang),
                     max(0.6, thick / 2.0), colour)


# ------------------------------------------------------------------ the font
# Vector strokes on a 5-wide, 9-tall integer grid: cap top y=0, baseline
# y=6, descender bottom y=8. A glyph is a list of strokes; a stroke is a
# list of (x, y) points. One-point strokes draw a dot.
FONT = {
    "A": [[(0, 6), (2, 0), (4, 6)], [(1, 4), (3, 4)]],
    "B": [[(0, 0), (0, 6)], [(0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)],
          [(0, 3), (3, 3), (4, 4), (4, 5), (3, 6), (0, 6)]],
    "C": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5)]],
    "D": [[(0, 0), (0, 6)], [(0, 0), (3, 0), (4, 1), (4, 5), (3, 6), (0, 6)]],
    "E": [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    "F": [[(0, 6), (0, 0), (4, 0)], [(0, 3), (3, 3)]],
    "G": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5),
           (4, 3), (3, 3)]],
    "H": [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "I": [[(2, 0), (2, 6)], [(1, 0), (3, 0)], [(1, 6), (3, 6)]],
    "J": [[(4, 0), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "K": [[(0, 0), (0, 6)], [(4, 0), (0, 3)], [(1, 3), (4, 6)]],
    "L": [[(0, 0), (0, 6), (4, 6)]],
    "M": [[(0, 6), (0, 0), (2, 3), (4, 0), (4, 6)]],
    "N": [[(0, 6), (0, 0), (4, 6), (4, 0)]],
    "O": [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1),
           (1, 0)]],
    "P": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)]],
    "Q": [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1),
           (1, 0)], [(3, 4), (4, 6)]],
    "R": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)],
          [(2, 3), (4, 6)]],
    "S": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 2), (1, 3), (3, 3), (4, 4),
           (4, 5), (3, 6), (1, 6), (0, 5)]],
    "T": [[(0, 0), (4, 0)], [(2, 0), (2, 6)]],
    "U": [[(0, 0), (0, 5), (1, 6), (3, 6), (4, 5), (4, 0)]],
    "V": [[(0, 0), (2, 6), (4, 0)]],
    "W": [[(0, 0), (1, 6), (2, 2), (3, 6), (4, 0)]],
    "X": [[(0, 0), (4, 6)], [(4, 0), (0, 6)]],
    "Y": [[(0, 0), (2, 3), (4, 0)], [(2, 3), (2, 6)]],
    "Z": [[(0, 0), (4, 0), (0, 6), (4, 6)]],
    "a": [[(1, 2), (3, 2), (4, 3), (4, 5), (3, 6), (1, 6), (0, 5), (0, 3),
           (1, 2)], [(4, 2), (4, 6)]],
    "b": [[(0, 0), (0, 6)],
          [(0, 3), (1, 2), (3, 2), (4, 3), (4, 5), (3, 6), (0, 6)]],
    "c": [[(4, 3), (3, 2), (1, 2), (0, 3), (0, 5), (1, 6), (3, 6), (4, 5)]],
    "d": [[(4, 0), (4, 6)],
          [(1, 2), (3, 2), (4, 3), (4, 5), (3, 6), (1, 6), (0, 5), (0, 3),
           (1, 2)]],
    "e": [[(4, 4), (3, 2), (1, 2), (0, 3), (0, 5), (1, 6), (3, 6), (4, 5)],
          [(0, 4), (4, 4)]],
    "f": [[(3, 6), (3, 1), (2, 0), (1, 0)], [(0, 2), (4, 2)]],
    "g": [[(1, 2), (3, 2), (4, 3), (4, 5), (3, 6), (1, 6), (0, 5), (0, 3),
           (1, 2)], [(4, 5), (4, 7), (3, 8), (1, 8)]],
    "h": [[(0, 0), (0, 6)], [(0, 4), (1, 2), (3, 2), (4, 3), (4, 6)]],
    "i": [[(2, 2), (2, 6)], [(2, 0)]],
    "j": [[(3, 2), (3, 7), (2, 8), (1, 8)], [(3, 0)]],
    "k": [[(0, 0), (0, 6)], [(4, 2), (0, 4)], [(1, 4), (4, 6)]],
    "l": [[(2, 0), (2, 6)]],
    "m": [[(0, 6), (0, 2), (1, 2), (2, 3), (2, 6)],
          [(2, 3), (3, 2), (4, 2), (4, 6)]],
    "n": [[(0, 6), (0, 2)], [(0, 4), (1, 2), (3, 2), (4, 3), (4, 6)]],
    "o": [[(1, 2), (3, 2), (4, 3), (4, 5), (3, 6), (1, 6), (0, 5), (0, 3),
           (1, 2)]],
    "p": [[(0, 2), (0, 8)],
          [(0, 4), (1, 2), (3, 2), (4, 3), (4, 5), (3, 6), (0, 6)]],
    "q": [[(4, 2), (4, 8)],
          [(1, 2), (3, 2), (4, 3), (4, 5), (3, 6), (1, 6), (0, 5), (0, 3),
           (1, 2)]],
    "r": [[(0, 6), (0, 2)], [(0, 4), (1, 2), (3, 2), (4, 3)]],
    "s": [[(4, 2), (3, 2), (1, 2), (0, 3), (1, 4), (3, 4), (4, 5), (3, 6),
           (1, 6), (0, 5)]],
    "t": [[(2, 0), (2, 5), (1, 6), (0, 6)], [(0, 2), (4, 2)]],
    "u": [[(0, 2), (0, 5), (1, 6), (3, 6), (4, 5), (4, 2)]],
    "v": [[(0, 2), (2, 6), (4, 2)]],
    "w": [[(0, 2), (1, 6), (2, 3), (3, 6), (4, 2)]],
    "x": [[(0, 2), (4, 6)], [(4, 2), (0, 6)]],
    "y": [[(0, 2), (2, 5), (4, 2)], [(2, 5), (2, 7), (1, 8), (0, 8)]],
    "z": [[(0, 2), (4, 2), (0, 6), (4, 6)]],
    "0": [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1),
           (1, 0)], [(1, 4), (3, 2)]],
    "1": [[(2, 0), (2, 6)], [(1, 1), (2, 0)], [(1, 6), (3, 6)]],
    "2": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (2, 4), (0, 6), (4, 6)]],
    "3": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (4, 3), (4, 5),
           (3, 6), (1, 6), (0, 5)]],
    "4": [[(4, 0), (4, 6)], [(0, 4), (4, 4)], [(0, 4), (4, 0)]],
    "5": [[(4, 0), (0, 0), (0, 2), (3, 2), (4, 3), (4, 5), (3, 6), (1, 6),
           (0, 5)]],
    "6": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5),
           (4, 3), (3, 2), (1, 2), (0, 3)]],
    "7": [[(0, 0), (4, 0), (2, 6)]],
    "8": [[(1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (1, 3), (0, 2), (0, 1),
           (1, 0)], [(1, 3), (0, 4), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4),
                     (3, 3)]],
    "9": [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 1), (3, 0), (1, 0), (0, 1),
           (0, 2), (1, 3), (3, 3), (4, 2)]],
    ".": [[(2, 6)]],
    ",": [[(2, 6), (2, 7), (1, 8)]],
    ":": [[(2, 2)], [(2, 5)]],
    ";": [[(2, 2)], [(2, 5), (2, 6), (1, 7)]],
    "!": [[(2, 0), (2, 4)], [(2, 6)]],
    "?": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (2, 4)], [(2, 6)]],
    "-": [[(0, 3), (4, 3)]],
    "\u2013": [[(0, 3), (4, 3)]],
    "\u2014": [[(0, 3), (4, 3)]],
    "'": [[(2, 0), (1, 2)]],
    "\u2019": [[(2, 0), (1, 2)]],
    '"': [[(1, 0), (1, 1)], [(3, 0), (3, 1)]],
    "\u201c": [[(1, 0), (1, 1)], [(3, 0), (3, 1)]],
    "\u201d": [[(1, 0), (1, 1)], [(3, 0), (3, 1)]],
    "(": [[(3, 0), (1, 1), (1, 5), (3, 6)]],
    ")": [[(1, 0), (3, 1), (3, 5), (1, 6)]],
    "[": [[(3, 0), (1, 0), (1, 6), (3, 6)]],
    "]": [[(1, 0), (3, 0), (3, 6), (1, 6)]],
    "/": [[(4, 0), (0, 6)]],
    "%": [[(0, 1), (1, 1), (1, 2), (0, 2)], [(4, 0), (0, 6)],
          [(3, 4), (4, 4), (4, 5), (3, 5)]],
    "+": [[(2, 1), (2, 5)], [(0, 3), (4, 3)]],
    "=": [[(0, 2), (4, 2)], [(0, 4), (4, 4)]],
    "$": [[(2, -1), (2, 7)],
          [(4, 1), (3, 0), (1, 0), (0, 1), (0, 2), (1, 3), (3, 3), (4, 4),
           (4, 5), (3, 6), (1, 6), (0, 5)]],
    "\u00b7": [[(2, 3)]],
    "\u2022": ["\u25cf"],
    "~": [[(0, 3), (1, 2), (2, 3), (3, 2), (4, 3)]],
    "_": [[(0, 6), (4, 6)]],
    "\u00b0": [[(1, 0), (2, 0), (3, 1), (3, 2), (2, 3), (1, 3), (0, 2),
               (0, 1), (1, 0)]],
    "\u00d7": [[(1, 1), (3, 5)], [(3, 1), (1, 5)]],
    "\u2192": [[(0, 3), (4, 3)], [(3, 1), (4, 3), (3, 5)]],
    "<": [[(4, 1), (1, 3), (4, 5)]],
    ">": [[(1, 1), (4, 3), (1, 5)]],
    "#": [[(1, 0), (1, 6)], [(3, 0), (3, 6)], [(0, 2), (4, 2)],
          [(0, 4), (4, 4)]],
    "&": [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 4), (1, 3), (3, 3), (4, 4),
           (4, 5), (3, 6), (2, 6), (1, 5), (1, 2), (2, 0), (3, 0), (4, 1)]],
    "\u00e9": [[(4, 4), (3, 2), (1, 2), (0, 3), (0, 5), (1, 6), (3, 6),
               (4, 5)], [(0, 4), (4, 4)], [(2, -1), (3, 0)]],
    "\u00a3": [[(3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6)],
              [(0, 2), (3, 2)]],
}

THIN = set("iljtfI!'.:;,|")
FAT = set("mwMW")
STEP = {}
for _letter in FONT:
    STEP[_letter] = 3.0 if _letter in THIN else (6.5 if _letter in FAT else 5.0)
STEP[" "] = 3.5
STEP["\u2014"] = 6.0
STEP["\u2013"] = 4.5
STEP["\u00b7"] = 3.5
STEP["\u2022"] = 5.0

_mask_cache = {}


def _mask(letter, size, bold, stretch):
    """Rasterise one glyph to a small mask, cached per size/weight."""
    tag = (letter, size, bold, stretch)
    found = _mask_cache.get(tag)
    if found is not None:
        return found
    unit = size / 6.0
    advance = STEP.get(letter, 5.0) * unit * stretch
    wide = max(1, int(math.ceil(advance)) + 2)
    tall = max(1, int(math.ceil(9.6 * unit)) + 2)
    mask = bytearray(wide * tall)
    strokes = FONT.get(letter)
    if strokes:
        scratch = Page(wide, tall, b"\x00\x00\x00")
        for stroke in strokes:
            if stroke == "\u25cf":
                scratch.dot(wide / 2.0, 3.4 * unit, 1.5 * unit,
                            b"\xff\xff\xff")
                continue
            pts = [(gx * unit * stretch + 1.0, gy * unit + 1.6)
                   for gx, gy in stroke]
            scratch.path(pts, b"\xff\xff\xff",
                         max(1.0, bold * unit * 0.30))
        if bold > 1.6:
            for stroke in strokes:
                if stroke == "\u25cf":
                    continue
                pts = [(gx * unit * stretch + 2.2, gy * unit + 1.6)
                       for gx, gy in stroke]
                scratch.path(pts, b"\xff\xff\xff",
                             max(1.0, bold * unit * 0.30))
        for n in range(wide * tall):
            if scratch.buf[n * 3]:
                mask[n] = 255
    made = (wide, tall, mask, advance)
    _mask_cache[tag] = made
    return made


def measure(text, size, bold=1.0, stretch=0.72):
    unit = size / 6.0
    return sum(STEP.get(ch, 5.0) * unit * stretch for ch in text)


def put_text(page, x, y, text, size, colour, bold=1.0, align="left",
             stretch=0.72):
    """Paint text; (x, y) is the baseline origin (or centre/right)."""
    if align != "left":
        full = measure(text, size, bold, stretch)
        if align == "center":
            x -= full / 2.0
        elif align == "right":
            x -= full
    unit = size / 6.0
    cursor = x
    for ch in text:
        if ch == " ":
            cursor += STEP[" "] * unit * stretch
            continue
        wide, tall, mask, advance = _mask(ch, size, bold, stretch)
        top = int(round(y - 6 * unit - 1.6))
        left = int(round(cursor - 1.0))
        for row in range(tall):
            yy = top + row
            if yy < 0 or yy >= page.height:
                continue
            base = row * wide
            for col in range(wide):
                if mask[base + col]:
                    xx = left + col
                    if 0 <= xx < page.width:
                        at = (yy * page.width + xx) * 3
                        page.buf[at:at + 3] = colour
        cursor += advance
    return cursor


def split_lines(text, size, limit, bold=1.0, stretch=0.72):
    """Greedy word wrap into lines no wider than limit."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = word if not current else current + " " + word
        if measure(trial, size, bold, stretch) <= limit or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def put_para(page, x, y, text, size, colour, limit, bold=1.0, leading=1.45,
             stretch=0.72):
    for line in split_lines(text, size, limit, bold, stretch):
        put_text(page, x, y, line, size, colour, bold, stretch=stretch)
        y += size * leading
    return y


# ------------------------------------------------------------------ palette
NEWS = bytes((245, 240, 227))
INK = bytes((26, 26, 26))
RUBY = bytes((164, 31, 31))
WINERED = bytes((122, 18, 18))
NAVY = bytes((28, 48, 80))
TEAL = bytes((18, 92, 86))
OCHRE = bytes((176, 124, 24))
ASH = bytes((110, 104, 90))
PALE = bytes((232, 226, 210))
SNOW = bytes((255, 255, 255))
SKY = bytes((176, 205, 225))
MIDNIGHT = bytes((16, 24, 48))
AMBER = bytes((232, 158, 44))
EMBER = bytes((232, 98, 24))
LEAF = bytes((46, 110, 58))
LIME = bytes((118, 185, 0))

BAND_COLOURS = [NAVY, WINERED, TEAL, OCHRE, bytes((96, 48, 96)),
                bytes((60, 90, 140)), ASH, bytes((40, 90, 60))]


def spark(page, cx, cy, radius, colour):
    for k in range(8):
        ang = math.pi * k / 4
        page.seg(cx - radius * math.cos(ang), cy - radius * math.sin(ang),
                 cx + radius * math.cos(ang), cy + radius * math.sin(ang),
                 colour, 1)


def ripple(page, x, y, width, colour, height=3, stride=14):
    pts = []
    for xx in range(int(x), int(x + width) + 1, 4):
        pts.append((xx, y + height * math.sin(xx / stride)))
    page.path(pts, colour, 1.5)


def tongue(page, cx, cy, size, colour=EMBER):
    page.fill([(cx - 0.55 * size, cy), (cx, cy - 1.5 * size),
               (cx + 0.4 * size, cy - 0.5 * size), (cx + 0.7 * size, cy),
               (cx + 0.2 * size, cy + 0.5 * size),
               (cx - 0.3 * size, cy + 0.5 * size)], colour)
    page.fill([(cx - 0.25 * size, cy), (cx, cy - 0.7 * size),
               (cx + 0.25 * size, cy), (cx, cy + 0.3 * size)], AMBER)


def puff(page, cx, cy, colour=ASH):
    for k, rad in enumerate((3, 4, 5, 6)):
        page.dot(cx + (k % 2) * 4 - 2, cy - k * 7, rad, colour)


# ------------------------------------------------------------------ lead art
def art_nvidia(page, x, y, w, h):
    """Green chip on black, chart climbing, +31% in lime."""
    page.box(x, y, w, h, bytes((16, 24, 16)))
    page.box(x, y + h * 0.72, w, h * 0.28, bytes((28, 44, 28)))
    cx, cy = x + w * 0.24, y + h * 0.42
    s = h * 0.30
    page.box(cx - s, cy - s * 0.75, s * 2, s * 1.5, bytes((24, 40, 24)))
    for k in range(3):
        page.box(cx - s - 8, cy - s * 0.5 + k * s * 0.5, 8, 4, LIME)
        page.box(cx + s, cy - s * 0.5 + k * s * 0.5, 8, 4, LIME)
        page.box(cx - s * 0.5 + k * s * 0.5, cy - s * 0.75 - 8, 4, 8, LIME)
        page.box(cx - s * 0.5 + k * s * 0.5, cy + s * 0.75, 4, 8, LIME)
    page.box(cx - s * 0.45, cy - s * 0.32, s * 0.9, s * 0.64, LIME)
    put_text(page, cx, cy + 5, "NV", 16, INK, bold=2.0, align="center")
    page.path([(x + w * 0.44, y + h * 0.62), (x + w * 0.55, y + h * 0.58),
               (x + w * 0.64, y + h * 0.64), (x + w * 0.72, y + h * 0.50),
               (x + w * 0.82, y + h * 0.52), (x + w * 0.93, y + h * 0.22)],
              LIME, 3)
    page.fill([(x + w * 0.93, y + h * 0.22), (x + w * 0.86, y + h * 0.24),
               (x + w * 0.92, y + h * 0.32)], LIME)
    put_text(page, x + w * 0.56, y + h * 0.16, "+31%", 22, LIME, bold=2.0)


def art_merkury(page, x, y, w, h):
    """Dusk sea: a listing warship, smoke, drones skimming the water."""
    page.box(x, y, w, h, bytes((214, 176, 130)))
    page.box(x, y + h * 0.55, w, h * 0.45, bytes((30, 68, 104)))
    ripple(page, x, y + h * 0.62, w, bytes((120, 170, 210)), 3, 12)
    ripple(page, x, y + h * 0.80, w, bytes((90, 140, 185)), 3, 10)
    page.dot(x + w * 0.86, y + h * 0.18, h * 0.11, bytes((240, 220, 180)))
    page.fill([(x + w * 0.10, y + h * 0.46), (x + w * 0.86, y + h * 0.58),
               (x + w * 0.78, y + h * 0.72), (x + w * 0.18, y + h * 0.62)],
              bytes((96, 96, 100)))
    page.box(x + w * 0.30, y + h * 0.36, w * 0.26, h * 0.12,
             bytes((200, 200, 196)))
    page.box(x + w * 0.40, y + h * 0.26, w * 0.05, h * 0.12,
             bytes((60, 60, 60)))
    page.fill([(x + w * 0.55, y + h * 0.40), (x + w * 0.58, y + h * 0.44),
               (x + w * 0.55, y + h * 0.50), (x + w * 0.70, y + h * 0.44)],
              bytes((200, 40, 40)))
    tongue(page, x + w * 0.60, y + h * 0.34, 10)
    puff(page, x + w * 0.60, y + h * 0.16)
    for dx in (0.14, 0.34, 0.52):
        bx, by = x + w * dx, y + h * 0.78
        page.fill([(bx, by), (bx + 18, by), (bx + 14, by + 6),
                   (bx + 4, by + 6)], bytes((220, 220, 215)))
        page.seg(bx, by + 8, bx - 16, by + 12, SNOW, 1.5)
        page.seg(bx, by + 8, bx - 12, by + 14, SNOW, 1.5)
    page.dot(x + w * 0.72, y + h * 0.14, 3, INK)
    page.seg(x + w * 0.66, y + h * 0.14, x + w * 0.78, y + h * 0.14, INK, 2)


def art_cop31(page, x, y, w, h):
    """Dawn over Antalya: sun, skyline, a globe, empty chairs."""
    page.box(x, y, w, h, bytes((252, 226, 180)))
    page.box(x, y, w, h * 0.42, bytes((250, 196, 130)))
    page.dot(x + w * 0.74, y + h * 0.30, h * 0.16, AMBER)
    page.ring(x + w * 0.74, y + h * 0.30, h * 0.22, AMBER, 2)
    page.box(x, y + h * 0.62, w, h * 0.38, bytes((58, 52, 66)))
    for k, tall in enumerate((0.22, 0.34, 0.16, 0.30, 0.20)):
        bx = x + w * (0.04 + k * 0.19)
        page.box(bx, y + h * 0.62 - h * tall, w * 0.13, h * (tall + 0.38),
                 bytes((38, 34, 46)))
        for wy in range(3):
            page.box(bx + 4, y + h * 0.62 - h * tall + 5 + wy * 8, 3, 4,
                     AMBER)
    cx, cy, rad = x + w * 0.24, y + h * 0.34, h * 0.24
    page.dot(cx, cy, rad, bytes((94, 140, 190)))
    page.oval(cx, cy, rad * 0.45, rad, bytes((46, 110, 58)))
    page.seg(cx - rad, cy, cx + rad, cy, bytes((210, 225, 240)), 1.5)
    page.seg(cx, cy - rad, cx, cy + rad, bytes((210, 225, 240)), 1.5)
    for k in range(4):
        bx = x + w * (0.55 + k * 0.11)
        page.box(bx, y + h * 0.80, w * 0.07, h * 0.10,
                 bytes((120, 110, 100)))
        page.box(bx, y + h * 0.72, w * 0.07, h * 0.08,
                 bytes((120, 110, 100)))


# ---------------------------------------------------------------- feature art
def art_collapse(page, x, y, w, h):
    page.box(x, y, w, h, bytes((210, 200, 180)))
    page.box(x + w * 0.12, y + h * 0.30, w * 0.60, h * 0.55,
             bytes((150, 140, 126)))
    for i in range(3):
        for j in range(2):
            page.box(x + w * (0.18 + i * 0.19), y + h * (0.38 + j * 0.24),
                     w * 0.10, h * 0.12, bytes((40, 40, 46)))
    page.fill([(x + w * 0.72, y + h * 0.30), (x + w * 0.86, y + h * 0.42),
               (x + w * 0.72, y + h * 0.55), (x + w * 0.60, y + h * 0.45)],
              bytes((120, 110, 96)))
    page.seg(x + w * 0.60, y + h * 0.45, x + w * 0.86, y + h * 0.42, INK, 2)
    puff(page, x + w * 0.76, y + h * 0.22)
    page.fill([(x + w * 0.10, y + h * 0.85), (x + w * 0.30, y + h * 0.85),
               (x + w * 0.26, y + h * 0.78), (x + w * 0.14, y + h * 0.78)],
              bytes((110, 100, 86)))


def art_khartoum(page, x, y, w, h):
    page.box(x, y, w, h, bytes((238, 214, 170)))
    page.box(x, y + h * 0.60, w, h * 0.40, bytes((120, 96, 66)))
    for k, tall in enumerate((0.24, 0.36, 0.18, 0.30)):
        bx = x + w * (0.06 + k * 0.23)
        page.box(bx, y + h * 0.60 - h * tall, w * 0.16, h * (tall + 0.40),
                 bytes((90, 74, 54)))
    page.dot(x + w * 0.78, y + h * 0.24, 2.5, INK)
    page.seg(x + w * 0.72, y + h * 0.24, x + w * 0.84, y + h * 0.24, INK, 2)
    page.seg(x + w * 0.78, y + h * 0.24, x + w * 0.70, y + h * 0.42, RUBY, 1.5)
    tongue(page, x + w * 0.42, y + h * 0.52, 8)
    puff(page, x + w * 0.42, y + h * 0.34)


def art_factory(page, x, y, w, h):
    page.box(x, y, w, h, bytes((238, 232, 216)))
    page.box(x + w * 0.12, y + h * 0.46, w * 0.76, h * 0.34,
             bytes((150, 96, 80)))
    page.fill([(x + w * 0.12, y + h * 0.46), (x + w * 0.30, y + h * 0.28),
               (x + w * 0.48, y + h * 0.46), (x + w * 0.66, y + h * 0.28),
               (x + w * 0.84, y + h * 0.46)], bytes((120, 70, 58)))
    page.box(x + w * 0.78, y + h * 0.18, w * 0.07, h * 0.30,
             bytes((110, 104, 96)))
    tongue(page, x + w * 0.42, y + h * 0.34, 10)
    puff(page, x + w * 0.80, y + h * 0.10)
    for k in range(3):
        page.box(x + w * (0.20 + k * 0.20), y + h * 0.56, w * 0.10,
                 h * 0.12, AMBER)


def art_plane(page, x, y, w, h):
    page.box(x, y, w, h, SKY)
    page.box(x + w * 0.10, y + h * 0.66, w * 0.80, h * 0.06,
             bytes((90, 90, 96)))
    page.oval(x + w * 0.50, y + h * 0.42, w * 0.34, h * 0.14, SNOW)
    page.fill([(x + w * 0.78, y + h * 0.42), (x + w * 0.92, y + h * 0.34),
               (x + w * 0.92, y + h * 0.50)], SNOW)
    page.fill([(x + w * 0.44, y + h * 0.34), (x + w * 0.52, y + h * 0.20),
               (x + w * 0.58, y + h * 0.34)], bytes((180, 30, 30)))
    page.fill([(x + w * 0.44, y + h * 0.50), (x + w * 0.52, y + h * 0.64),
               (x + w * 0.58, y + h * 0.50)], bytes((180, 30, 30)))
    for k in range(4):
        page.box(x + w * (0.30 + k * 0.10), y + h * 0.38, w * 0.04,
                 h * 0.06, NAVY)
    page.seg(x + w * 0.08, y + h * 0.42, x + w * 0.16, y + h * 0.42, RUBY, 3)


def art_tanker(page, x, y, w, h):
    page.box(x, y, w, h, bytes((250, 200, 140)))
    page.box(x, y + h * 0.60, w, h * 0.40, bytes((38, 90, 128)))
    ripple(page, x, y + h * 0.68, w, SNOW, 2, 10)
    page.fill([(x + w * 0.12, y + h * 0.50), (x + w * 0.88, y + h * 0.50),
               (x + w * 0.80, y + h * 0.70), (x + w * 0.20, y + h * 0.70)],
              bytes((40, 40, 44)))
    page.box(x + w * 0.30, y + h * 0.32, w * 0.34, h * 0.18,
             bytes((220, 220, 215)))
    tongue(page, x + w * 0.62, y + h * 0.34, 9)
    puff(page, x + w * 0.62, y + h * 0.18)
    page.seg(x + w * 0.18, y + h * 0.20, x + w * 0.30, y + h * 0.34, RUBY, 2)
    page.dot(x + w * 0.16, y + h * 0.18, 3, RUBY)


def art_stadium(page, x, y, w, h):
    page.box(x, y, w, h, bytes((214, 232, 196)))
    page.box(x, y + h * 0.68, w, h * 0.32, bytes((90, 150, 70)))
    page.oval(x + w * 0.50, y + h * 0.52, w * 0.42, h * 0.18,
              bytes((240, 240, 235)))
    page.oval(x + w * 0.50, y + h * 0.50, w * 0.30, h * 0.12,
              bytes((120, 170, 90)))
    page.seg(x + w * 0.50, y + h * 0.38, x + w * 0.50, y + h * 0.62, SNOW, 2)
    page.dot(x + w * 0.50, y + h * 0.50, h * 0.05, SNOW)
    page.ring(x + w * 0.50, y + h * 0.50, h * 0.05, SNOW, 1.5)
    page.fill([(x + w * 0.14, y + h * 0.30), (x + w * 0.20, y + h * 0.18),
               (x + w * 0.26, y + h * 0.30)], RUBY)
    page.fill([(x + w * 0.74, y + h * 0.30), (x + w * 0.80, y + h * 0.18),
               (x + w * 0.86, y + h * 0.30)], RUBY)


def art_fbi(page, x, y, w, h):
    page.box(x, y, w, h, bytes((226, 232, 240)))
    for k in range(3):
        shade = NAVY if k % 2 == 0 else bytes((52, 84, 130))
        page.box(x + w * 0.16, y + h * (0.16 + k * 0.22), w * 0.34,
                 h * 0.14, shade)
        page.box(x + w * 0.20, y + h * (0.20 + k * 0.22), w * 0.26,
                 h * 0.03, SNOW)
        page.box(x + w * 0.20, y + h * (0.25 + k * 0.22), w * 0.18,
                 h * 0.03, SNOW)
    page.ring(x + w * 0.68, y + h * 0.40, h * 0.20, INK, 3)
    page.seg(x + w * 0.80, y + h * 0.54, x + w * 0.92, y + h * 0.72, INK, 4)
    page.box(x + w * 0.60, y + h * 0.32, w * 0.16, h * 0.03, RUBY)
    page.box(x + w * 0.60, y + h * 0.38, w * 0.10, h * 0.03, RUBY)


def art_chart(page, x, y, w, h):
    page.box(x, y, w, h, bytes((238, 240, 236)))
    for k in range(4):
        page.seg(x + w * 0.14, y + h * (0.20 + k * 0.20),
                 x + w * 0.86, y + h * (0.20 + k * 0.20),
                 bytes((200, 205, 200)), 1)
    page.path([(x + w * 0.16, y + h * 0.72), (x + w * 0.30, y + h * 0.66),
               (x + w * 0.44, y + h * 0.70), (x + w * 0.56, y + h * 0.52),
               (x + w * 0.70, y + h * 0.56), (x + w * 0.84, y + h * 0.30)],
              LEAF, 3)
    page.dot(x + w * 0.84, y + h * 0.30, 4, LEAF)
    page.dot(x + w * 0.50, y + h * 0.34, h * 0.13, bytes((240, 170, 40)))
    put_text(page, x + w * 0.50, y + h * 0.40, "B", 13,
             bytes((150, 95, 0)), bold=2.0, align="center")


def art_baseball(page, x, y, w, h):
    page.box(x, y, w, h, bytes((214, 232, 196)))
    page.box(x, y + h * 0.70, w, h * 0.30, bytes((120, 160, 90)))
    page.fill([(x + w * 0.30, y + h * 0.14), (x + w * 0.42, y + h * 0.14),
               (x + w * 0.48, y + h * 0.58), (x + w * 0.34, y + h * 0.58)],
              bytes((196, 164, 110)))
    page.seg(x + w * 0.36, y + h * 0.14, x + w * 0.30, y + h * 0.02,
             bytes((120, 90, 60)), 3)
    page.dot(x + w * 0.72, y + h * 0.24, h * 0.10, SNOW)
    page.arc(x + w * 0.72, y + h * 0.24, h * 0.07, 0.6, 2.2, RUBY, 1.5)
    page.arc(x + w * 0.72, y + h * 0.24, h * 0.07, 3.7, 5.3, RUBY, 1.5)
    for k in range(3):
        page.seg(x + w * (0.60 + k * 0.06), y + h * 0.70,
                 x + w * (0.60 + k * 0.06), y + h * 0.44, AMBER, 2)


def art_flag(page, x, y, w, h):
    page.box(x, y, w, h, bytes((238, 232, 216)))
    page.seg(x + w * 0.30, y + h * 0.12, x + w * 0.30, y + h * 0.88,
             bytes((90, 70, 40)), 3)
    page.fill([(x + w * 0.30, y + h * 0.12), (x + w * 0.78, y + h * 0.24),
               (x + w * 0.30, y + h * 0.38)], bytes((255, 153, 51)))
    page.fill([(x + w * 0.30, y + h * 0.38), (x + w * 0.78, y + h * 0.50),
               (x + w * 0.30, y + h * 0.62)], SNOW)
    page.fill([(x + w * 0.30, y + h * 0.62), (x + w * 0.78, y + h * 0.74),
               (x + w * 0.30, y + h * 0.86)], bytes((19, 136, 8)))
    page.dot(x + w * 0.52, y + h * 0.50, h * 0.07, NAVY)
    page.ring(x + w * 0.52, y + h * 0.50, h * 0.07, NAVY, 1.5)


# ------------------------------------------------------------------ the map
# Coarse continent outlines (longitude, latitude), equirectangular.
LAND = [
    [(-165, 65), (-140, 70), (-110, 70), (-85, 68), (-65, 60), (-55, 50),
     (-70, 42), (-78, 30), (-85, 28), (-95, 20), (-105, 22), (-115, 32),
     (-125, 45), (-135, 58), (-155, 58)],
    [(-78, 8), (-65, 10), (-52, 5), (-38, -8), (-42, -22), (-52, -32),
     (-65, -42), (-72, -50), (-73, -35), (-77, -12), (-80, 2)],
    [(-16, 15), (-16, 30), (-5, 36), (10, 37), (22, 33), (32, 31),
     (42, 13), (50, 12), (42, -2), (38, -16), (30, -28), (20, -35),
     (14, -24), (12, -10), (8, 4), (-10, 6)],
    [(-10, 37), (-8, 43), (-2, 48), (3, 52), (8, 57), (15, 56), (22, 57),
     (28, 61), (30, 69), (42, 66), (40, 58), (32, 45), (26, 40), (18, 42),
     (10, 44), (2, 42)],
    [(32, 64), (48, 68), (70, 72), (105, 76), (140, 71), (170, 66),
     (160, 60), (142, 50), (128, 40), (122, 30), (110, 18), (102, 8),
     (95, 15), (88, 22), (78, 10), (72, 22), (62, 25), (52, 28),
     (44, 29), (36, 36), (28, 40), (32, 50), (38, 58)],
    [(114, -22), (124, -14), (134, -12), (142, -12), (148, -20),
     (152, -28), (148, -38), (138, -36), (128, -32), (116, -34),
     (113, -24)],
    [(134, -12), (136, -20), (132, -32), (126, -32), (120, -34),
     (115, -32), (114, -24)],
]


def paint_map(page, x, y, w, h, pins):
    page.box(x, y, w, h, bytes((206, 224, 238)))
    for shape in LAND:
        pts = []
        for lon, lat in shape:
            pts.append((x + (lon + 180.0) / 360.0 * w,
                        y + (90.0 - lat) / 180.0 * h))
        page.fill(pts, bytes((228, 214, 178)))
        page.path(pts, bytes((170, 156, 120)), 1, shut=True)
    for num, lon, lat in pins:
        px = x + (lon + 180.0) / 360.0 * w
        py = y + (90.0 - lat) / 180.0 * h
        page.dot(px, py, 7, RUBY)
        page.ring(px, py, 7, SNOW, 1.5)
        put_text(page, px, py + 3.2, str(num), 9, SNOW, bold=2.0,
                 align="center")


# ------------------------------------------------------------------ the news
KICKER = ("Huang is back at Nvidia \u00b7 Ukraine sinks a Russian warship "
          "off Libya \u00b7 COP31 ends with no deal")

BIG_NUMBERS = [
    ("+31%", "NVIDIA SHARES IN A DAY"),
    ("+$950B", "NVIDIA VALUE ADDED"),
    ("7", "SEA DRONES VS MERKURY"),
    ("11", "DEAD IN DYMER STRIKE"),
    ("24", "DEAD IN BANTEN FIRE"),
    ("130", "PARTIES REJECTED COP31 TEXT"),
]

REGION_TALLY = [("EUROPE", 12), ("MIDDLE EAST", 5), ("AMERICAS", 6),
                ("SOUTH ASIA", 4), ("ASIA-PACIFIC", 2), ("AFRICA", 2),
                ("MARKETS & SPORT", 3), ("WORLD", 1)]

DAY_CLOCK = ("THE DAY IN UTC \u2014 14:00 Nvidia reinstates Huang \u00b7 "
             "15:20 US strike reported off Qeshm Island \u00b7 21:00 Wall "
             "Street closes: Nasdaq +6.5%, S&P +4.7%")

LEAD_STORIES = [
    {"art": art_nvidia, "num": 1, "place": "SANTA CLARA, USA",
     "beat": "TECH", "flag": "CONFIRMED",
     "head": "Huang is back: Nvidia reinstates its CEO after 11 days",
     "body": ("The board restores Jensen Huang as CEO, president and "
              "director, 11 days after he resigned. Shares jump 31% "
              "\u2014 best day since 2003 \u2014 adding about $950bn."),
     "credit": "Sources: Reuters \u00b7 WSJ \u00b7 CNN"},
    {"art": art_merkury, "num": 2, "place": "OFF BENGHAZI, LIBYA",
     "beat": "WAR AT SEA", "flag": "CONFIRMED",
     "head": "Ukraine says its sea drones sank the Russian corvette Merkury",
     "body": ("President Zelensky says seven sea drones sank the "
              "Merkury off Libya and hit a second vessel. The Kremlin "
              "warns of escalation; Albania denies the launch."),
     "credit": "Sources: Reuters \u00b7 BBC"},
    {"art": art_cop31, "num": 3, "place": "ANTALYA, TURKIYE",
     "beat": "CLIMATE", "flag": "FALLOUT",
     "head": "COP31 ends with no deal \u2014 now the blame and the reform calls",
     "body": ("The summit closed with no approved text after the draft "
              "dropped any mention of moving away from fossil fuels. "
              "Calls grow for urgent reform of the UN climate talks."),
     "credit": "Sources: The Guardian \u00b7 BBC \u00b7 Reuters"},
]

TEN_STORIES = [
    {"art": art_collapse, "num": 4, "place": "DYMER, UKRAINE",
     "beat": "WAR", "head": "Drone collapses block of flats; 11 dead",
     "body": ("A five-storey block partly collapses; a boy is pulled "
              "alive after 14 hours."),
     "credit": "Reuters"},
    {"art": art_khartoum, "num": 5, "place": "KHARTOUM, SUDAN",
     "beat": "WAR", "head": "Drone strikes hit homes and UN site; 4 die",
     "body": ("Strikes hit homes and a UN compound near Khartoum; fears "
              "grow for civilians."),
     "credit": "Reuters"},
    {"art": art_factory, "num": 6, "place": "CIKANDE, INDONESIA",
     "beat": "FIRE", "head": "Search goes on for dozens missing after fire",
     "body": ("At least 24 dead at the Fonusa Agung Mulia candy plant; "
              "dozens still missing."),
     "credit": "Detiknews \u00b7 AP"},
    {"art": art_plane, "num": 7, "place": "BRUSSELS, BELGIUM",
     "beat": "STRIKE", "head": "Belgium strike grounds flights, halts trains",
     "body": ("An anti-austerity strike disrupts flights and trains "
              "across Belgium."),
     "credit": "BBC"},
    {"art": art_tanker, "num": 8, "place": "TEHRAN / D.C.",
     "beat": "GULF", "head": "Trump warns Iran of \u2018very traumatic\u2019 outcome",
     "body": ("Trump may send a second carrier to the Gulf; Iran vows "
              "to use \u2018all means\u2019."),
     "credit": "Al Jazeera \u00b7 Reuters"},
    {"art": art_stadium, "num": 9, "place": "LONDON, UK",
     "beat": "POLITICS", "head": "UK to host the 2035 Women\u2019s World Cup",
     "body": ("FIFA confirms the UK as 2035 host; Burnham defends the "
              "new EU agreement."),
     "credit": "BBC"},
    {"art": art_fbi, "num": 10, "place": "WASHINGTON, USA",
     "beat": "CYBER", "head": "FBI probes hack of its crime database",
     "body": ("The FBI investigates an apparent hack of the National "
              "Crime Information Center."),
     "credit": "BBC \u00b7 AP"},
    {"art": art_chart, "num": 11, "place": "NEW YORK, USA",
     "beat": "MARKETS", "head": "Bitcoin rebounds from two-year low to $61,000",
     "body": ("Bitcoin bounces back as Wall Street futures recover "
              "after Friday\u2019s plunge."),
     "credit": "CoinDesk"},
    {"art": art_baseball, "num": 12, "place": "NEW YORK, USA",
     "beat": "SPORT", "head": "Skubal agrees $450m Mets deal, pitcher record",
     "body": ("Two-time Cy Young winner Tarik Skubal agrees a nine-year, "
              "$450m Mets deal."),
     "credit": "AP"},
    {"art": art_flag, "num": 13, "place": "NEW DELHI",
     "beat": "DIPLOMACY", "head": "Modi offers Nepal an offshore IIT campus",
     "body": ("Modi announces an offshore IIT campus in Nepal and "
              "closer ties on the PM\u2019s visit."),
     "credit": "Indian media"},
]

MORE_STORIES = [
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

DATE_NOTE = ("DATE CHECK \u00b7 Left out on purpose, first reported before "
             "Monday: ICJ Myanmar genocide ruling (19 Nov) \u00b7 Kerch "
             "Bridge strike (17 Nov) \u00b7 Shenzhen summit (19 Nov) \u00b7 "
             "Nvidia CEO resigns (12 Nov) \u00b7 Peru 6.7 quake (20 Nov) \u00b7 "
             "Alcaraz wins ATP Finals (22 Nov) \u00b7 COP31 collapse (22 Nov "
             "\u2014 only the fallout is Monday\u2019s news).")

PIN_SPOTS = [(1, -122.0, 37.4), (2, 20.1, 32.1), (3, 30.7, 36.9),
             (4, 30.8, 50.9), (5, 32.5, 15.6), (6, 106.1, -6.2),
             (7, 4.35, 50.85), (8, 51.4, 35.7), (9, -0.1, 51.5),
             (10, -77.0, 38.9), (11, -74.0, 40.7), (12, -73.2, 41.3),
             (13, 77.2, 28.6)]


def hrule(page, top, colour=INK, thick=2):
    page.box(24, top, PAGE_W - 48, thick, colour)


def compose():
    page = Page(PAGE_W, PAGE_H, NEWS)
    put_text(page, 24, 24, "THE WORLD IN ONE DAY", 12, RUBY, bold=2.0)
    put_text(page, PAGE_W - 24, 24,
             "35 STORIES \u00b7 8 REGIONS \u00b7 EVERY ONE DATED MONDAY 23 NOVEMBER 2026",
             10, INK, bold=1.4, align="right")
    hrule(page, 30, INK, 2)
    put_text(page, PAGE_W / 2, 96, "Monday 23 November 2026", 62, INK,
             bold=1.5, align="center", stretch=0.58)
    put_text(page, PAGE_W / 2, 122, KICKER, 14, RUBY, bold=1.3,
             align="center")
    hrule(page, 128, INK, 3)
    cell = (PAGE_W - 48) / 6.0
    for k, (big, label) in enumerate(BIG_NUMBERS):
        middle = 24 + cell * (k + 0.5)
        put_text(page, middle, 164, big, 26, RUBY, bold=2.0,
                 align="center", stretch=0.8)
        put_text(page, middle, 180, label, 9, INK, bold=1.3,
                 align="center")
        if k:
            page.box(24 + int(cell * k), 136, 1, 48, PALE)
    hrule(page, 186, INK, 1)
    nband = len(REGION_TALLY)
    chip_w = (PAGE_W - 48 - (nband - 1) * 4) / float(nband)
    for k, (name, total) in enumerate(REGION_TALLY):
        left = 24 + k * (chip_w + 4)
        page.box(left, 192, chip_w, 18,
                 BAND_COLOURS[k % len(BAND_COLOURS)])
        put_text(page, left + chip_w / 2, 206, "%s %d" % (name, total), 9,
                 SNOW, bold=1.6, align="center")
    page.box(24, 216, PAGE_W - 48, 16, NAVY)
    put_text(page, PAGE_W / 2, 229, DAY_CLOCK, 9.5, SNOW, bold=1.3,
             align="center")
    lead_w = (PAGE_W - 48 - 2 * 12) / 3.0
    for k, lead in enumerate(LEAD_STORIES):
        left = 24 + k * (lead_w + 12)
        lead["art"](page, left, 238, lead_w, 104)
        page.box(left, 342, lead_w, 2, INK)
        tag = "%d \u00b7 %s \u00b7 %s" % (lead["num"], lead["place"],
                                        lead["beat"])
        put_text(page, left, 356, tag, 10, RUBY, bold=2.0)
        tag_w = measure(tag, 10, 2.0)
        page.box(left + tag_w + 6, 347, 54, 13, RUBY)
        put_text(page, left + tag_w + 33, 357, lead["flag"], 9, SNOW,
                 bold=2.0, align="center")
        yy = 380
        for line in split_lines(lead["head"], 16, lead_w, 2.0)[:3]:
            put_text(page, left, yy, line, 16, INK, bold=2.0)
            yy += 19.5
        yy += 4
        yy = put_para(page, left, yy, lead["body"], 10.5, INK, lead_w,
                      leading=1.35)
        put_text(page, left, yy + 8, lead["credit"], 8.5, ASH, bold=1.2)
    hrule(page, 522, INK, 2)
    put_text(page, 24, 538, "THE DAY IN TEN", 13, INK, bold=2.0)
    put_text(page, PAGE_W - 24, 538, "THE STORIES THAT MOVED THE WORLD TODAY",
             9, ASH, bold=1.3, align="right")
    feat_w = (PAGE_W - 48 - 4 * 8) / 5.0
    for pos, feat in enumerate(TEN_STORIES):
        col, row = pos % 5, pos // 5
        left = 24 + col * (feat_w + 8)
        top = 544 + row * 127
        feat["art"](page, left, top, feat_w, 40)
        yy = top + 50
        put_text(page, left, yy, "%d \u00b7 %s \u00b7 %s" % (
            feat["num"], feat["place"], feat["beat"]), 8, RUBY, bold=2.0)
        yy += 11
        for line in split_lines(feat["head"], 11, feat_w, 2.0)[:2]:
            put_text(page, left, yy, line, 11, INK, bold=2.0)
            yy += 12.5
        yy += 1
        for line in split_lines(feat["body"], 8.5, feat_w, 1.0)[:3]:
            put_text(page, left, yy, line, 8.5, INK, bold=1.0)
            yy += 10.5
    hrule(page, 800, INK, 2)
    put_text(page, 24, 816, "WHERE IT HAPPENED \u2014 PINS MATCH STORY NUMBERS",
             10, INK, bold=2.0)
    paint_map(page, 24, 822, 300, 112, PIN_SPOTS)
    put_text(page, 24, 946, "Red numbers mark stories 1\u201313 on the map.",
             8.5, ASH, bold=1.2)
    ax = 348
    put_text(page, ax, 816, "ALSO ON MONDAY 23 NOVEMBER \u2014 22 MORE STORIES",
             12, INK, bold=2.0)
    half = (PAGE_W - 24 - ax - 12) / 2.0
    for j, (num, place, text, src) in enumerate(MORE_STORIES):
        col, row = j % 2, j // 2
        left = ax + col * (half + 12)
        line = "%d %s \u2014 %s (%s)" % (num, place, text, src)
        put_text(page, left, 834 + row * 12, line, 8, INK, bold=1.0)
    page.box(24, 958, PAGE_W - 48, 2, RUBY)
    page.box(24, 958, 2, 34, RUBY)
    page.box(PAGE_W - 26, 958, 2, 34, RUBY)
    page.box(24, 990, PAGE_W - 48, 2, RUBY)
    yy = 970
    for line in split_lines(DATE_NOTE, 8.5, PAGE_W - 48 - 16, 1.2)[:2]:
        put_text(page, 32, yy, line, 8.5, WINERED, bold=1.2)
        yy += 12
    put_text(page, PAGE_W / 2, 1006,
             "Every story here happened, or was first reported, on Monday 23 "
             "November 2026 in at least one time zone. Claims are attributed, "
             "not stated as fact.", 8.5, INK, bold=1.2, align="center")
    put_text(page, PAGE_W / 2, 1019,
             "Sources: Reuters \u00b7 AP \u00b7 BBC \u00b7 Al Jazeera \u00b7 The "
             "Guardian \u00b7 CNN \u00b7 WSJ \u00b7 UKMTO \u00b7 Detiknews. Original "
             "vector drawings.", 8.5, INK, bold=1.2, align="center")
    return page


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/tmp/out")
    os.makedirs(out_dir, exist_ok=True)
    front = compose()
    data = png_bytes(bytes(front.buf), PAGE_W, PAGE_H)
    with open(os.path.join(out_dir, "entry.png"), "wb") as handle:
        handle.write(data)


if __name__ == "__main__":
    main()
