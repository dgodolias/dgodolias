"""Render the language / stack card as an animated SVG.

Usage: python scripts/gen_stack.py <data.json> <site.json> <out.svg>

The bars are counted by *repository*, not by bytes: byte counts are dominated by
generated build output and notebook outputs, which misrepresents what is actually
written. The chips are the skill groups published by the website, so the card and
the site's Skills section can never disagree. The card height is derived from the
content, so adding a skill group on the site cannot overflow it.
"""
import json, sys, io, collections

DATA, SITE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

d = json.load(open(DATA, encoding="utf-8"))["data"]["user"]
total = d["contributionsCollection"]["contributionCalendar"]["totalContributions"]
repos = d["repositories"]["nodes"]
n_repos = len(repos)

counts, colors = collections.Counter(), {}
for r in repos:
    edges = r["languages"]["edges"]
    if edges:
        node = edges[0]["node"]
        counts[node["name"]] += 1
        colors[node["name"]] = node["color"] or "#8b949e"
LANGS = [(n, c, colors[n]) for n, c in counts.most_common(6)]

site = json.load(open(SITE, encoding="utf-8"))
MAX_CHIPS = 6
STACK = [(g["title"].lower(), g["skills"][:MAX_CHIPS]) for g in site["skillGroups"]]

W = 1320
MONO, CHIP_CELL, CHIP_PAD, CHIP_H, CHIP_GAP = 9.03, 7.0, 11, 26, 8
RIGHT_X, RIGHT_MAX = 668, 1262
BAR_X, BAR_W = 210, 350
CMD = "tokei --languages --by-repo"
T_CMD, CMD_DUR, T_BODY, STEP = 0.5, 0.95, 1.7, 0.09
LABEL_STEP, CHIP_STEP = 0.07, 0.04


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---- lay the right column out first, so the card can be sized to fit --------
chips, labels = [], []
y, rd = 196, T_BODY + 0.12
for label, items in STACK:
    labels.append((RIGHT_X, y, label, round(rd, 3)))
    rd += LABEL_STEP
    cx, cy = RIGHT_X, y + 12
    for it in items:
        cw = round(len(it) * CHIP_CELL + CHIP_PAD * 2, 1)
        if cx + cw > RIGHT_MAX:
            cx = RIGHT_X
            cy += CHIP_H + CHIP_GAP
        chips.append((cx, cy, cw, it, round(rd, 3)))
        cx += cw + CHIP_GAP
        rd += CHIP_STEP
    y = cy + CHIP_H + 26

right_bottom = y - 26
left_bottom = 202 + len(LANGS) * 38
RULE_Y = round(max(right_bottom, left_bottom) + 22)
FOOT_Y = RULE_Y + 22
H = FOOT_Y + 36
BAR_H = H - 78 - 36
T_FOOT = round(max(rd, T_BODY + 0.12 + len(LANGS) * STEP) + 0.12, 3)

out = io.StringIO()
w = out.write

w(f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" '
  'xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="t d">\n')
w('  <title id="t">dgodolias language and stack card</title>\n')
w('  <desc id="d">Languages by repository count and the tools Dimosthenis Gkontolias works with.</desc>\n')

w('''  <style>
    .mono, .caption, .prompt, .cmd, .lab, .val, .chip-t, .foot, .head {
      font-family: "Cascadia Mono", "Consolas", "SF Mono", "Liberation Mono", "DejaVu Sans Mono", monospace;
    }
    .page { fill: #0d1117; }
    .frame { fill: #161b22; stroke: #8b949e; stroke-width: 1.2; }
    .bar { fill: #0d1117; opacity: .86; }
    .caption { fill: #f0f6fc; font-size: 15px; font-weight: 600; }
    .prompt { fill: #3fb950; font-size: 15px; font-weight: 600; }
    .cmd { fill: #f0f6fc; font-size: 15px; }
    .head { fill: #6e7681; font-size: 11.5px; letter-spacing: 1.6px; font-weight: 600; }
    .lab { fill: #f0f6fc; font-size: 13px; }
    .val { fill: #6e7681; font-size: 12px; }
    .track { fill: #21262d; }
    .chip { fill: #161b22; stroke: #30363d; stroke-width: 1; }
    .chip-t { fill: #adbac7; font-size: 12.5px; }
    .foot { fill: #6e7681; font-size: 12.5px; }
    .foot-hi { fill: #79c0ff; }

    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    @keyframes fadeUp { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
    @keyframes blink  { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }

    .an-frame { opacity: 0; animation: fadeIn .5s ease-out .15s forwards; }
    .item     { opacity: 0; animation: fadeUp .42s cubic-bezier(.2,.7,.3,1) forwards; }
    .caret    { opacity: 0; animation: blink 1.06s step-end 1.5s infinite; }

    @media (prefers-reduced-motion: reduce) {
      .an-frame, .item { opacity: 1; animation: none; }
      .caret { opacity: 1; animation: none; }
      .grow  { display: none; }
    }
  </style>
''')

