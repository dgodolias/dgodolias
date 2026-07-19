"""Render the GitHub contribution calendar as a self-contained animated SVG.

Usage: python scripts/gen_contributions.py <calendar.json> <out.svg>

The card draws itself in, then a snake walks the whole grid eating every
contribution and the graph regrows on loop. Everything is plain SVG + SMIL/CSS:
no scripts, no third-party services, no network access at render time.
"""
import json, sys, io
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

cal = json.load(open(IN, encoding="utf-8"))["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = cal["weeks"]
total = cal["totalContributions"]

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
PERIOD = 19.0            # one full lap of the grid

# The snake starts short and grows as it eats. A cell is worth its contribution
# level, so a dark-green day feeds the snake four times as much as a faint one.
SEG_MIN, SEG_MAX = 4, 42
FOOD = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
        "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
HEAD_RGB, TAIL_RGB = (0x39, 0xd3, 0x53), (0x0e, 0x44, 0x29)


def seg_color(t):
    """Blend head colour into tail colour along the body."""
    return "#%02x%02x%02x" % tuple(
        round(h + (tl - h) * t) for h, tl in zip(HEAD_RGB, TAIL_RGB)
    )

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def cx(wi):
    return round(GRID_X + wi * PITCH + CELL / 2, 1)

def cy(wd):
    return round(GRID_Y + wd * PITCH + CELL / 2, 1)

# ---- serpentine path over every cell, column by column ------------------
level_at = {}
for wi, wk in enumerate(weeks):
    for day in wk["contributionDays"]:
        level_at[(wi, day["weekday"])] = day["contributionLevel"]

order, pts = [], []
for wi in range(len(weeks)):
    days = range(7) if wi % 2 == 0 else range(6, -1, -1)
    for wd in days:
        order.append((wi, wd))
        pts.append((cx(wi), cy(wd)))
STEPS = len(pts)
step_at = {wd_wi: i for i, wd_wi in enumerate(order)}
DT = PERIOD / STEPS

# Cumulative food eaten after each step, normalised so the snake reaches exactly
# SEG_MAX at the end of the lap however dense the year happened to be.
eaten, run = [], 0
for wi, wd in order:
    run += FOOD.get(level_at.get((wi, wd), "NONE"), 0)
    eaten.append(run)
total_food = eaten[-1] or 1
# grow_at[i] = fraction of the lap at which body segment i appears
grow_at = []
for i in range(SEG_MIN, SEG_MAX):
    need = (i - SEG_MIN + 1) / (SEG_MAX - SEG_MIN) * total_food
    step = next((k for k, v in enumerate(eaten) if v >= need), STEPS - 1)
    grow_at.append(round(step / STEPS, 5))

out = io.StringIO()
w = out.write

w(f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" '
  'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
  'role="img" aria-labelledby="t d">\n')
w('  <title id="t">dgodolias contribution graph</title>\n')
w(f'  <desc id="d">{total} contributions in the last year, rendered from the GitHub GraphQL API, '
  'with a snake eating the grid.</desc>\n')

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
    /* Revealed only once every segment's motion has begun, so none of them are
       caught sitting at the SVG origin waiting for their turn. */
    .snake    { opacity: 0; animation: fadeIn .4s ease-out ''' + f"{round(T_SNAKE + (SEG_MIN - 1) * DT, 4)}s" + ''' forwards; }

    /* A static, readable card for anyone who asked the OS for less motion. */
    @media (prefers-reduced-motion: reduce) {
      .an-frame, .an-lab, .cell, .an-foot { opacity: 1; animation: none; }
      .caret { opacity: 1; animation: none; }
      .snake { display: none; }
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
path_d = "M" + " L".join(f"{x},{y}" for x, y in pts)
w(f'    <path id="snakepath" d="{path_d}"/>\n')
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
# Cells fade in on a diagonal sweep, then each one is "eaten" the instant the
# snake's head reaches it and regrows as the lap restarts.
w('  <g>\n')
for wi, wk in enumerate(weeks):
    for day in wk["contributionDays"]:
        wd = day["weekday"]
        x = round(GRID_X + wi * PITCH, 1)
        y = round(GRID_Y + wd * PITCH, 1)
        lvl = day["contributionLevel"]
        fill = LEVEL.get(lvl, LEVEL["NONE"])
        delay = round(T_GRID + wi * W_STEP + wd * D_STEP, 3)
        n = day["contributionCount"]
        tip = f'{n} contribution{"" if n == 1 else "s"} on {day["date"]}'
        w(f'    <rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{CELL_R}" '
          f'fill="{fill}" style="animation-delay:{delay}s">')
        if lvl != "NONE":
            f = round(step_at[(wi, wd)] / STEPS, 5)
            w(f'<animate attributeName="fill" dur="{PERIOD}s" begin="{T_SNAKE}s" '
              f'repeatCount="indefinite" calcMode="discrete" '
              f'values="{fill};{LEVEL["NONE"]};{LEVEL["NONE"]};{fill}" '
              f'keyTimes="0;{f};0.995;1"/>')
        w(f'<title>{tip}</title></rect>\n')
w('  </g>\n\n')

# ---- the snake ----------------------------------------------------------
w('  <g class="snake">\n')
for i in range(SEG_MAX):
    t = i / (SEG_MAX - 1)
    s = round(CELL * (1.0 - 0.45 * t), 2)
    half = round(s / 2, 2)
    extra = ' filter="url(#glow)"' if i == 0 else ""
    # No transform attribute here: animateMotion contributes its own transform,
    # and a static translate would stack on top of it and push the snake off-grid.
    w(f'    <rect x="{-half}" y="{-half}" width="{s}" height="{s}" rx="{round(s * 0.3, 2)}" '
      f'fill="{seg_color(t)}"{extra}')
    if i >= SEG_MIN:
        # This segment only exists once the snake has eaten enough to earn it.
        f = grow_at[i - SEG_MIN]
        w(f' opacity="0">\n')
        w(f'      <animate attributeName="opacity" dur="{PERIOD}s" begin="{T_SNAKE}s" '
          f'repeatCount="indefinite" calcMode="discrete" values="0;1;1;0" '
          f'keyTimes="0;{f};0.995;1"/>\n')
    else:
        w('>\n')
    w(f'      <animateMotion dur="{PERIOD}s" begin="{round(T_SNAKE + i * DT, 4)}s" '
      f'repeatCount="indefinite" rotate="0">\n')
    w('        <mpath xlink:href="#snakepath" href="#snakepath"/>\n')
    w('      </animateMotion>\n')
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
print(f"wrote {OUT}: {total} contributions, {len(weeks)} weeks, "
      f"snake over {STEPS} cells in {PERIOD}s", file=sys.stderr)
