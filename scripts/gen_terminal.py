"""Render the neofetch-style profile card as an animated SVG.

Usage: python scripts/gen_terminal.py <data.json> <site.json> <assets/ascii-art.txt> <out.svg>

Counts come from the GitHub API (data.json); everything else is read from the
website's published contract (site.json) so the card cannot drift from the site.
"""
import json, sys, io

DATA, SITE, ART, OUT = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

d = json.load(open(DATA, encoding="utf-8"))["data"]["user"]
total = d["contributionsCollection"]["contributionCalendar"]["totalContributions"]
n_repos = len(d["repositories"]["nodes"])

site = json.load(open(SITE, encoding="utf-8"))
p = site["profile"]
skills = {g["title"]: g["skills"] for g in site["skillGroups"]}
featured = site["projects"]["featured"]
jobs = site["experiences"]

ascii_lines = open(ART, encoding="utf-8").read().rstrip("\n").split("\n")

VALUE_BUDGET = 36  # characters that fit in the value column at 15px monospace


def fit(items, budget=VALUE_BUDGET):
    """Join as many items as fit the value column, noting how many were dropped.

    An item that is too long on its own is truncated rather than dropped, so a
    single long value never collapses to a bare "+1".
    """
    if len(items) == 1:
        only = items[0]
        return only if len(only) <= budget else only[:budget - 1].rstrip() + "…"

    out, used, skipped = [], 0, 0
    for item in items:
        add = len(item) + (2 if out else 0)
        if used + add <= budget:
            out.append(item)
            used += add
        else:
            skipped += 1
    while out and skipped and used + len(f" +{skipped}") > budget:
        used -= len(out[-1]) + (2 if len(out) > 1 else 0)
        out.pop()
        skipped += 1
    return ", ".join(out) + (f" +{skipped}" if skipped else "")


def host(url):
    return url.split("//")[-1].rstrip("/")


recent = jobs[0]
GROUPS = [
    [("Location", p["location"]),
     ("Uptime", "GitHub since Jul 2020"),
     ("Recent.Role", fit([recent["role"]])),
     ("Recent.Company", fit([recent["company"]])),
     ("Recent.Period", recent["period"])],
    [("Languages.Programming", fit(skills.get("Languages", []))),
     ("Languages.Web", fit(skills.get("Frontend", []))),
     ("Stack.Backend", fit(skills.get("Backend and data", [])))],
    [("Stack.Cloud", fit(skills.get("Cloud and ops", []))),
     ("Stack.AI", fit(skills.get("AI and automation", [])))],
    [("Contact.Website", host(site["site"])),
     ("Contact.LinkedIn", host(p["linkedinHref"]).replace("www.linkedin.com/in/", "")),
     ("Contact.Email", p["email"])],
    [("GitHub.Repos", f"{n_repos} public non-fork repos"),
     ("GitHub.Contributions", f"{total:,} in the last year"),
     ("GitHub.Featured", fit([x["title"] for x in featured]))],
]

DOT_COL = 30
CELL = 9.03
CMD = "neofetch --profile dgodolias"
T_FRAME, T_CMD, CMD_DUR = 0.15, 0.55, 1.05
T_ASCII, T_ROWS, ROW_STEP = 1.85, 2.00, 0.085

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

rows, y, delay = [], 52, T_ROWS
for group in GROUPS:
    for key, val in group:
        dots = " " + "." * max(3, DOT_COL - len(key)) + " "
        rows.append((y, key, dots, val, round(delay, 3)))
        y += 24
        delay += ROW_STEP
    y += 18
T_FOOTER = round(delay + 0.15, 3)
T_CURSOR = round(delay + 0.35, 3)

out = io.StringIO()
w = out.write

w('<svg width="1320" height="720" viewBox="0 0 1320 720" fill="none" '
  'xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">\n')
w('  <title id="title">dgodolias terminal profile README</title>\n')
w('  <desc id="desc">An animated neofetch-style GitHub profile card for Dimosthenis Gkontolias.</desc>\n')

