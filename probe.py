#!/usr/bin/env python
"""
Work out a reachable public URL for every site and cache it in links.json.

    python probe.py            # probe everything
    python probe.py <repo>     # just one

Resolution order per site:
  1. CNAME in the repo            -> https://<domain>/
  2. GitHub Pages project URL     -> https://alexharper24.github.io/<remote-repo>/
  3. nothing reachable            -> recorded as unreachable

The remote repo name is often NOT the folder name (hope-website-repo ->
HopeBaptistWarsaw, carvercowood-website-repo -> CarverCoWood), so the URL is
derived from `git remote get-url origin`, never from the folder.

build.py reads links.json so the page can be generated without network access.
Re-run this after enabling Pages on a repo or moving a site to a domain.
"""

import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SELF = os.path.basename(HERE)
PAGES_OWNER = "alexharper24"
UA = "Mozilla/5.0 (project-index probe)"

# Live sites with no CNAME in the repo because they are hosted elsewhere.
# Keep in sync with EXTRA_DOMAINS in build.py.
EXTRA_DOMAINS = {"inf-website": "www.infinitesolutionsllc.com"}


def read(p):
    try:
        return io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def sh(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def head(url, timeout=20):
    """Return (status, final_url). Uses curl, not urllib.

    urllib hangs on this machine (observed twice: YouTube's timedtext endpoint
    and this probe), while curl returns promptly for the same URLs. Do not
    switch this back.
    """
    r = subprocess.run(
        ["curl", "-s", "-o", os.devnull, "-L",
         "-w", "%{http_code} %{url_effective}",
         "--max-time", str(timeout),
         "-A", UA, url],
        capture_output=True, text=True, timeout=timeout + 15,
        stdin=subprocess.DEVNULL,
    )
    out = (r.stdout or "").strip().split(" ", 1)
    try:
        code = int(out[0])
    except Exception:
        code = 0
    return code, (out[1] if len(out) > 1 else url)


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    overlay = json.loads(read(os.path.join(HERE, "projects.json")))
    meta = overlay.get("projects", {})

    sites = []
    for x in sorted(os.listdir(ROOT)):
        if x.startswith(".") or x == SELF or not os.path.isdir(os.path.join(ROOT, x)):
            continue
        m = meta.get(x, {})
        if m.get("site") is False:
            continue
        if m.get("site") is True or x.endswith("-website-repo"):
            sites.append(x)
    if only:
        sites = [s for s in sites if s in only]

    lp = os.path.join(HERE, "links.json")
    links = json.loads(read(lp)) if os.path.exists(lp) else {}

    for repo in sites:
        d = os.path.join(ROOT, repo)
        cname = read(os.path.join(d, "CNAME")).strip() or EXTRA_DOMAINS.get(repo, "")
        remote = sh(["git", "-C", d, "remote", "get-url", "origin"])
        # the remote repo name, which is frequently not the folder name
        rname = re.sub(r"\.git$", "", remote.rsplit("/", 1)[-1]) if remote else ""
        on_gh = "github.com" in remote

        entry = {"remote_name": rname, "host": "github" if on_gh else ("ghe" if remote else "none")}

        if cname:
            url = "https://%s/" % cname
            code, final = head(url)
            entry.update(url=url, via="domain", status=code, reachable=200 <= code < 400, final=final)
        elif on_gh and rname:
            url = "https://%s.github.io/%s/" % (PAGES_OWNER, rname)
            code, final = head(url)
            entry.update(url=url, via="pages", status=code, reachable=code == 200, final=final)
        else:
            entry.update(url="", via="none", status=0, reachable=False)

        links[repo] = entry
        print("  %-38s %-7s %-4s %s"
              % (repo, entry["via"], entry["status"],
                 entry["url"] if entry["reachable"] else "UNREACHABLE " + (entry["url"] or "no remote")))

    io.open(lp, "w", encoding="utf-8", newline="\n").write(
        json.dumps(links, indent=2, sort_keys=True) + "\n"
    )
    ok = len([v for v in links.values() if v.get("reachable")])
    print("reachable: %d of %d   -> links.json" % (ok, len(links)))
    bad = [k for k, v in links.items() if not v.get("reachable")]
    if bad:
        print("unreachable (Pages likely not enabled):")
        for b in bad:
            print("  %s  ->  gh api -X POST repos/%s/%s/pages -f 'source[branch]=main' -f 'source[path]=/'"
                  % (b, PAGES_OWNER, links[b].get("remote_name", "?")))


if __name__ == "__main__":
    main()
