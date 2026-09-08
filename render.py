"""
Card rendering for the project index, in the same shape as the work grid on
harperstudio.co: screenshot on top, category eyebrow, serif title, one-line
description, then the links.

Imported by build.py. Kept separate so the scanning logic and the markup can
be changed independently.
"""

import os

STATUS_ORDER = {"live": 0, "pushed": 1, "draft": 2, "no-git": 3, "other": 4}

STATUS_LABEL = {
    "live": "Live",
    "pushed": "Built",
    "draft": "Draft",
    "no-git": "No git",
    "other": "Other",
}


def esc(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def eyebrow_slug(eyebrow):
    """Map an eyebrow label to a colour class, so a category reads at a glance."""
    e = (eyebrow or "").lower()
    if "church" in e:
        return "church"
    if "bakery" in e:
        return "bakery"
    if "breeder" in e:
        return "breeder"
    if "trades" in e or "contracting" in e or "painting" in e or "woodworking" in e:
        return "trades"
    if "photo" in e:
        return "photo"
    if "technology" in e or "web design" in e:
        return "tech"
    if "coaching" in e or "consulting" in e:
        return "coach"
    if "salon" in e or "detailing" in e:
        return "service"
    if "mockup" in e or "concept" in e:
        return "concept"
    return "other"


def card(x, tiles_dir="img/tiles"):
    """One site card. x is the dict built by build.scan() plus overlay fields."""
    A = []
    a = A.append

    title = x["client"] or x["repo"]
    tile = os.path.join(tiles_dir, x["repo"] + ".jpg").replace(os.sep, "/")
    has_tile = os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), tile))

    hay = " ".join([x["repo"], title, x.get("domain", ""), x.get("eyebrow", "")]).lower()

    # the audit note rides along as a tooltip so it is not lost at this width
    tip = (' title="%s"' % esc(x["note"])) if x.get("note") else ""

    a('<article class="wcard s-%s" data-hay="%s" data-todo="%d" data-status="%s"%s>'
      % (x["status"], esc(hay), x["todo"], esc(x["status"]), tip))

    # ---- thumbnail ----
    a('<div class="shot">')
    if has_tile:
        a('<img src="%s?v=1" alt="Homepage of %s" width="640" height="400" loading="lazy" decoding="async">'
          % (esc(tile), esc(title)))
    else:
        a('<div class="noshot"><span>no capture</span></div>')
    a('<span class="stat s-%s">%s</span>' % (x["status"], esc(STATUS_LABEL.get(x["status"], x["status"]))))
    a("</div>")

    # ---- body ----
    a('<div class="wbody">')
    if x.get("eyebrow"):
        a('<p class="eyebrow e-%s">%s</p>' % (eyebrow_slug(x["eyebrow"]), esc(x["eyebrow"])))
    a("<h3>%s</h3>" % esc(title))
    if x.get("blurb"):
        a('<p class="blurb">%s</p>' % esc(x["blurb"]))

    # compact meta line
    bits = []
    if x.get("grade"):
        bits.append("Grade %s" % esc(x["grade"]))
    if x["pages"]:
        bits.append("%d pages" % x["pages"])
    if x["todo"]:
        bits.append('<b class="warn">%d open</b>' % x["todo"])
    if x.get("dirty"):
        bits.append('<b class="warn">uncommitted</b>')
    if bits:
        a('<p class="meta">%s</p>' % " &middot; ".join(bits))

    # ---- links ----
    a('<div class="wlinks">')
    if x.get("domain"):
        a('<a class="go" href="https://%s/" target="_blank" rel="noopener">Visit site <span>&rarr;</span></a>'
          % esc(x["domain"]))
    for p in x.get("previews", []):
        if p.get("port"):
            a('<a class="go" href="http://localhost:%s/" target="_blank" rel="noopener" '
              'title="Start it first: preview_start({name: &quot;%s&quot;})">Open preview <span>&rarr;</span></a>'
              % (esc(p["port"]), esc(p["name"])))
            break
    if x.get("remote"):
        a('<a class="sub-link" href="https://%s" target="_blank" rel="noopener">Repo <span>&rarr;</span></a>'
          % esc(x["remote"]))
    a('<button class="sub-link copy" data-copy="%s">Copy path <span>&rarr;</span></button>' % esc(x["path"]))
    a("</div>")

    a("</div>")   # .wbody
    a("</article>")
    return "\n".join(A)


def sort_key(x):
    return (STATUS_ORDER.get(x["status"], 9), (x["client"] or x["repo"]).lower())
