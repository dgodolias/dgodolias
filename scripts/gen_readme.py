"""Render README.md from the website's published data contract.

Usage: python scripts/gen_readme.py <site.json> <out.md>

dimosthenisgkontolias.com/profile.json is the single source of truth: the about
copy, the project table and every link below are projections of it. Editing this
file by hand will be overwritten on the next run — change the website instead.
"""
import json, sys

SITE, OUT = sys.argv[1], sys.argv[2]

site = json.load(open(SITE, encoding="utf-8"))
p = site["profile"]
featured = site["projects"]["featured"]
site_url = site["site"]

# Prefer a live product link, then source, then the project's section on the site.
LINK_ORDER = ["Live", "Hub", "Demo", "GitHub", "Repo"]


def best_link(project):
    by_label = {l["label"]: l["href"] for l in project.get("links", [])}
    for label in LINK_ORDER:
        if label in by_label:
            return by_label[label]
    if project.get("links"):
        return project["links"][0]["href"]
    return f"{site_url}/#work"


def md_escape(text):
    return text.replace("|", "\\|")


L = []
w = L.append

w(f'<p align="center">')
w(f'  <img src="./assets/contributions.svg" alt="Contribution graph for dgodolias" width="100%">')
w("</p>")
w("")
w(f'<p align="center">')
w(f'  <a href="{site_url}/">')
w(f'    <img src="./assets/profile-terminal.svg" alt="Terminal profile card for dgodolias" width="100%">')
w("  </a>")
w("</p>")
w("")
w(f'<p align="center">')
w(f'  <a href="{site_url}/"><b>Website</b></a> &nbsp;·&nbsp;')
w(f'  <a href="{p["resumeHref"]}"><b>CV</b></a> &nbsp;·&nbsp;')
w(f'  <a href="{p["linkedinHref"]}"><b>LinkedIn</b></a> &nbsp;·&nbsp;')
w(f'  <a href="mailto:{p["email"]}"><b>Email</b></a>')
w("</p>")
w("")
w("---")
w("")
w("### About")
w("")
w(p["intro"])
w("")
w(f'**{p["availability"]}**')
w("")
w("---")
w("")
w(f'<p align="center">')
w(f'  <img src="./assets/stack.svg" alt="Languages by repository and tech stack" width="100%">')
w("</p>")
w("")
w("---")
w("")
w("### Things I've built")
w("")
w("| Project | What it is | Stack |")
w("| --- | --- | --- |")
for proj in featured:
    stack = ", ".join(proj["stack"][:5])
    w(f'| **[{md_escape(proj["title"])}]({best_link(proj)})** '
      f'| {md_escape(proj["summary"])} | {md_escape(stack)} |')
w("")
w("---")
w("")
w("<details>")
w("<summary><sub>How this page builds itself</sub></summary>")
w("")
w("<br>")
w("")
w(f'Everything above is generated. The about copy, the project table and the links come from')
w(f'[`{site_url}/profile.json`]({site_url}/profile.json) — the same data that renders my website,')
w("published as a machine-readable contract so the site stays the single source of truth.")
w("The three cards are plain SVG built from the GitHub GraphQL API by [`scripts/`](./scripts).")
w("")
w("A daily [workflow](./.github/workflows/refresh-cards.yml) re-runs the generators, so editing")
w("the website is enough to update this page. No third-party badge or stats services are")
w("involved, so nothing here can rate-limit, break, or track whoever is reading it. The")
w("animation is CSS and SMIL inside the SVG and collapses to a static card under")
w("`prefers-reduced-motion`.")
w("")
w("</details>")
w("")

open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print(f"wrote {OUT}: {len(featured)} projects from {site_url}", file=sys.stderr)
