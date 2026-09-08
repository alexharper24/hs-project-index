#!/usr/bin/env python
"""
Regenerate index.html from the actual state of C:\\Git_Repos.

Only projects marked "site": true in projects.json are rendered. The internal
tools (inf-* dashboards, phc-* scripts, form-backend-worker, site-checks,
hs-proposals, harperfinance) are deliberately left off: this is the site
portfolio, shaped like the work grid on harperstudio.co. To include one, add
"site": true to its entry.

    python build.py

Thumbnails come from capture.py, which screenshots each homepage. Run that
first, or after any redesign.

Local tool. Never published: it lists client work, draft sites, and local paths.
"""

import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

import render

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SELF = os.path.basename(HERE)

CSS_V = 5
SKIP_HTML = ("preview", "-options", "crop-", "hero-options", "theme-preview")


def sh(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def read(p):
    try:
        return io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def load_launch():
    """Parse the JSONC launch.json: strip // comments and trailing commas."""
    raw = read(os.path.join(ROOT, ".claude", "launch.json"))
    if not raw:
        return {}
    out, in_str, esc_ = [], False, False
    i = 0
    while i < len(raw):
        c = raw[i]
        if in_str:
            out.append(c)
            if esc_:
                esc_ = False
            elif c == "\\":
                esc_ = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if raw.startswith("//", i):
            while i < len(raw) and raw[i] != "\n":
                i += 1
            continue
        out.append(c)
        i += 1
    txt = re.sub(r",(\s*[}\]])", r"\1", "".join(out))
    try:
        cfg = json.loads(txt)
    except Exception as e:
        print("  warn: launch.json unparseable:", e)
        return {}
    by_repo = {}
    for c in cfg.get("configurations", []):
        args = c.get("runtimeArgs") or []
        if "--directory" not in args:
            continue
        target = args[args.index("--directory") + 1].replace("\\", "/")
        by_repo.setdefault(target.split("/")[0], []).append(
            {"name": c.get("name"), "port": c.get("port")}
        )
    return by_repo


EXTRA_DOMAINS = {"inf-website": "www.infinitesolutionsllc.com"}


def scan(repo):
    d = os.path.join(ROOT, repo)
    info = {"repo": repo, "path": d}

    info["is_git"] = os.path.isdir(os.path.join(d, ".git"))
    if info["is_git"]:
        info["commits"] = sh(["git", "-C", d, "rev-list", "--count", "HEAD"]) or "0"
        info["last"] = sh(["git", "-C", d, "log", "-1", "--format=%ad", "--date=short"])
        info["remote"] = re.sub(
            r"^https?://|\.git$", "", sh(["git", "-C", d, "remote", "get-url", "origin"])
        )
        info["dirty"] = bool(sh(["git", "-C", d, "status", "--porcelain"]))
    else:
        info.update(commits="0", last="", remote="", dirty=False)

    cn = os.path.join(d, "CNAME")
    info["domain"] = read(cn).strip() if os.path.exists(cn) else EXTRA_DOMAINS.get(repo, "")

    pages = noindex = 0
    for dirpath, dirnames, filenames in os.walk(d):
        dirnames[:] = [x for x in dirnames if x not in (".git", "node_modules", "_harvest")]
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), d).replace(os.sep, "/")
            if any(x in rel.lower() for x in SKIP_HTML):
                continue
            pages += 1
            if re.search(r'name="robots"[^>]*noindex', read(os.path.join(dirpath, fn)), re.I):
                noindex += 1
    info["pages"], info["noindex"] = pages, noindex

    rd = read(os.path.join(d, "README.md"))
    info["todo"] = len(re.findall(r"^\s*-\s*\[ \]", rd, re.M))

    if not info["is_git"]:
        info["status"] = "no-git"
    elif pages and noindex == pages:
        info["status"] = "draft"
    elif info["domain"]:
        info["status"] = "live"
    elif pages:
        info["status"] = "pushed"
    else:
        info["status"] = "other"
    return info


def main():
    overlay = json.loads(read(os.path.join(HERE, "projects.json")))
    meta = overlay.get("projects", {})
    launch = load_launch()

    site_repos = sorted(r for r, m in meta.items() if m.get("site"))
    missing_dir = [r for r in site_repos if not os.path.isdir(os.path.join(ROOT, r))]

    rows = []
    for r in site_repos:
        if r in missing_dir:
            continue
        info = scan(r)
        m = meta[r]
        for k in ("client", "eyebrow", "blurb", "grade", "note"):
            info[k] = m.get(k, "")
        info["previews"] = launch.get(r, [])
        rows.append(info)

    rows.sort(key=render.sort_key)

    counts = {}
    for x in rows:
        counts[x["status"]] = counts.get(x["status"], 0) + 1
    built = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")

    H = []
    a = H.append
    a('<!DOCTYPE html>\n<html lang="en">\n<head>')
    a('<meta charset="UTF-8">')
    a('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    a('<meta name="color-scheme" content="light only">')
    a('<meta name="supported-color-schemes" content="light">')
    a('<meta name="robots" content="noindex,nofollow">')
    a("<title>Site Portfolio</title>")
    a('<link rel="stylesheet" href="style.css?v=%d">' % CSS_V)
    a("</head>\n<body>")

    a('<header class="top"><div class="wrap">')
    a("<h1>Site Portfolio</h1>")
    a('<p class="sub">%d sites &middot; generated %s</p>' % (len(rows), render.esc(built)))
    a('<div class="tally">')
    for k, label in (("live", "live"), ("pushed", "built"), ("draft", "draft"),
                     ("no-git", "no git"), ("other", "other")):
        if counts.get(k):
            a('<span class="pill s-%s">%d %s</span>' % (k, counts[k], label))
    a("</div>")
    a('<div class="tools">')
    a('<input type="search" id="q" placeholder="Filter by name, client, domain, or category" '
      'autocomplete="off" aria-label="Filter sites">')
    a('<label><input type="checkbox" id="onlyTodo"> only with open items</label>')
    a('<span class="count" id="count"></span>')
    a("</div>")
    a("</div></header>")

    a('<main class="wrap">')
    a('<div class="wgrid" id="grid">')
    for x in rows:
        a(render.card(x))
    a("</div>")
    a('<p class="empty" id="empty" hidden>Nothing matches that filter.</p>')
    a("</main>")

    a('<p class="foot wrap">Regenerate with <code>python build.py</code>. '
      'Thumbnails via <code>python capture.py</code>. Local only, never published.</p>')
    a('<script src="main.js?v=%d"></script>' % CSS_V)
    a("</body>\n</html>")

    io.open(os.path.join(HERE, "index.html"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(H) + "\n"
    )

    tiles = os.path.join(HERE, "img", "tiles")
    have = {f[:-4] for f in os.listdir(tiles)} if os.path.isdir(tiles) else set()
    no_tile = [x["repo"] for x in rows if x["repo"] not in have]

    print("rendered %d sites" % len(rows))
    for k in sorted(counts):
        print("  %-8s %d" % (k, counts[k]))
    if no_tile:
        print("  NO THUMBNAIL (%d): %s" % (len(no_tile), ", ".join(no_tile)))
        print("  -> python capture.py")
    if missing_dir:
        print("  MISSING FOLDER: %s" % ", ".join(missing_dir))
    print("wrote index.html")


if __name__ == "__main__":
    sys.exit(main())
