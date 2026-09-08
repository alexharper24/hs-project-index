#!/usr/bin/env python
"""
Regenerate index.html from the actual state of C:\\Git_Repos.

Everything that can be derived from disk is derived (git state, live domain,
draft vs live, preview port, open README items). Everything that cannot be
derived lives in projects.json, which is hand-maintained.

    python build.py

Local tool. The generated page is never published: it lists client work,
draft sites, and local paths.
"""

import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(os.path.dirname(__file__) + os.sep))
HERE = os.path.dirname(os.path.abspath(__file__))
SELF = os.path.basename(HERE)

SKIP_HTML = ("preview", "-options", "crop-", "hero-options", "theme-preview")


def sh(args, cwd=None):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=20)
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
    out, in_str, esc = [], False, False
    i = 0
    while i < len(raw):
        c = raw[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
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
        target = None
        if "--directory" in args:
            target = args[args.index("--directory") + 1]
        if not target:
            continue
        repo = target.replace("\\", "/").split("/")[0]
        by_repo.setdefault(repo, []).append(
            {"name": c.get("name"), "port": c.get("port"), "url": c.get("url")}
        )
    return by_repo


def scan(repo):
    d = os.path.join(ROOT, repo)
    info = {"repo": repo, "path": d}

    info["is_git"] = os.path.isdir(os.path.join(d, ".git"))
    if info["is_git"]:
        info["commits"] = sh(["git", "-C", d, "rev-list", "--count", "HEAD"]) or "0"
        info["last"] = sh(["git", "-C", d, "log", "-1", "--format=%ad", "--date=short"])
        info["subject"] = sh(["git", "-C", d, "log", "-1", "--format=%s"])[:110]
        info["remote"] = re.sub(
            r"^https?://|\.git$", "", sh(["git", "-C", d, "remote", "get-url", "origin"])
        )
        info["dirty"] = bool(sh(["git", "-C", d, "status", "--porcelain"]))
    else:
        info.update(commits="0", last="", subject="", remote="", dirty=False)

    cn = os.path.join(d, "CNAME")
    info["domain"] = read(cn).strip() if os.path.exists(cn) else ""

    pages, noindex = [], 0
    for dirpath, dirnames, filenames in os.walk(d):
        dirnames[:] = [x for x in dirnames if x not in (".git", "node_modules", "_harvest")]
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), d).replace(os.sep, "/")
            if any(x in rel.lower() for x in SKIP_HTML):
                continue
            pages.append(rel)
            if re.search(r'name="robots"[^>]*noindex', read(os.path.join(dirpath, fn)), re.I):
                noindex += 1
    info["pages"] = len(pages)
    info["noindex"] = noindex

    # open README checkboxes
    rd = read(os.path.join(d, "README.md"))
    info["todo"] = len(re.findall(r"^\s*-\s*\[ \]", rd, re.M))
    info["done"] = len(re.findall(r"^\s*-\s*\[x\]", rd, re.M | re.I))

    # status
    if not info["is_git"]:
        info["status"] = "no-git"
    elif info["pages"] and noindex == info["pages"]:
        info["status"] = "draft"
    elif info["domain"]:
        info["status"] = "live"
    elif info["pages"]:
        info["status"] = "pushed"
    else:
        info["status"] = "other"
    return info


