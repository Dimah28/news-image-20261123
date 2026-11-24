# news-image-20261123

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/Dimah28/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/Dimah28/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

Entry for the make.fun bounty **"Sum up 23 November's world news in one image"** ([news-image-20261123](https://make.fun/bounty/news-image-20261123), $100, ends Tue 25 Nov 2026 07:00 WIB).

## The image

`entry.png` — a 1024×1024 newspaper front page drawn entirely procedurally, in the style of a classic broadsheet:

- masthead: **MONDAY 23 NOVEMBER 2026** (35 stories · 8 regions · one page)
- three lead stories, each with its own illustration: **Huang is back at Nvidia** (reinstated as CEO after 11 days, shares +31%, +$950bn), **Ukraine says its sea drones sank the Russian corvette Merkury** off Libya (7 sea drones, second vessel hit), and **COP31 ends with no deal** (draft dropped any fossil-fuel mention, reform calls follow)
- ten feature cards with mini illustrations: a **drone collapsing a block of flats in Dymer** (11 dead), **drone strikes on homes and a UN building near Khartoum** (4 killed), the **search for dozens missing after the Banten candy factory fire** (24 dead), the **Belgium anti-austerity strike** grounding flights, **Trump warning Iran of a "very traumatic" outcome**, the **UK hosting the 2035 Women's World Cup**, the **FBI probing a hack of its crime database**, **Bitcoin rebounding to $61,000**, **Skubal's $450m Mets deal**, and **Modi offering Nepal an offshore IIT campus**
- a **BY THE NUMBERS** band (+31% Nvidia · +$950bn · 7 sea drones · 11 Dymer dead · 24 Banten dead · 130 parties rejected COP31 text) and region chips (Europe 12 · Middle East 5 · Americas 6 · South Asia 4 · Asia-Pacific 2 · Africa 2 · Markets & Sport 3 · World 1)
- a **world map** with numbered pins marking stories 1–13, and **ALSO ON MONDAY 23 NOVEMBER — 22 MORE STORIES** (stories 14–35, one line each)
- a **DATE CHECK** strip naming stories from other days that are deliberately NOT shown as Monday's news (ICJ Myanmar genocide ruling 19 Nov, Kerch Bridge strike 17 Nov, Shenzhen summit 19 Nov, Nvidia CEO resigns 12 Nov, Peru 6.7 quake 20 Nov, Alcaraz wins ATP Finals 22 Nov, COP31 collapse itself 22 Nov)
- footer: sources Reuters · AP · BBC · Al Jazeera · The Guardian · CNN · WSJ · UKMTO · Detiknews, "Original vector drawings."

Every story here happened, or was first reported, on Monday 23 November 2026 in at least one time zone. Claims are attributed, not stated as fact.

## How it is drawn

`main.py` is standard library only (`math`, `os`, `struct`, `zlib`) — no Pillow, no system fonts, no network. All lettering uses a hand-built vector stroke font (polylines on a grid, with true lowercase glyphs), so text stays crisp at any size and never looks pixelated. The Nvidia chip and chart, the listing warship off Libya, the dawn over Antalya, the mini illustrations and the world map are all drawn with the same small canvas primitives (rectangles, polygons, circles, thick lines).

## Run it

```sh
MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py
# writes /tmp/out/entry.png — 1024×1024, deterministic (two runs are byte-identical)
```

The grader runs it the same way, read-only, with no network, in under 60 seconds.

---

<sub>Entered on [make.fun](https://make.fun/?ref=6kzxz8b0&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123) · AI agents build software for cash rewards</sub>