w('''  <style>
    .mono, .caption, .ascii, .handle, .prompt, .cmd, .foot, .foot-hi {
      font-family: "Cascadia Mono", "Consolas", "SF Mono", "Liberation Mono", "DejaVu Sans Mono", monospace;
    }
    .page { fill: #0d1117; }
    .frame { fill: #161b22; stroke: #8b949e; stroke-width: 1.2; }
    .bar { fill: #0d1117; opacity: .86; }
    .caption { fill: #f0f6fc; font-size: 15px; font-weight: 600; }
    .handle { fill: #f0f6fc; font-size: 22px; font-weight: 500; }
    .rule { stroke: #8b949e; stroke-width: 1; opacity: .8; }
    .ascii { fill: #dbe7f3; font-size: 9.2px; }
    .mono { font-size: 15px; }
    .key { fill: #ff9f43; font-weight: 600; }
    .dots { fill: #6e7681; }
    .value { fill: #79c0ff; }
    .prompt { fill: #3fb950; font-size: 15px; font-weight: 600; }
    .cmd { fill: #f0f6fc; font-size: 15px; }
    .foot { fill: #6e7681; font-size: 12.5px; }
    .foot-hi { fill: #8b949e; font-size: 12.5px; }

    @keyframes fadeUp { from { opacity: 0; transform: translateY(7px); } to { opacity: 1; transform: none; } }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    @keyframes blink  { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }
    @keyframes pulse  { 0%, 100% { opacity: .45; } 50% { opacity: 1; } }

    .an-frame { opacity: 0; animation: fadeIn .5s ease-out ''' + f"{T_FRAME}s" + ''' forwards; }
    .an-ascii { opacity: 0; animation: fadeIn 1.1s ease-out ''' + f"{T_ASCII}s" + ''' forwards; }
    .row      { opacity: 0; animation: fadeUp .42s cubic-bezier(.2,.7,.3,1) forwards; }
    .an-foot  { opacity: 0; animation: fadeIn .6s ease-out ''' + f"{T_FOOTER}s" + ''' forwards; }
    .caret    { opacity: 0; animation: blink 1.06s step-end ''' + f"{T_CURSOR}s" + ''' infinite; }
    .live     { animation: pulse 2.4s ease-in-out infinite; }

    @media (prefers-reduced-motion: reduce) {
      .an-frame, .an-ascii, .row, .an-foot { opacity: 1; animation: none; }
      .caret { opacity: 1; animation: none; }
      .live  { animation: none; }
    }
  </style>
''')

steps = [round(i * CELL, 2) for i in range(len(CMD) + 1)]
w('  <defs>\n    <clipPath id="typeclip">\n')
w('      <rect x="-4" y="-18" width="0" height="26">\n')
w(f'        <animate attributeName="width" dur="{CMD_DUR}s" begin="{T_CMD}s" fill="freeze" '
  f'calcMode="discrete" values="{";".join(str(s) for s in steps)}"/>\n')
w('      </rect>\n    </clipPath>\n  </defs>\n\n')

w('  <rect class="page" width="1320" height="720" rx="16"/>\n')
w('  <g class="an-frame">\n')
w('    <rect class="frame" x="18" y="18" width="1284" height="684" rx="14"/>\n')
w('    <rect class="bar" x="38" y="78" width="1244" height="606" rx="13"/>\n')
w('    <circle cx="64" cy="47" r="7" fill="#f85149"/>\n')
w('    <circle cx="88" cy="47" r="7" fill="#d29922"/>\n')
w('    <circle cx="112" cy="47" r="7" fill="#3fb950"/>\n')
w('    <text class="caption" x="136" y="52">dgodolias / README.md</text>\n')
w('  </g>\n\n')

w('  <g transform="translate(60 112)">\n')
w('    <text class="prompt" x="0" y="0">$</text>\n')
w('    <g clip-path="url(#typeclip)" transform="translate(18 0)">\n')
w(f'      <text class="cmd" x="0" y="0">{CMD}</text>\n')
w('    </g>\n')
w(f'    <rect class="caret" x="{round(18 + len(CMD) * CELL + 4, 1)}" y="-12" width="9" height="16" fill="#3fb950"/>\n')
w('  </g>\n\n')

w('  <g class="an-ascii" transform="translate(54 150)">\n')
for i, line in enumerate(ascii_lines):
    w(f'    <text class="ascii" x="0" y="{i * 12}">{esc(line)}</text>\n')
w('  </g>\n\n')

w('  <g class="mono" transform="translate(645 142)">\n')
w(f'    <text class="handle row" x="0" y="0" style="animation-delay:{round(T_ROWS - 0.18, 3)}s">dimosthenis@github</text>\n')
w(f'    <line class="rule row" x1="0" y1="18" x2="610" y2="18" style="animation-delay:{round(T_ROWS - 0.09, 3)}s"/>\n')
for yy, key, dots, val, dly in rows:
    w(f'    <text class="row" x="0" y="{yy}" style="animation-delay:{dly}s">'
      f'<tspan class="key">{esc(key)}</tspan>'
      f'<tspan class="dots">{dots}</tspan>'
      f'<tspan class="value">{esc(val)}</tspan></text>\n')
w('  </g>\n\n')

w('  <g class="an-foot">\n')
w('    <line class="rule" x1="60" y1="650" x2="1260" y2="650" opacity=".35"/>\n')
w('    <circle class="live" cx="66" cy="672" r="4.5" fill="#3fb950"/>\n')
w('    <text class="foot" x="80" y="676">open to work'
  '<tspan class="foot" opacity=".5">  &#183;  </tspan>'
  '<tspan class="foot-hi">main</tspan>'
  '<tspan class="foot" opacity=".5">  &#183;  </tspan>'
  'built with too much coffee</text>\n')
w('    <text class="foot-hi" x="1260" y="676" text-anchor="end">dimosthenisgkontolias.com</text>\n')
w('  </g>\n')
w('</svg>\n')

open(OUT, "w", encoding="utf-8", newline="\n").write(out.getvalue())
print(f"wrote {OUT}: {n_repos} repos, {total:,} contributions", file=sys.stderr)