def esc(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main():
    overlay = {}
    op = os.path.join(HERE, "projects.json")
    if os.path.exists(op):
        overlay = json.loads(read(op))
    meta = overlay.get("projects", {})
    order = overlay.get("categories", [])

    launch = load_launch()

    repos = sorted(
        x for x in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, x))
        and not x.startswith(".")
        and x != SELF
    )

    rows = []
    for r in repos:
        info = scan(r)
        m = meta.get(r, {})
        info["client"] = m.get("client", "")
        info["category"] = m.get("category", "Unsorted")
        info["grade"] = m.get("grade", "")
        info["note"] = m.get("note", "")
        info["previews"] = launch.get(r, [])
        rows.append(info)

    groups = {}
    for x in rows:
        groups.setdefault(x["category"], []).append(x)
    cats = [c for c in order if c in groups] + sorted(c for c in groups if c not in order)

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
    a("<title>Project Index</title>")
    a('<link rel="stylesheet" href="style.css?v=3">')
    a("</head>\n<body>")

    a('<header class="top"><div class="wrap">')
    a("<h1>Project Index</h1>")
    a('<p class="sub">%d projects in <code>%s</code> &middot; generated %s</p>'
      % (len(rows), esc(ROOT), esc(built)))
    a('<div class="tally">')
    for k, label in (("live", "live"), ("draft", "draft"), ("pushed", "pushed"),
                     ("no-git", "no git"), ("other", "other")):
        if counts.get(k):
            a('<span class="pill s-%s">%d %s</span>' % (k, counts[k], label))
    a("</div>")
    a('<div class="tools">')
    a('<input type="search" id="q" placeholder="Filter by name, client, or domain" '
      'autocomplete="off" aria-label="Filter projects">')
    a('<label><input type="checkbox" id="onlyTodo"> only with open items</label>')
    a("</div>")
    a("</div></header>")

    a('<main class="wrap">')
    for cat in cats:
        items = sorted(groups[cat], key=lambda x: x["repo"])
        a('<section class="cat"><h2>%s <span class="n">%d</span></h2>' % (esc(cat), len(items)))
        a('<div class="grid">')
        for x in items:
            hay = " ".join([x["repo"], x["client"], x["domain"], x["category"]]).lower()
            a('<article class="card s-%s" data-hay="%s" data-todo="%d">'
              % (x["status"], esc(hay), x["todo"]))

            a('<div class="chead">')
            a('<h3>%s</h3>' % esc(x["client"] or x["repo"]))
            a('<span class="badge s-%s">%s</span>' % (x["status"], esc(x["status"])))
            a("</div>")
            if x["client"]:
                a('<p class="repo"><code>%s</code></p>' % esc(x["repo"]))
            if x["note"]:
                a('<p class="note">%s</p>' % esc(x["note"]))

            a('<ul class="facts">')
            if x["grade"]:
                a("<li><span>grade</span><b>%s</b></li>" % esc(x["grade"]))
            if x["pages"]:
                nid = " (%d noindex)" % x["noindex"] if x["noindex"] else ""
                a("<li><span>pages</span><b>%d%s</b></li>" % (x["pages"], esc(nid)))
            if x["is_git"]:
                a("<li><span>commits</span><b>%s%s</b></li>"
                  % (esc(x["commits"]), " &middot; uncommitted" if x["dirty"] else ""))
                if x["last"]:
                    a("<li><span>last</span><b>%s</b></li>" % esc(x["last"]))
            else:
                a('<li><span>git</span><b class="warn">not a repo</b></li>')
            if x["todo"]:
                a('<li><span>open</span><b class="warn">%d README items</b></li>' % x["todo"])
            a("</ul>")

            if x["subject"]:
                a('<p class="subject">%s</p>' % esc(x["subject"]))

            a('<div class="acts">')
            if x["domain"]:
                a('<a class="btn go" href="https://%s/" target="_blank" rel="noopener">Live site</a>'
                  % esc(x["domain"]))
            for p in x["previews"]:
                if p.get("port"):
                    a('<a class="btn" href="http://localhost:%s/" target="_blank" '
                      'rel="noopener" title="needs preview_start(&quot;%s&quot;)">Preview :%s</a>'
                      % (esc(p["port"]), esc(p["name"]), esc(p["port"])))
            if x["remote"]:
                a('<a class="btn" href="https://%s" target="_blank" rel="noopener">Repo</a>'
                  % esc(x["remote"]))
            a('<button class="btn copy" data-copy="%s">Copy path</button>' % esc(x["path"]))
            a("</div>")
            a("</article>")
        a("</div></section>")
    a("</main>")

    a('<p class="foot wrap">Regenerate with <code>python build.py</code> from '
      '<code>hs-project-index</code>. Local only, never published.</p>')
    a('<script src="main.js?v=1"></script>')
    a("</body>\n</html>")

    io.open(os.path.join(HERE, "index.html"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(H) + "\n"
    )

    print("scanned %d projects" % len(rows))
    for k in sorted(counts):
        print("  %-8s %d" % (k, counts[k]))
    missing = [x["repo"] for x in rows if x["category"] == "Unsorted"]
    if missing:
        print("  UNSORTED (add to projects.json): " + ", ".join(missing))
    print("wrote index.html")


if __name__ == "__main__":
    sys.exit(main())
