"""Render the GitHub contribution calendar as a self-contained animated SVG.

Usage: python scripts/gen_contributions.py <calendar.json> <out.svg>

The JSON is the raw response of the GraphQL query in .github/workflows/refresh-cards.yml,
so this script has no network access and no third-party dependencies.
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
CELL_CELL = 9.03  # monospace advance at 15px

CMD = f"gh api graphql --contributions --user dgodolias"
T_CMD, CMD_DUR = 0.45, 0.95
T_GRID = 1.55
W_STEP, D_STEP = 0.011, 0.004

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

out = io.StringIO()
w = out.write

w(f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" '
  'xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="t d">\n')
w('  <title id="t">dgodolias contribution graph</title>\n')
w(f'  <desc id="d">{total} contributions in the last year, rendered from the GitHub GraphQL API.</desc>\n')

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
    @keyframes pop    { from { opacity: 0; } to { opacity: 1; } }
    @keyframes blink  { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }

    .an-frame { opacity: 0; animation: fadeIn .5s ease-out .12s forwards; }
    .an-lab   { opacity: 0; animation: fadeIn .5s ease-out ''' + f"{T_GRID - 0.15}s" + ''' forwards; }
    .cell     { opacity: 0; animation: pop .34s ease-out forwards; }
    .an-foot  { opacity: 0; animation: fadeIn .55s ease-out ''' + f"{T_GRID + 0.95}s" + ''' forwards; }
    .caret    { opacity: 0; animation: blink 1.06s step-end 1.42s infinite; }

    @media (prefers-reduced-motion: reduce) {
      .an-frame, .an-lab, .cell, .an-foot { opacity: 1; animation: none; }
      .caret { opacity: 1; animation: none; }
    }
  </style>
''')

steps = [round(i * CELL_CELL, 2) for i in range(len(CMD) + 1)]
w('  <defs>\n    <clipPath id="typeclip">\n')
w('      <rect x="-4" y="-18" width="0" height="26">\n')
w(f'        <animate attributeName="width" dur="{CMD_DUR}s" begin="{T_CMD}s" fill="freeze" '
  f'calcMode="discrete" values="{";".join(str(s) for s in steps)}"/>\n')
w('      </rect>\n    </clipPath>\n  </defs>\n\n')

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
w(f'    <rect class="caret" x="{round(18 + len(CMD) * CELL_CELL + 4, 1)}" y="-12" '
  'width="9" height="16" fill="#3fb950"/>\n')
w('  </g>\n\n')

# ---- month labels -------------------------------------------------------
w('  <g class="an-lab">\n')
# GitHub labels the leading (partial) month too, then each month at the first
# week that mostly belongs to it; skip labels that would collide.
labels, prev_month, last_x = [], None, -999
for wi, wk in enumerate(weeks):
    dt = date.fromisoformat(wk["firstDay"])
    is_new = dt.month != prev_month
    if is_new:
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
    y = round(GRID_Y + wd * PITCH + CELL * 0.72, 1)
    w(f'    <text class="lab" x="96" y="{y}" text-anchor="end">{name}</text>\n')
w('  </g>\n\n')

# ---- the grid -----------------------------------------------------------
w('  <g>\n')
for wi, wk in enumerate(weeks):
    for day in wk["contributionDays"]:
        wd = day["weekday"]
        x = round(GRID_X + wi * PITCH, 1)
        y = round(GRID_Y + wd * PITCH, 1)
        fill = LEVEL.get(day["contributionLevel"], LEVEL["NONE"])
        delay = round(T_GRID + wi * W_STEP + wd * D_STEP, 3)
        n = day["contributionCount"]
        w(f'    <rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{CELL_R}" '
          f'fill="{fill}" style="animation-delay:{delay}s">'
          f'<title>{n} contribution{"" if n == 1 else "s"} on {day["date"]}</title></rect>\n')
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
print(f"wrote {OUT}: {total} contributions, {len(weeks)} weeks", file=sys.stderr)
