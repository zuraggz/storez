"""Generate every placeholder image the storefront uses as a flat SVG.

    python scripts/generate_images.py

Output: public/images/{products,blog,hero,about}/*.svg plus public/favicon.svg.
Nothing is fetched from an image host, so the shop works offline, in Docker and
on Vercel alike. The generated files are committed — re-run this only when a
shape or colourway changes.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public" / "images"

BG = {"main": "#f1f0ef", "alt": "#e9e7e5", "detail": "#f6f4f2"}
SHADOW = '<ellipse cx="300" cy="506" rx="118" ry="13" fill="#1a1a1a" opacity="0.06"/>'

Palette = dict[str, str]


def _round(value: float) -> int:
    """Round halves away from zero, the way the original generator did."""
    return math.floor(value + 0.5)


# ---------------------------------------------------------------------------
# Garment / product shapes. Every shape draws inside a 600x600 viewBox.
# ---------------------------------------------------------------------------
def shirt(c: Palette, short: bool = False, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]

    if short:
        sleeves = (
            f'<path d="M236 170 L172 204 Q162 210 166 222 L190 276 Q194 288 206 284 L250 264 Z" fill="{shade}"/>'
            f'<path d="M364 170 L428 204 Q438 210 434 222 L410 276 Q406 288 394 284 L350 264 Z" fill="{shade}"/>'
        )
    else:
        sleeves = (
            f'<path d="M236 170 L192 190 Q176 197 172 214 L150 320 Q147 334 160 338 L196 348 Q210 352 213 338 L238 236 Z" fill="{shade}"/>'
            f'<path d="M364 170 L408 190 Q424 197 428 214 L450 320 Q453 334 440 338 L404 348 Q390 352 387 338 L362 236 Z" fill="{shade}"/>'
        )

    buttons = "".join(f'<circle cx="300" cy="{y}" r="5" fill="{trim}"/>' for y in (236, 296, 356, 416))

    return (
        f"{sleeves}"
        f'<path d="M232 168 Q300 206 368 168 L392 470 Q393 482 381 482 L219 482 Q207 482 208 470 Z" fill="{main}"/>'
        f'<path d="M268 158 L300 200 L332 158 L318 150 L300 172 L282 150 Z" fill="{trim}"/>'
        f'<rect x="294" y="196" width="12" height="286" fill="{shade}" opacity="0.55"/>'
        f"{buttons}"
    )


def tee(c: Palette, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]
    return (
        f'<path d="M238 172 L178 204 Q168 210 172 222 L194 272 Q198 284 210 280 L250 262 Z" fill="{shade}"/>'
        f'<path d="M362 172 L422 204 Q432 210 428 222 L406 272 Q402 284 390 280 L350 262 Z" fill="{shade}"/>'
        f'<path d="M238 172 Q300 214 362 172 L386 470 Q387 482 375 482 L225 482 Q213 482 214 470 Z" fill="{main}"/>'
        f'<path d="M252 166 Q300 210 348 166 Q326 190 300 190 Q274 190 252 166 Z" fill="{trim}"/>'
    )


def sweatshirt(c: Palette, open: bool = False, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]

    if open:
        body = (
            f'<path d="M232 168 Q266 196 292 200 L292 460 L219 460 Q207 460 208 448 Z" fill="{main}"/>'
            f'<path d="M368 168 Q334 196 308 200 L308 460 L381 460 Q393 460 392 448 Z" fill="{main}"/>'
        )
    else:
        body = f'<path d="M232 168 Q300 206 368 168 L392 448 L208 448 Z" fill="{main}"/>'

    ribs = "".join(
        f'<rect x="{x}" y="454" width="4" height="22" fill="{main}" opacity="0.5"/>'
        for x in (216, 240, 264, 288, 312, 336, 360, 384)
    )

    return (
        f'<path d="M236 168 L190 190 Q172 198 168 216 L144 328 Q141 342 155 346 L192 356 Q206 360 209 346 L238 238 Z" fill="{shade}"/>'
        f'<path d="M364 168 L410 190 Q428 198 432 216 L456 328 Q459 342 445 346 L408 356 Q394 360 391 346 L362 238 Z" fill="{shade}"/>'
        f"{body}"
        f'<rect x="204" y="448" width="192" height="34" rx="8" fill="{shade}"/>'
        f"{ribs}"
        f'<path d="M258 162 Q300 198 342 162 Q322 182 300 182 Q278 182 258 162 Z" fill="{trim}"/>'
    )


def coat(c: Palette, quilted: bool = False, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]

    quilt = (
        "".join(
            f'<rect x="212" y="{y}" width="176" height="3" fill="{shade}" opacity="0.7"/>'
            for y in (230, 278, 326, 374, 422)
        )
        if quilted
        else ""
    )

    buttons = "".join(f'<circle cx="300" cy="{y}" r="6" fill="{trim}"/>' for y in (268, 330, 392))

    return (
        f'<path d="M232 164 L184 188 Q164 198 160 218 L134 348 Q131 363 146 367 L186 378 Q201 382 204 367 L234 240 Z" fill="{shade}"/>'
        f'<path d="M368 164 L416 188 Q436 198 440 218 L466 348 Q469 363 454 367 L414 378 Q399 382 396 367 L366 240 Z" fill="{shade}"/>'
        f'<path d="M228 164 Q300 200 372 164 L398 492 Q399 504 387 504 L213 504 Q201 504 202 492 Z" fill="{main}"/>'
        f"{quilt}"
        f'<path d="M262 168 L300 226 L300 168 Z" fill="{trim}"/>'
        f'<path d="M338 168 L300 226 L300 168 Z" fill="{trim}"/>'
        f'<rect x="296" y="226" width="8" height="278" fill="{shade}" opacity="0.5"/>'
        f"{buttons}"
    )


def pants(c: Palette, bib: bool = False, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]

    bib_art = (
        (
            f'<path d="M252 96 L348 96 L348 178 L252 178 Z" fill="{main}"/>'
            f'<rect x="266" y="118" width="68" height="44" rx="6" fill="{shade}" opacity="0.6"/>'
            f'<path d="M256 96 L242 168 L228 166 L244 92 Z" fill="{shade}"/>'
            f'<path d="M344 96 L358 168 L372 166 L356 92 Z" fill="{shade}"/>'
        )
        if bib
        else ""
    )

    return (
        f"{bib_art}"
        f'<path d="M222 176 L378 176 L370 476 Q369 486 359 486 L318 486 Q308 486 307 476 L300 306 L293 476 Q292 486 282 486 L241 486 Q231 486 230 476 Z" fill="{main}"/>'
        f'<rect x="220" y="168" width="160" height="30" rx="6" fill="{shade}"/>'
        f'<path d="M240 210 Q258 226 276 212" fill="none" stroke="{trim}" stroke-width="4" opacity="0.8"/>'
        f'<path d="M324 210 Q342 226 360 212" fill="none" stroke="{trim}" stroke-width="4" opacity="0.8"/>'
        f'<rect x="292" y="168" width="16" height="24" rx="4" fill="{trim}"/>'
    )


def dress(c: Palette, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]
    return (
        f'<path d="M262 152 L272 108" stroke="{shade}" stroke-width="9" stroke-linecap="round"/>'
        f'<path d="M338 152 L328 108" stroke="{shade}" stroke-width="9" stroke-linecap="round"/>'
        f'<path d="M250 156 Q300 188 350 156 L368 256 L404 474 Q406 486 394 486 L206 486 Q194 486 196 474 L232 256 Z" fill="{main}"/>'
        f'<rect x="234" y="262" width="132" height="20" rx="6" fill="{trim}"/>'
        f'<path d="M366 272 L410 296 L404 306 L364 288 Z" fill="{trim}"/>'
        f'<path d="M254 300 L246 470" stroke="{shade}" stroke-width="3" opacity="0.5"/>'
        f'<path d="M346 300 L354 470" stroke="{shade}" stroke-width="3" opacity="0.5"/>'
    )


def scarf(c: Palette, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]

    fringe = "".join(
        f'<rect x="{_round(174 + index * 26)}" y="{_round(412 - index * 3.35)}" width="4" height="26" rx="2" fill="{shade}"/>'
        for index in range(11)
    )

    return (
        f'<path d="M170 236 L430 196 L430 372 L170 412 Z" fill="{main}"/>'
        f'<path d="M170 236 L430 196 L430 232 L170 272 Z" fill="{shade}"/>'
        f'<path d="M300 216 L300 392" stroke="{trim}" stroke-width="5" opacity="0.7"/>'
        f'<path d="M170 320 L430 280" stroke="{trim}" stroke-width="5" opacity="0.7"/>'
        f"{fringe}"
    )


def backpack(c: Palette, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]
    return (
        f'<path d="M214 214 Q170 316 206 424" fill="none" stroke="{shade}" stroke-width="18" stroke-linecap="round"/>'
        f'<path d="M386 214 Q430 316 394 424" fill="none" stroke="{shade}" stroke-width="18" stroke-linecap="round"/>'
        f'<path d="M274 190 Q300 152 326 190" fill="none" stroke="{shade}" stroke-width="13" stroke-linecap="round"/>'
        f'<rect x="196" y="182" width="208" height="272" rx="38" fill="{main}"/>'
        f'<path d="M196 262 L404 262" stroke="{trim}" stroke-width="6" opacity="0.9"/>'
        f'<rect x="226" y="316" width="148" height="112" rx="24" fill="{shade}"/>'
        f'<rect x="248" y="352" width="104" height="7" rx="3" fill="{trim}" opacity="0.9"/>'
        f'<circle cx="300" cy="230" r="13" fill="{shade}"/>'
    )


def tote(c: Palette, small: bool = False, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]

    y = 288 if small else 244
    h = 190 if small else 236
    x = 214 if small else 190
    w = 172 if small else 220

    if small:
        strap = f'<path d="M232 300 Q300 122 368 300" fill="none" stroke="{shade}" stroke-width="11"/>'
    else:
        strap = (
            f'<path d="M240 250 Q240 168 300 168 Q360 168 360 250" fill="none" '
            f'stroke="{shade}" stroke-width="14" stroke-linecap="round"/>'
        )

    return (
        f"{strap}"
        f'<path d="M{x} {y} L{x + w} {y} L{x + w - 16} {y + h} Q{x + w - 17} {y + h + 10} {x + w - 27} {y + h + 10} '
        f'L{x + 27} {y + h + 10} Q{x + 17} {y + h + 10} {x + 16} {y + h} Z" fill="{main}"/>'
        f'<path d="M{x} {y} L{x + w} {y} L{x + w} {y + 46} Q{x + w // 2} {y + 74} {x} {y + 46} Z" fill="{shade}"/>'
        f'<rect x="288" y="{y + 40}" width="24" height="20" rx="5" fill="{trim}"/>'
    )


def duffel(c: Palette, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]
    return (
        f'<path d="M244 252 Q244 200 272 200" fill="none" stroke="{shade}" stroke-width="11" stroke-linecap="round"/>'
        f'<path d="M356 252 Q356 200 328 200" fill="none" stroke="{shade}" stroke-width="11" stroke-linecap="round"/>'
        f'<path d="M272 200 L328 200" stroke="{shade}" stroke-width="11" stroke-linecap="round"/>'
        f'<rect x="152" y="248" width="296" height="164" rx="82" fill="{main}"/>'
        f'<path d="M172 296 Q300 268 428 296" fill="none" stroke="{trim}" stroke-width="7"/>'
        f'<rect x="188" y="344" width="224" height="18" rx="9" fill="{shade}"/>'
        f'<rect x="264" y="410" width="72" height="16" rx="8" fill="{shade}"/>'
    )


def shoe(c: Palette, boot: bool = False, laces: bool = False, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]

    shaft = (
        (
            f'<path d="M238 178 Q238 168 248 168 L326 168 Q336 168 336 178 L344 336 L232 336 Z" '
            f'fill="{main}" stroke="{shade}" stroke-width="3"/>'
            f'<rect x="330" y="196" width="17" height="140" rx="8" fill="{shade}"/>'
            f'<rect x="230" y="196" width="15" height="140" rx="7" fill="{shade}"/>'
        )
        if boot
        else ""
    )

    if laces:
        lace_art = "".join(
            f'<path d="M{x - 20} {332 - index * 8} L{x + 20} {314 - index * 8}" '
            f'stroke="{trim}" stroke-width="8" stroke-linecap="round"/>'
            for index, x in enumerate((252, 284, 316))
        )
    else:
        lace_art = f'<path d="M226 316 L330 344 L326 366 L222 338 Z" fill="{trim}"/>'

    return (
        f"{shaft}"
        f'<path d="M160 410 Q154 312 204 292 L252 276 Q276 268 296 282 L346 320 Q398 350 424 372 '
        f'Q440 384 440 400 L440 412 Z" fill="{main}" stroke="{shade}" stroke-width="3"/>'
        f'<ellipse cx="212" cy="288" rx="44" ry="15" fill="{shade}" transform="rotate(-16 212 288)"/>'
        f'<ellipse cx="214" cy="292" rx="34" ry="10" fill="{main}" opacity="0.55" transform="rotate(-16 214 292)"/>'
        f"{lace_art}"
        f'<path d="M352 336 Q400 366 428 400" fill="none" stroke="{shade}" stroke-width="5" opacity="0.55"/>'
        f'<path d="M154 408 L446 408 L446 434 Q446 450 430 450 L170 450 Q154 450 154 434 Z" fill="{shade}"/>'
        f'<path d="M154 432 L446 432" stroke="{trim}" stroke-width="3" opacity="0.5"/>'
    )


def watch(c: Palette, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]

    links = "".join(
        f'<rect x="272" y="{y}" width="56" height="3" fill="{main}" opacity="0.5"/>' for y in (150, 176, 202)
    )

    return (
        f'<path d="M258 246 L262 128 Q263 114 277 114 L323 114 Q337 114 338 128 L342 246 Z" fill="{shade}"/>'
        f'<path d="M258 354 L262 472 Q263 486 277 486 L323 486 Q337 486 338 472 L342 354 Z" fill="{shade}"/>'
        f'<rect x="238" y="232" width="124" height="136" rx="30" fill="{main}"/>'
        f'<rect x="252" y="246" width="96" height="108" rx="22" fill="#fbfaf9"/>'
        f'<path d="M300 268 L300 300 L326 314" fill="none" stroke="{trim}" stroke-width="6" stroke-linecap="round"/>'
        f'<circle cx="300" cy="300" r="5" fill="{trim}"/>'
        f'<rect x="360" y="284" width="14" height="26" rx="5" fill="{shade}"/>'
        f"{links}"
    )


def beanie(c: Palette, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]

    knit = "".join(
        f'<path d="M{226 + index * 25} 214 Q{226 + index * 25} 280 {226 + index * 25} 344" '
        f'stroke="{trim}" stroke-width="3" opacity="0.45" fill="none"/>'
        for index in range(7)
    )
    brim = "".join(
        f'<rect x="{198 + index * 20}" y="352" width="5" height="56" rx="2" fill="{main}" opacity="0.45"/>'
        for index in range(11)
    )

    return (
        f'<circle cx="300" cy="182" r="26" fill="{shade}"/>'
        f'<path d="M194 344 Q194 206 300 206 Q406 206 406 344 Z" fill="{main}"/>'
        f"{knit}"
        f'<rect x="184" y="342" width="232" height="76" rx="20" fill="{shade}"/>'
        f"{brim}"
    )


def sunglasses(c: Palette, **_: object) -> str:
    main, shade, trim = c["main"], c["shade"], c["trim"]
    return (
        f'<path d="M164 288 L108 258" stroke="{main}" stroke-width="10" stroke-linecap="round"/>'
        f'<path d="M436 288 L492 258" stroke="{main}" stroke-width="10" stroke-linecap="round"/>'
        f'<circle cx="226" cy="302" r="64" fill="{trim}" opacity="0.55"/>'
        f'<circle cx="374" cy="302" r="64" fill="{trim}" opacity="0.55"/>'
        f'<circle cx="226" cy="302" r="64" fill="none" stroke="{main}" stroke-width="10"/>'
        f'<circle cx="374" cy="302" r="64" fill="none" stroke="{main}" stroke-width="10"/>'
        f'<path d="M290 292 Q300 278 310 292" fill="none" stroke="{main}" stroke-width="10" stroke-linecap="round"/>'
        f'<path d="M206 278 Q222 262 244 268" fill="none" stroke="{shade}" stroke-width="7" stroke-linecap="round" opacity="0.8"/>'
    )


SHAPES = {
    "shirt": shirt,
    "tee": tee,
    "sweatshirt": sweatshirt,
    "coat": coat,
    "pants": pants,
    "dress": dress,
    "scarf": scarf,
    "backpack": backpack,
    "tote": tote,
    "duffel": duffel,
    "shoe": shoe,
    "watch": watch,
    "beanie": beanie,
    "sunglasses": sunglasses,
}


# ---------------------------------------------------------------------------
# Product catalogue: file name -> shape + palette. Must stay in sync with the
# image column seeded in app/seed.py.
# ---------------------------------------------------------------------------
PRODUCTS: list[tuple[str, str, Palette, dict[str, bool]]] = [
    ("shirt-blue", "shirt", {"main": "#b9d2ea", "shade": "#9dbcda", "trim": "#7fa4c6"}, {}),
    ("jeans-indigo", "pants", {"main": "#4a6d9c", "shade": "#3a5880", "trim": "#d9a441"}, {}),
    ("coat-camel", "coat", {"main": "#c9a271", "shade": "#ad855a", "trim": "#8a6740"}, {}),
    ("chino-olive", "pants", {"main": "#8d8f6a", "shade": "#737556", "trim": "#5c5e42"}, {}),
    ("polo-sand", "shirt", {"main": "#ddc9a8", "shade": "#c4ac89", "trim": "#9c8763"}, {"short": True}),
    ("sweatshirt-grey", "sweatshirt", {"main": "#b6b6b6", "shade": "#9a9a9a", "trim": "#828282"}, {}),
    ("blouse-white", "shirt", {"main": "#f7f4ee", "shade": "#ddd7cb", "trim": "#b6ae9e"}, {}),
    ("dress-rose", "dress", {"main": "#e5b4b8", "shade": "#cf979d", "trim": "#a86f76"}, {}),
    ("trouser-black", "pants", {"main": "#3a3a3d", "shade": "#2a2a2c", "trim": "#5b5b60"}, {}),
    ("cardigan-cream", "sweatshirt", {"main": "#eadfcc", "shade": "#d3c5ac", "trim": "#b3a288"}, {"open": True}),
    ("scarf-teal", "scarf", {"main": "#5f9a99", "shade": "#4a7e7d", "trim": "#d8e4e2"}, {}),
    ("backpack-black", "backpack", {"main": "#33333a", "shade": "#22222a", "trim": "#6d6d78"}, {}),
    ("puffer-navy", "coat", {"main": "#2f4a72", "shade": "#233a5b", "trim": "#d6a52f"}, {"quilted": True}),
    ("tee-pink", "tee", {"main": "#efc4cd", "shade": "#dba9b4", "trim": "#c98d99"}, {}),
    ("dungaree-blue", "pants", {"main": "#5e83b3", "shade": "#4a6b95", "trim": "#e2c07a"}, {"bib": True}),
    ("tote-tan", "tote", {"main": "#c08a53", "shade": "#a06f3f", "trim": "#7d5529"}, {}),
    ("weekender-olive", "duffel", {"main": "#6f7350", "shade": "#565a3c", "trim": "#b99a63"}, {}),
    ("crossbody-black", "tote", {"main": "#2e2e33", "shade": "#1f1f24", "trim": "#c9a24a"}, {"small": True}),
    ("sneaker-white", "shoe", {"main": "#f7f5f1", "shade": "#c2bdb3", "trim": "#8e8981"}, {"laces": True}),
    ("boot-brown", "shoe", {"main": "#7a4d31", "shade": "#5c3823", "trim": "#3f2717"}, {"boot": True}),
    ("loafer-navy", "shoe", {"main": "#39435e", "shade": "#2a3247", "trim": "#c2a15c"}, {}),
    ("watch-silver", "watch", {"main": "#c3c6ca", "shade": "#9ea2a7", "trim": "#3a3d42"}, {}),
    ("beanie-grey", "beanie", {"main": "#9d9d9d", "shade": "#7f7f7f", "trim": "#6a6a6a"}, {}),
    ("sunglasses-gold", "sunglasses", {"main": "#c9a447", "shade": "#a8862f", "trim": "#4c4a45"}, {}),
]


# ---------------------------------------------------------------------------
# Editorial illustrations for the blog cards and the about page.
# ---------------------------------------------------------------------------
def _storefront() -> str:
    rails = "".join(
        f'<path d="M{x} 104 L{x + 34} 104 L{x + 44} {210 + index * 16} L{x - 10} {210 + index * 16} Z" fill="{colour}"/>'
        for index, (x, colour) in enumerate(
            zip((92, 132, 172), ("#c88f7d", "#8fa5b8", "#cdb98c"), strict=True)
        )
    )

    return (
        '<rect width="600" height="400" fill="#efe9e2"/>'
        '<rect x="40" y="40" width="220" height="300" rx="10" fill="#e2d8cc"/>'
        '<rect x="70" y="96" width="160" height="8" rx="4" fill="#b9a992"/>'
        f"{rails}"
        '<rect x="292" y="120" width="120" height="220" rx="12" fill="#d9cfc2"/>'
        '<circle cx="352" cy="96" r="30" fill="#c4b7a6"/>'
        '<path d="M318 150 L386 150 L400 316 L304 316 Z" fill="#e0a394"/>'
        '<rect x="446" y="196" width="112" height="144" rx="10" fill="#cfd8c6"/>'
        '<path d="M502 196 Q470 130 502 92 Q534 130 502 196 Z" fill="#9db089"/>'
        '<rect x="24" y="340" width="552" height="26" rx="8" fill="#d8cec1"/>'
    )


SCENES = {
    "storefront": _storefront(),
    "flatlay": (
        '<rect width="600" height="400" fill="#f3efe9"/>'
        '<path d="M60 300 Q120 190 240 214 Q330 232 300 300 Z" fill="#e8c3c6"/>'
        '<circle cx="176" cy="150" r="52" fill="#dcc9a8"/>'
        '<rect x="330" y="120" width="150" height="104" rx="14" fill="#efe6d8"/>'
        '<path d="M330 120 L480 120 L480 156 Q405 178 330 156 Z" fill="#ddd0bb"/>'
        '<rect x="392" y="146" width="26" height="20" rx="5" fill="#c9a447"/>'
        '<ellipse cx="378" cy="292" rx="54" ry="30" fill="#3c4658"/>'
        '<ellipse cx="470" cy="292" rx="54" ry="30" fill="#3c4658"/>'
        '<circle cx="248" cy="330" r="20" fill="#e0b4bb"/>'
        '<path d="M96 96 L150 60" stroke="#c9a447" stroke-width="6" stroke-linecap="round"/>'
        '<circle cx="520" cy="86" r="34" fill="none" stroke="#c9a447" stroke-width="6"/>'
        '<circle cx="86" cy="352" r="16" fill="#cbb9a0"/>'
    ),
    "atelier": (
        '<rect width="600" height="400" fill="#eeeae4"/>'
        '<path d="M180 74 Q210 40 240 74" fill="none" stroke="#8b7355" stroke-width="9" stroke-linecap="round"/>'
        '<path d="M96 168 L210 78 L324 168" fill="none" stroke="#8b7355" stroke-width="14" stroke-linecap="round"/>'
        '<path d="M118 168 Q210 200 302 168 L322 340 L98 340 Z" fill="#d9c3a5"/>'
        '<rect x="392" y="196" width="88" height="120" rx="12" fill="#d8b25f"/>'
        '<rect x="386" y="188" width="100" height="18" rx="9" fill="#b9903f"/>'
        '<rect x="386" y="306" width="100" height="18" rx="9" fill="#b9903f"/>'
        '<path d="M508 120 L556 236" stroke="#5c5f66" stroke-width="10" stroke-linecap="round"/>'
        '<path d="M556 120 L508 236" stroke="#5c5f66" stroke-width="10" stroke-linecap="round"/>'
        '<circle cx="504" cy="256" r="20" fill="none" stroke="#5c5f66" stroke-width="9"/>'
        '<circle cx="560" cy="256" r="20" fill="none" stroke="#5c5f66" stroke-width="9"/>'
        '<rect x="40" y="340" width="520" height="24" rx="8" fill="#ddd5c9"/>'
    ),
    "workshop": (
        '<rect width="600" height="400" fill="#f0ece6"/>'
        '<rect x="60" y="150" width="200" height="150" rx="10" fill="#d8cdbd"/>'
        '<rect x="86" y="182" width="148" height="12" rx="6" fill="#b6a68f"/>'
        '<rect x="86" y="212" width="106" height="12" rx="6" fill="#c6b8a3"/>'
        '<rect x="86" y="242" width="130" height="12" rx="6" fill="#c6b8a3"/>'
        '<circle cx="404" cy="180" r="66" fill="#dcc4a4"/>'
        '<path d="M338 300 Q404 232 470 300 Z" fill="#8fa5b8"/>'
        '<rect x="300" y="300" width="208" height="20" rx="10" fill="#cfc5b6"/>'
        '<path d="M520 90 L556 126" stroke="#c9a447" stroke-width="8" stroke-linecap="round"/>'
        '<circle cx="98" cy="96" r="26" fill="#e0a394"/>'
    ),
}


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def svg(width: int, height: int, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img">{body}</svg>\n'
    )


def product_svg(shape_name: str, colours: Palette, options: dict[str, bool], variant: str) -> str:
    art = SHAPES[shape_name](colours, **options)
    background = BG[variant]

    if variant == "alt":
        transform = '<g transform="rotate(-7 300 300) translate(0 8) scale(0.94) translate(19 19)">'
    elif variant == "detail":
        transform = '<g transform="translate(-190 -200) scale(1.62)">'
    else:
        transform = "<g>"

    return svg(600, 600, f'<rect width="600" height="600" fill="{background}"/>{transform}{SHADOW}{art}</g>')


def hero_svg(ring_colour: str, shape_name: str, colours: Palette, options: dict[str, bool] | None = None) -> str:
    art = SHAPES[shape_name](colours, **(options or {}))

    return svg(
        700,
        700,
        f'<circle cx="350" cy="350" r="330" fill="{ring_colour}"/>'
        f'\n     <g transform="translate(50 42) scale(1.02)">{art}</g>'
        f'\n     <circle cx="96" cy="150" r="16" fill="#ffffff" opacity="0.65"/>'
        f'\n     <circle cx="604" cy="214" r="10" fill="#ffffff" opacity="0.5"/>'
        f'\n     <circle cx="576" cy="556" r="22" fill="#ffffff" opacity="0.45"/>',
    )


# ---------------------------------------------------------------------------
# Write everything
# ---------------------------------------------------------------------------
def main() -> int:
    written = 0

    def write(folder: str, filename: str, contents: str) -> None:
        nonlocal written
        directory = OUT / folder
        directory.mkdir(parents=True, exist_ok=True)
        (directory / filename).write_text(contents, encoding="utf-8", newline="")
        written += 1

    for name, shape_name, colours, options in PRODUCTS:
        write("products", f"{name}.svg", product_svg(shape_name, colours, options, "main"))
        write("products", f"{name}-alt.svg", product_svg(shape_name, colours, options, "alt"))
        write("products", f"{name}-detail.svg", product_svg(shape_name, colours, options, "detail"))

    # Fallback used by the templates when an image 404s.
    write(
        "products",
        "placeholder.svg",
        svg(
            600,
            600,
            '<rect width="600" height="600" fill="#f1f0ef"/>'
            '\n     <rect x="180" y="180" width="240" height="240" rx="24" fill="none" stroke="#c9c6c2" stroke-width="8"/>'
            '\n     <path d="M212 372 L272 300 L318 350 L358 312 L388 372 Z" fill="#c9c6c2"/>'
            '\n     <circle cx="252" cy="252" r="22" fill="#c9c6c2"/>',
        ),
    )

    for name, body in SCENES.items():
        write("blog", f"{name}.svg", svg(600, 400, body))

    write("hero", "slide-1.svg", hero_svg("#e3ded9", "dress", {"main": "#e5b4b8", "shade": "#cf979d", "trim": "#a86f76"}))
    write("hero", "slide-2.svg", hero_svg("#dfe3e6", "coat", {"main": "#c9a271", "shade": "#ad855a", "trim": "#8a6740"}))
    write("hero", "slide-3.svg", hero_svg("#e6e2da", "backpack", {"main": "#33333a", "shade": "#22222a", "trim": "#6d6d78"}))

    write("about", "studio.svg", svg(600, 400, SCENES["atelier"]))
    write("about", "workshop.svg", svg(600, 400, SCENES["workshop"]))

    (ROOT / "public" / "favicon.svg").write_text(
        svg(
            64,
            64,
            '<rect width="64" height="64" rx="14" fill="#111111"/>'
            '\n     <circle cx="26" cy="30" r="13" fill="none" stroke="#ffffff" stroke-width="5"/>'
            '\n     <path d="M34 38 L42 47" stroke="#ffffff" stroke-width="5" stroke-linecap="round"/>'
            '\n     <rect x="44" y="18" width="5" height="26" rx="2.5" fill="#ffffff"/>',
        ),
        encoding="utf-8",
        newline="",
    )

    print(f"Generated {written + 1} SVG assets into public/images")
    return 0


if __name__ == "__main__":
    sys.exit(main())