steps = [round(i * MONO, 2) for i in range(len(CMD) + 1)]
w('  <defs>\n    <clipPath id="typeclip">\n')
w('      <rect x="-4" y="-18" width="0" height="26">\n')
w(f'        <animate attributeName="width" dur="{CMD_DUR}s" begin="{T_CMD}s" fill="freeze" '
  f'calcMode="discrete" values="{";".join(str(s) for s in steps)}"/>\n')
w('      </rect>\n    </clipPath>\n  </defs>\n\n')

w(f'  <rect class="page" width="{W}" height="{H}" rx="16"/>\n')
w('  <g class="an-frame">\n')
w(f'    <rect class="frame" x="18" y="18" width="1284" height="{H - 36}" rx="14"/>\n')
w(f'    <rect class="bar" x="38" y="78" width="1244" height="{BAR_H}" rx="13"/>\n')
w('    <circle cx="64" cy="47" r="7" fill="#f85149"/>\n')
w('    <circle cx="88" cy="47" r="7" fill="#d29922"/>\n')
w('    <circle cx="112" cy="47" r="7" fill="#3fb950"/>\n')
w('    <text class="caption" x="136" y="52">dgodolias / stack</text>\n')
w('  </g>\n\n')

w('  <g transform="translate(60 112)">\n')
w('    <text class="prompt" x="0" y="0">$</text>\n')
w('    <g clip-path="url(#typeclip)" transform="translate(18 0)">\n')
w(f'      <text class="cmd" x="0" y="0">{CMD}</text>\n')
w('    </g>\n')
w(f'    <rect class="caret" x="{round(18 + len(CMD) * MONO + 4, 1)}" y="-12" width="9" height="16" fill="#3fb950"/>\n')
w('  </g>\n\n')

top = max(n for _, n, _ in LANGS)
w(f'  <text class="head item" x="60" y="168" style="animation-delay:{T_BODY}s">LANGUAGES &#183; BY REPOSITORY</text>\n')
yy = 202
for i, (name, n, color) in enumerate(LANGS):
    dly = round(T_BODY + 0.12 + i * STEP, 3)
    bw = round(BAR_W * n / top, 1)
    w(f'  <g class="item" style="animation-delay:{dly}s">\n')
    w(f'    <text class="lab" x="60" y="{yy + 4}">{esc(name)}</text>\n')
    w(f'    <rect class="track" x="{BAR_X}" y="{yy - 9}" width="{BAR_W}" height="12" rx="6"/>\n')
    w(f'    <rect class="grow" x="{BAR_X}" y="{yy - 9}" width="0" height="12" rx="6" fill="{color}">\n')
    w(f'      <animate attributeName="width" from="0" to="{bw}" dur=".85s" '
      f'begin="{round(dly + 0.1, 3)}s" fill="freeze" calcMode="spline" '
      'keySplines="0.2 0.7 0.3 1" keyTimes="0;1"/>\n')
    w('    </rect>\n')
    w(f'    <text class="val" x="{BAR_X + BAR_W + 14}" y="{yy + 3}">{n} repo{"" if n == 1 else "s"}</text>\n')
    w('  </g>\n')
    yy += 38

w(f'  <text class="head item" x="{RIGHT_X}" y="168" style="animation-delay:{T_BODY}s">STACK</text>\n')
for x, ly, label, dly in labels:
    w(f'  <text class="val item" x="{x}" y="{ly}" style="animation-delay:{dly}s">{esc(label)}</text>\n')
for x, cy, cw, text, dly in chips:
    w(f'  <g class="item" style="animation-delay:{dly}s">\n')
    w(f'    <rect class="chip" x="{x}" y="{cy}" width="{cw}" height="{CHIP_H}" rx="13"/>\n')
    w(f'    <text class="chip-t" x="{round(x + cw / 2, 1)}" y="{cy + 17}" '
      f'text-anchor="middle">{esc(text)}</text>\n')
    w('  </g>\n')

w(f'  <g class="item" style="animation-delay:{T_FOOT}s">\n')
w(f'    <line x1="60" y1="{RULE_Y}" x2="1262" y2="{RULE_Y}" stroke="#8b949e" stroke-width="1" opacity=".3"/>\n')
w(f'    <text class="foot" x="60" y="{FOOT_Y}">'
  f'<tspan class="foot-hi">{n_repos}</tspan> public repos'
  '<tspan opacity=".5">  &#183;  </tspan>'
  f'<tspan class="foot-hi">{total:,}</tspan> contributions in the last year'
  '<tspan opacity=".5">  &#183;  </tspan>'
  'skills mirrored from <tspan class="foot-hi">dimosthenisgkontolias.com</tspan></text>\n')
w(f'    <text class="foot" x="1262" y="{FOOT_Y}" text-anchor="end">no third-party trackers</text>\n')
w('  </g>\n')
w('</svg>\n')

open(OUT, "w", encoding="utf-8", newline="\n").write(out.getvalue())
print(f"wrote {OUT}: {len(LANGS)} languages, {len(chips)} chips, height {H}", file=sys.stderr)
