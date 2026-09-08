#!/usr/bin/env python
"""
Regenerate the site portfolio from the actual state of C:\\Git_Repos.

    python build.py              # full internal page -> index.html
    python build.py --public     # sanitised page     -> docs/index.html

Auto-discovery: any folder named `*-website-repo` is treated as a site with no
configuration needed, so a new build shows up on its own. Add an entry to
projects.json to give it an eyebrow and a blurb; set "site": false to exclude
one, or "site": true to include something that does not match the naming rule
(that is how inf-website is included).

The internal page carries grades, open-item counts, uncommitted flags, and
localhost preview links. The public page in docs/ carries none of that. It
lists every site, but only the ones with a live domain get a link, since a
localhost URL is useless to a visitor.

docs/ is what GitHub Pages serves. Rebuild it and commit after any change,
or the published page goes stale.
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import render

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SELF = os.path.basename(HERE)

CSS_V = 8
SKIP_HTML = ("preview", "-options", "crop-", "hero-options", "theme-preview")
EXTRA_DOMAINS = {"inf-website": "www.infinitesolutionsllc.com"}


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
    raw = read(os.path.join(ROOT, ".claude", "launch.json"))
    if not raw:
        return {}
    out, in_str, bs = [], False, False
    i = 0
    while i < len(raw):
        c = raw[i]
        if in_str:
            out.append(c)
            if bs:
                bs = False
            elif c == "\\":
                bs = True
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
    try:
        cfg = json.loads(re.sub(r",(\s*[}\]])", r"\1", "".join(out)))
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


def discover(meta):
    """Folders to treat as sites: the naming rule plus explicit overrides."""
    found = []
    for x in sorted(os.listdir(ROOT)):
        if x.startswith(".") or x == SELF:
            continue
        if not os.path.isdir(os.path.join(ROOT, x)):
            continue
        m = meta.get(x, {})
        if m.get("site") is False:
            continue
        if m.get("site") is True or x.endswith("-website-repo"):
            found.append(x)
    return found


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
        dirnames[:] = [y for y in dirnames if y not in (".git", "node_modules", "_harvest")]
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), d).replace(os.sep, "/")
            if any(y in rel.lower() for y in SKIP_HTML):
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


def page(rows, public, built):
    H = []
    a = H.append
    title = "Selected Work" if public else "Site Portfolio"

    a('<!DOCTYPE html>\n<html lang="en">\n<head>')
    a('<meta charset="UTF-8">')
    a('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    a('<meta name="color-scheme" content="light only">')
    a('<meta name="supported-color-schemes" content="light">')
    if not public:
        a('<meta name="robots" content="noindex,nofollow">')
    a("<title>%s</title>" % title)
    a('<link rel="stylesheet" href="style.css?v=%d">' % CSS_V)
    a("</head>\n<body>")

    a('<header class="top"><div class="wrap">')
    a("<h1>%s</h1>" % title)
    if public:
        a('<p class="sub">Sites designed, built, and still managed today.</p>')
    else:
        counts = {}
        for x in rows:
            counts[x["status"]] = counts.get(x["status"], 0) + 1
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
    if not public:
        a('<label><input type="checkbox" id="onlyTodo"> only with open items</label>')
    a('<span class="count" id="count"></span>')
    a("</div>")
    a("</div></header>")

    a('<main class="wrap">')
    a('<div class="wgrid" id="grid">')
    for x in rows:
        a(render.card(x, public=public))
    a("</div>")
    a('<p class="empty" id="empty" hidden>Nothing matches that filter.</p>')
    a("</main>")
    if not public:
        a('<p class="foot wrap">Regenerate with <code>python build.py</code>. '
          'Thumbnails via <code>python capture.py</code>. '
          'Public build: <code>python build.py --public</code>.</p>')
    a('<script src="main.js?v=%d"></script>' % CSS_V)
    a("</body>\n</html>")
    return "\n".join(H) + "\n"


def main():
    public = "--public" in sys.argv[1:]
    overlay = json.loads(read(os.path.join(HERE, "projects.json")))
    meta = overlay.get("projects", {})
    launch = load_launch()

    repos = discover(meta)
    rows, undescribed = [], []
    for r in repos:
        info = scan(r)
        m = meta.get(r, {})
        for k in ("client", "eyebrow", "blurb", "grade", "note"):
            info[k] = m.get(k, "")
        info["previews"] = launch.get(r, [])
        if not m.get("eyebrow") or not m.get("blurb"):
            undescribed.append(r)
        rows.append(info)

    # The public build keeps every site but strips everything internal
    # (grades, open counts, uncommitted flags, local paths, preview links).
    # Sites with no live domain render without a link rather than pointing at
    # a localhost URL a visitor cannot reach.
    rows.sort(key=render.sort_key)

    built = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    html = page(rows, public, built)

    if public:
        out = os.path.join(HERE, "docs")
        os.makedirs(os.path.join(out, "img", "tiles"), exist_ok=True)
        io.open(os.path.join(out, "index.html"), "w", encoding="utf-8", newline="\n").write(html)
        for f in ("style.css", "main.js"):
            shutil.copyfile(os.path.join(HERE, f), os.path.join(out, f))
        io.open(os.path.join(out, ".nojekyll"), "w").write("")
        kept = 0
        for x in rows:
            src = os.path.join(HERE, "img", "tiles", x["repo"] + ".jpg")
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(out, "img", "tiles", x["repo"] + ".jpg"))
                kept += 1
        print("PUBLIC build: %d sites, %d thumbnails -> docs/" % (len(rows), kept))
        print("  omitted: grades, open-item counts, uncommitted flags, local")
        print("           paths, and localhost preview links.")
        nolink = len([x for x in rows if not x["domain"]])
        print("  %d of %d have no live domain and render without a link." % (nolink, len(rows)))
    else:
        io.open(os.path.join(HERE, "index.html"), "w", encoding="utf-8", newline="\n").write(html)
        tiles = os.path.join(HERE, "img", "tiles")
        have = {f[:-4] for f in os.listdir(tiles)} if os.path.isdir(tiles) else set()
        no_tile = [x["repo"] for x in rows if x["repo"] not in have]
        print("rendered %d sites -> index.html" % len(rows))
        if no_tile:
            print("  NO THUMBNAIL (%d): %s" % (len(no_tile), ", ".join(no_tile)))
            print("  -> python capture.py")
        if undescribed:
            print("  NEEDS eyebrow/blurb in projects.json (%d): %s"
                  % (len(undescribed), ", ".join(undescribed)))


if __name__ == "__main__":
    sys.exit(main())
