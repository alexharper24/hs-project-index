#!/usr/bin/env python
"""
Capture a homepage thumbnail for every site marked "site": true in projects.json.

    python capture.py            # only missing tiles
    python capture.py --all      # recapture everything
    python capture.py <repo>     # one repo

Live sites are captured from their real domain. Everything else is served
locally on its launch.json port for the duration of the capture.

Headless Chrome screenshots DO work on this machine for desktop widths (the
Browser pane's `computer` screenshot is what times out). Captured at 2x and
resized down, same pipeline that produced alexharper-website-repo/img/work.
"""

import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TILES = os.path.join(HERE, "img", "tiles")

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SHOT_W, SHOT_H = 1280, 800          # capture viewport
TILE_W, TILE_H = 640, 400           # output tile (2x a 320px card)
SETTLE = 9000                       # virtual-time budget, ms

# Live sites without a CNAME in the repo (hosted elsewhere).
EXTRA_DOMAINS = {"inf-website": "www.infinitesolutionsllc.com"}


def read(p):
    try:
        return io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def launch_ports():
    """repo -> (port, served_directory) from the JSONC launch.json."""
    raw = read(os.path.join(ROOT, ".claude", "launch.json"))
    raw = re.sub(r"//[^\n]*", "", raw)
    out = {}
    for m in re.finditer(r'"runtimeArgs":\s*\[([^\]]*)\]', raw):
        body = m.group(1)
        port = re.search(r'"(\d{4,5})"', body)
        d = re.search(r'"--directory",\s*"([^"]+)"', body)
        if port and d:
            target = d.group(1).replace("\\", "/")
            repo = target.split("/")[0]
            out.setdefault(repo, (int(port.group(1)), target))
    return out


def free_port(start=8500):
    p = start
    while p < start + 200:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
        p += 1
    raise RuntimeError("no free port")


def up(port, tries=40):
    for _ in range(tries):
        with socket.socket() as s:
            s.settimeout(0.4)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.25)
    return False


def shoot(url, out_png):
    if os.path.exists(out_png):
        os.remove(out_png)
    cmd = [
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=2",
        "--window-size=%d,%d" % (SHOT_W, SHOT_H),
        "--virtual-time-budget=%d" % SETTLE,
        "--screenshot=" + out_png,
        url,
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=110)
    except subprocess.TimeoutExpired:
        return False
    return os.path.exists(out_png) and os.path.getsize(out_png) > 8000


def to_tile(png, jpg):
    from PIL import Image
    im = Image.open(png).convert("RGB")
    # crop to the tile aspect from the top, then resize
    target = TILE_W / TILE_H
    w, h = im.size
    if w / h > target:
        nw = int(h * target)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / target)
        im = im.crop((0, 0, w, nh))
    im = im.resize((TILE_W, TILE_H), Image.LANCZOS)
    im.save(jpg, "JPEG", quality=72, optimize=True, progressive=True)
    return os.path.getsize(jpg)


def main():
    args = [a for a in sys.argv[1:]]
    do_all = "--all" in args
    only = [a for a in args if not a.startswith("--")]

    overlay = json.loads(read(os.path.join(HERE, "projects.json")))
    projects = overlay.get("projects", {})
    sites = [r for r, m in projects.items() if m.get("site")]
    if only:
        sites = [r for r in sites if r in only]

    os.makedirs(TILES, exist_ok=True)
    ports = launch_ports()
    manifest_path = os.path.join(HERE, "tiles.json")
    manifest = json.loads(read(manifest_path)) if os.path.exists(manifest_path) else {}

    print("%d site(s) to consider" % len(sites))
    for repo in sorted(sites):
        jpg = os.path.join(TILES, repo + ".jpg")
        if os.path.exists(jpg) and not do_all and repo not in only:
            print("  skip   %s (tile exists)" % repo)
            continue

        cname = read(os.path.join(ROOT, repo, "CNAME")).strip()
        domain = cname or EXTRA_DOMAINS.get(repo, "")
        srv = None
        tmp_png = os.path.join(TILES, "_" + repo + ".png")

        entry = (projects.get(repo) or {}).get("entry", "")
        override = (projects.get(repo) or {}).get("capture_url", "")

        force_local = (projects.get(repo) or {}).get("capture_local", False)

        if override:
            url, src = override, "override"
        elif domain and not force_local:
            url, src = "https://%s/%s" % (domain, entry.lstrip("/")), "live"
        else:
            cfg = ports.get(repo)
            served = cfg[1] if cfg else repo
            directory = os.path.join(ROOT, served)
            if not os.path.isdir(directory):
                print("  FAIL   %s (no directory %s)" % (repo, served))
                continue
            port = free_port()
            srv = subprocess.Popen(
                [sys.executable, "-m", "http.server", str(port), "--directory", directory],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if not up(port):
                srv.terminate()
                print("  FAIL   %s (server did not start)" % repo)
                continue
            url = "http://localhost:%d/%s" % (port, entry.lstrip("/"))
            src = "local:%s" % served

        ok = shoot(url, tmp_png)
        if srv:
            srv.terminate()
            try:
                srv.wait(timeout=8)
            except Exception:
                srv.kill()

        if not ok:
            print("  FAIL   %-40s %s" % (repo, url))
            if os.path.exists(tmp_png):
                os.remove(tmp_png)
            continue

        kb = to_tile(tmp_png, jpg) // 1024
        os.remove(tmp_png)
        manifest[repo] = {"src": src, "url": url, "kb": kb, "at": time.strftime("%Y-%m-%d %H:%M")}
        print("  ok     %-40s %-34s %d KB" % (repo, src, kb))

    io.open(manifest_path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    have = len([f for f in os.listdir(TILES) if f.endswith(".jpg")])
    print("tiles on disk: %d   manifest: tiles.json" % have)


if __name__ == "__main__":
    main()
