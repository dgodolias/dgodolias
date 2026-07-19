"""Render the GitHub contribution calendar as a self-contained animated SVG.

Usage: python scripts/gen_contributions.py <calendar.json> <out.svg>

One master cycle: the card draws itself in, a snake walks the whole grid eating
every contribution and growing as it feeds, then it detonates, the grid spells
DIMOS next to a winking face, detonates again, and the year grows back.

Everything is plain SVG + SMIL/CSS: no scripts, no third-party services, no
network access at render time. Every looping animation is anchored to the same
begin time and the same master duration, which is what keeps the snake, the
eaten cells, the letters and the explosions in step.
"""
import json, sys, io, math
from datetime import date

IN, OUT = sys.argv[1], sys.argv[2]

# GitHub's own dark-theme palette, keyed by the API's contributionLevel enum,
# so the card matches the graph rendered on the profile page.
LEVEL = {
    "NONE":             "#161b22",
    "FIRST_QUARTILE":   "#0e4429",
    "SECOND_QUARTILE":  "#006d32",
    "THIRD_QUARTILE":   "#26a641",
    "FOURTH_QUARTILE":  "#39d353",
}
ORDER = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
LIT = "#39d353"

cal = json.load(open(IN, encoding="utf-8"))["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = cal["weeks"]
total = cal["totalContributions"]
NW = len(weeks)

W, H = 1320, 420
GRID_X, GRID_Y = 106, 160
CELL, GAP = 17.0, 4.8
PITCH = CELL + GAP
CELL_R = 3.5
MONO = 9.03  # monospace advance at 15px

CMD = "gh api graphql --contributions --user dgodolias"
T_CMD, CMD_DUR = 0.45, 0.95
T_GRID = 1.45
W_STEP, D_STEP = 0.009, 0.003
T_SNAKE = 2.65

# ---- the master cycle ---------------------------------------------------
LAP     = 14.5   # snake crosses the whole grid
EXP1    = 0.80   # first detonation
SHOW    = 3.20   # DIMOS + winking face held
EXP2    = 0.80   # second detonation
REGROW  = 1.90   # year grows back and rests before the next lap
MASTER  = LAP + EXP1 + SHOW + EXP2 + REGROW

f_lap     = LAP / MASTER
f_exp1_e  = (LAP + EXP1) / MASTER
f_show_s  = (LAP + EXP1 * 0.55) / MASTER      # letters appear inside the blast
f_show_e  = (LAP + EXP1 + SHOW) / MASTER
f_exp2_e  = (LAP + EXP1 + SHOW + EXP2) / MASTER
f_regrow  = f_exp2_e + 0.004

SEG_MIN, SEG_MAX = 4, 42
FOOD = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
        "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
HEAD_RGB, TAIL_RGB = (0x39, 0xd3, 0x53), (0x0e, 0x44, 0x29)

# ---- 5x7 pixel font, plus a 7x7 winking face ----------------------------
FONT = {
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
}
FACE = [
    ".......",
    ".......",
    ".#..##.",   # open eye, then the winking eye as a dash
    ".......",
    "#.....#",
    ".#####.",   # smile
    ".......",
]
WORD = "DIMOS"


def seg_color(t):
    """Blend head colour into tail colour along the body."""
    return "#%02x%02x%02x" % tuple(
        round(h + (tl - h) * t) for h, tl in zip(HEAD_RGB, TAIL_RGB)
    )


def build_mask():
    """Cells that light up for the DIMOS + face frame, centred on the grid."""
    word_w = len(WORD) * 5 + (len(WORD) - 1)
    face_w = len(FACE[0])
    span = word_w + 3 + face_w
    start = max(0, (NW - 1 - span) // 2)
    mask, col = set(), start
    for ch in WORD:
        for r, row in enumerate(FONT[ch]):
            for c, px in enumerate(row):
                if px == "#":
                    mask.add((col + c, r))
        col += 6
    col += 2
    for r, row in enumerate(FACE):
        for c, px in enumerate(row):
            if px == "#":
                mask.add((col + c, r))
    return mask


MASK = build_mask()


def cx(wi):
    return round(GRID_X + wi * PITCH + CELL / 2, 1)


def cy(wd):
    return round(GRID_Y + wd * PITCH + CELL / 2, 1)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


level_at = {}
for wi, wk in enumerate(weeks):
    for day in wk["contributionDays"]:
        level_at[(wi, day["weekday"])] = day["contributionLevel"]

# ---- serpentine path over every cell, column by column ------------------
order, pts = [], []
for wi in range(NW):
    days = range(7) if wi % 2 == 0 else range(6, -1, -1)
    for wd in days:
        order.append((wi, wd))
        pts.append((cx(wi), cy(wd)))
STEPS = len(pts)
step_at = {k: i for i, k in enumerate(order)}
DT = LAP / STEPS

# Cumulative food eaten after each step, normalised so the snake reaches exactly
# SEG_MAX at the end of the lap however dense the year happened to be.
eaten, run = [], 0
for wi, wd in order:
    run += FOOD.get(level_at.get((wi, wd), "NONE"), 0)
    eaten.append(run)
total_food = eaten[-1] or 1
grow_at = []
for i in range(SEG_MIN, SEG_MAX):
    need = (i - SEG_MIN + 1) / (SEG_MAX - SEG_MIN) * total_food
    step = next((k for k, v in enumerate(eaten) if v >= need), STEPS - 1)
    grow_at.append(step / STEPS * f_lap)

BLAST_X = round(GRID_X + (NW - 1) * PITCH / 2 + CELL / 2, 1)
BLAST_Y = round(GRID_Y + 3 * PITCH + CELL / 2, 1)

out = io.StringIO()
w = out.write

w(f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" '
  'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
  'role="img" aria-labelledby="t d">\n')
w('  <title id="t">dgodolias contribution graph</title>\n')
w(f'  <desc id="d">{total} contributions in the last year, rendered from the GitHub GraphQL API, '
  'with a snake that eats the grid and spells DIMOS.</desc>\n')

w('''  <style>
    .caption, .prompt, .cmd, .lab, .foot {
      font-family: "Cascadia Mono", "Consolas", "SF Mono", "Liberation Mono", "DejaVu Sans Mono", monospace;
    }
    .page { fill: #0d1117; }
    .frame { fill: #161b22; stroke: #8b949e; stroke-width: 1.2; }
    .bar { fill: #0d1117; opacity: .86; }
    .caption { fill: #f0f6fc; font-size: 15px; font-weight: 600; }
    .prompt { fill: #3fb950; font-size: 15px; font-weight: 600; }
    .cmd { fill: #f0f6fc; font-size: 15px; }
    .lab { fill: #6e7681; font-size: 11.5px; }
    .foot { fill: #6e7681; font-size: 12.5px; }
    .foot-hi { fill: #39d353; font-weight: 600; }
    .cell { stroke: #f0f6fc; stroke-opacity: .05; stroke-width: 1; }

    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    @keyframes pop    { from { opacity: 0; transform: translateY(-3px); } to { opacity: 1; transform: none; } }
    @keyframes blink  { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }

    .an-frame { opacity: 0; animation: fadeIn .5s ease-out .12s forwards; }
    .an-lab   { opacity: 0; animation: fadeIn .5s ease-out ''' + f"{T_GRID - 0.15}s" + ''' forwards; }
    .cell     { opacity: 0; animation: pop .32s ease-out forwards; }
    .an-foot  { opacity: 0; animation: fadeIn .55s ease-out ''' + f"{T_GRID + 0.9}s" + ''' forwards; }
    .caret    { opacity: 0; animation: blink 1.06s step-end 1.42s infinite; }
    .stage    { opacity: 0; animation: fadeIn .3s ease-out ''' + f"{T_SNAKE}s" + ''' forwards; }

    /* A static, readable card for anyone who asked the OS for less motion. */
    @media (prefers-reduced-motion: reduce) {
      .an-frame, .an-lab, .cell, .an-foot { opacity: 1; animation: none; }
      .caret { opacity: 1; animation: none; }
      .stage { display: none; }
    }
  </style>
''')

steps_cmd = [round(i * MONO, 2) for i in range(len(CMD) + 1)]
w('  <defs>\n')
w('    <clipPath id="typeclip">\n')
w('      <rect x="-4" y="-18" width="0" height="26">\n')
w(f'        <animate attributeName="width" dur="{CMD_DUR}s" begin="{T_CMD}s" fill="freeze" '
  f'calcMode="discrete" values="{";".join(str(s) for s in steps_cmd)}"/>\n')
w('      </rect>\n    </clipPath>\n')
w('    <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">\n')
w('      <feGaussianBlur stdDeviation="3.2" result="b"/>\n')
w('      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>\n')
w('    </filter>\n')
w(f'    <path id="snakepath" d="M{" L".join(f"{x},{y}" for x, y in pts)}"/>\n')
w('  </defs>\n\n')

w(f'  <rect class="page" width="{W}" height="{H}" rx="16"/>\n')
w('  <g class="an-frame">\n')
w('    <rect class="frame" x="18" y="18" width="1284" height="384" rx="14"/>\n')
w('    <rect class="bar" x="38" y="78" width="1244" height="306" rx="13"/>\n')
w('    <circle cx="64" cy="47" r="7" fill="#f85149"/>\n')
w('    <circle cx="88" cy="47" r="7" fill="#d29922"/>\n')
w('    <circle cx="112" cy="47" r="7" fill="#3fb950"/>\n')
w('    <text class="caption" x="136" y="52">dgodolias / contributions</text>\n')
w('  </g>\n\n')

w('  <g transform="translate(60 112)">\n')
w('    <text class="prompt" x="0" y="0">$</text>\n')
w('    <g clip-path="url(#typeclip)" transform="translate(18 0)">\n')
w(f'      <text class="cmd" x="0" y="0">{esc(CMD)}</text>\n')
w('    </g>\n')
w(f'    <rect class="caret" x="{round(18 + len(CMD) * MONO + 4, 1)}" y="-12" '
  'width="9" height="16" fill="#3fb950"/>\n')
w('  </g>\n\n')

# ---- month + weekday labels --------------------------------------------
w('  <g class="an-lab">\n')
labels, prev_month, last_x = [], None, -999
for wi, wk in enumerate(weeks):
    dt = date.fromisoformat(wk["firstDay"])
    if dt.month != prev_month:
        prev_month = dt.month
        if wi != 0 and dt.day > 7:
            continue
        x = round(GRID_X + wi * PITCH, 1)
        if x - last_x >= 28 and x < GRID_X + 52 * PITCH:
            labels.append((x, MONTHS[dt.month - 1]))
            last_x = x
for x, name in labels:
    w(f'    <text class="lab" x="{x}" y="148">{name}</text>\n')
for wd, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
    w(f'    <text class="lab" x="96" y="{round(GRID_Y + wd * PITCH + CELL * 0.72, 1)}" '
      f'text-anchor="end">{name}</text>\n')
w('  </g>\n\n')

# ---- the grid -----------------------------------------------------------
# Each cell is eaten the instant the snake's head reaches it, lights up if it is
# part of the DIMOS frame, and grows back after the second detonation.
w('  <g>\n')
for wi, wk in enumerate(weeks):
    for day in wk["contributionDays"]:
        wd = day["weekday"]
        x = round(GRID_X + wi * PITCH, 1)
        y = round(GRID_Y + wd * PITCH, 1)
        lvl = day["contributionLevel"]
        fill = LEVEL.get(lvl, LEVEL["NONE"])
        none = LEVEL["NONE"]
        delay = round(T_GRID + wi * W_STEP + wd * D_STEP, 3)
        n = day["contributionCount"]
        in_mask = (wi, wd) in MASK
        w(f'    <rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{CELL_R}" '
          f'fill="{fill}" style="animation-delay:{delay}s">')
        if lvl != "NONE" or in_mask:
            f_eat = round(step_at[(wi, wd)] / STEPS * f_lap, 5)
            if in_mask:
                vals = f"{fill};{none};{LIT};{none};{fill};{fill}"
                keys = f"0;{f_eat};{round(f_show_s, 5)};{round(f_show_e, 5)};{round(f_regrow, 5)};1"
            else:
                vals = f"{fill};{none};{fill};{fill}"
                keys = f"0;{f_eat};{round(f_regrow, 5)};1"
            w(f'<animate attributeName="fill" dur="{MASTER}s" begin="{T_SNAKE}s" '
              f'repeatCount="indefinite" calcMode="discrete" values="{vals}" keyTimes="{keys}"/>')
        w(f'<title>{n} contribution{"" if n == 1 else "s"} on {day["date"]}</title></rect>\n')
w('  </g>\n\n')

w('  <g class="stage">\n')

# ---- the snake ----------------------------------------------------------
# animateMotion runs on the master clock via keyPoints: each segment waits its
# turn, crosses the grid over one lap, then holds until the cycle restarts.
for i in range(SEG_MAX):
    t = i / (SEG_MAX - 1)
    s = round(CELL * (1.0 - 0.45 * t), 2)
    half = round(s / 2, 2)
    lag = round(i * DT / MASTER, 5)
    end = round(lag + f_lap, 5)
    show = round(grow_at[i - SEG_MIN], 5) if i >= SEG_MIN else lag
    extra = ' filter="url(#glow)"' if i == 0 else ""
    # No transform attribute here: animateMotion contributes its own transform,
    # and a static translate would stack on top of it and push the snake off-grid.
    w(f'    <rect x="{-half}" y="{-half}" width="{s}" height="{s}" rx="{round(s * 0.3, 2)}" '
      f'fill="{seg_color(t)}"{extra} opacity="0">\n')
    w(f'      <animate attributeName="opacity" dur="{MASTER}s" begin="{T_SNAKE}s" '
      f'repeatCount="indefinite" calcMode="discrete" values="0;1;0;0" '
      f'keyTimes="0;{show};{round(f_lap, 5)};1"/>\n')
    w(f'      <animateMotion dur="{MASTER}s" begin="{T_SNAKE}s" repeatCount="indefinite" '
      f'rotate="0" calcMode="linear" keyPoints="0;0;1;1" keyTimes="0;{lag};{min(end, 0.999)};1">\n')
    w('        <mpath xlink:href="#snakepath" href="#snakepath"/>\n')
    w('      </animateMotion>\n')
    w('    </rect>\n')

# ---- the two detonations ------------------------------------------------
PARTICLES = 34
SPARK = ["#39d353", "#26a641", "#f0f6fc", "#2ea043", "#d29922"]
for burst, (s_frac, e_frac) in enumerate(((f_lap, f_exp1_e), (f_show_e, f_exp2_e))):
    for i in range(PARTICLES):
        ang = (i / PARTICLES) * math.tau + (0.11 if burst else 0.0)
        dist = 96 + 74 * ((i * 7) % 5) / 4
        dx, dy = round(math.cos(ang) * dist, 1), round(math.sin(ang) * dist * 0.62, 1)
        sz = 5 + (i % 3) * 2
        col = SPARK[i % len(SPARK)]
        mid = round(s_frac + (e_frac - s_frac) * 0.45, 5)
        w(f'    <rect x="{-sz / 2}" y="{-sz / 2}" width="{sz}" height="{sz}" rx="{sz / 2}" '
          f'fill="{col}" opacity="0" transform="translate({BLAST_X} {BLAST_Y})">\n')
        w(f'      <animateTransform attributeName="transform" type="translate" dur="{MASTER}s" '
          f'begin="{T_SNAKE}s" repeatCount="indefinite" calcMode="spline" '
          f'values="{BLAST_X},{BLAST_Y};{BLAST_X},{BLAST_Y};'
          f'{round(BLAST_X + dx, 1)},{round(BLAST_Y + dy, 1)};'
          f'{round(BLAST_X + dx, 1)},{round(BLAST_Y + dy, 1)}" '
          f'keyTimes="0;{round(s_frac, 5)};{round(e_frac, 5)};1" '
          'keySplines="0 0 1 1;0.12 0.8 0.25 1;0 0 1 1"/>\n')
        w(f'      <animate attributeName="opacity" dur="{MASTER}s" begin="{T_SNAKE}s" '
          f'repeatCount="indefinite" calcMode="linear" values="0;0;1;0;0" '
          f'keyTimes="0;{round(s_frac, 5)};{mid};{round(e_frac, 5)};1"/>\n')
        w('    </rect>\n')

    # a short flash across the grid to sell the impact
    w(f'    <rect x="{GRID_X - 10}" y="{GRID_Y - 10}" width="{round((NW - 1) * PITCH + CELL + 20, 1)}" '
      f'height="{round(6 * PITCH + CELL + 20, 1)}" rx="10" fill="#39d353" opacity="0">\n')
    w(f'      <animate attributeName="opacity" dur="{MASTER}s" begin="{T_SNAKE}s" '
      f'repeatCount="indefinite" calcMode="linear" values="0;0;0.18;0;0" '
      f'keyTimes="0;{round(s_frac, 5)};{round(s_frac + (e_frac - s_frac) * 0.2, 5)};'
      f'{round(e_frac, 5)};1"/>\n')
    w('    </rect>\n')

w('  </g>\n\n')

# ---- legend + footer ----------------------------------------------------
w('  <g class="an-foot">\n')
w(f'    <text class="foot" x="60" y="352"><tspan class="foot-hi">{total:,}</tspan> '
  'contributions in the last year</text>\n')
lx = 1262 - (len(ORDER) * (CELL - 3 + 4)) - 78
w(f'    <text class="lab" x="{lx}" y="352">Less</text>\n')
for i, lv in enumerate(ORDER):
    w(f'    <rect x="{round(lx + 34 + i * (CELL - 3 + 4), 1)}" y="342" width="{CELL - 3}" '
      f'height="{CELL - 3}" rx="3" fill="{LEVEL[lv]}" stroke="#f0f6fc" stroke-opacity=".05"/>\n')
w(f'    <text class="lab" x="{round(lx + 34 + len(ORDER) * (CELL - 3 + 4) + 6, 1)}" y="352">More</text>\n')
w('  </g>\n')
w('</svg>\n')

open(OUT, "w", encoding="utf-8", newline="\n").write(out.getvalue())
print(f"wrote {OUT}: {total} contributions, snake {LAP}s of a {MASTER}s cycle, "
      f"{len(MASK)} cells in the DIMOS frame", file=sys.stderr)
