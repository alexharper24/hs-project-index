"""
Card rendering for the site portfolio, shaped like the work grid on
harperstudio.co: screenshot on top, category eyebrow, serif title, one-line
description, one link.

The whole card is a single <a>. There is exactly one action per card, so
wrapping it avoids nested interactive elements and keeps it keyboard
reachable with one tab stop.

Imported by build.py.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))

STATUS_ORDER = {"live": 0, "pushed": 1, "draft": 2, "no-git": 3, "other": 4}
STATUS_LABEL = {
    "live": "Live", "pushed": "Built", "draft": "Draft",
    "no-git": "No git", "other": "Other",
}


def esc(s):
    return (
        str(s).replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;")
    )


def eyebrow_slug(eyebrow):
    e = (eyebrow or "").lower()
    for needle, slug in (
        ("church", "church"), ("bakery", "bakery"), ("breeder", "breeder"),
        ("trades", "trades"), ("contracting", "trades"), ("painting", "trades"),
        ("woodworking", "trades"), ("photo", "photo"), ("technology", "tech"),
        ("web design", "tech"), ("coaching", "coach"), ("consulting", "coach"),
        ("salon", "service"), ("detailing", "service"),
        ("mockup", "concept"), ("concept", "concept"),
    ):
        if needle in e:
            return slug
    return "other"


def target(x, public=False):
    """Where the card points.

    1. the resolved public URL from probe.py (a custom domain, or the repo's
       GitHub Pages project URL, whichever actually answered 200)
    2. failing that, the local preview port, but only on the internal build,
       since a localhost URL is useless to anyone else

    A site with neither gets no link.
    """
    if x.get("public_url"):
        return x["public_url"], "Visit site"
    if public:
        return "", ""
    for p in x.get("previews", []):
        if p.get("port"):
            return "http://localhost:%s/" % p["port"], "Open locally"
    return "", ""


def card(x, tiles_dir="img/tiles", public=False):
    A = []
    a = A.append

    title = x["client"] or x["repo"]
    tile = (tiles_dir + "/" + x["repo"] + ".jpg")
    has_tile = os.path.exists(os.path.join(HERE, tile.replace("/", os.sep)))
    href, label = target(x, public)

    hay = " ".join([x["repo"], title, x.get("domain", ""), x.get("eyebrow", "")]).lower()

    # The card is a link when there is somewhere to go, a plain article when not.
    if href:
        a('<a class="wcard s-%s" href="%s" target="_blank" rel="noopener" '
          'data-hay="%s" data-todo="%d" data-status="%s" aria-label="%s, open the site">'
          % (x["status"], esc(href), esc(hay), x["todo"], esc(x["status"]), esc(title)))
    else:
        a('<article class="wcard nolink s-%s" data-hay="%s" data-todo="%d" data-status="%s">'
          % (x["status"], esc(hay), x["todo"], esc(x["status"])))

    a('<div class="shot">')
    if has_tile:
        a('<img src="%s?v=2" alt="Homepage of %s" width="640" height="400" '
          'loading="lazy" decoding="async">' % (esc(tile), esc(title)))
    else:
        a('<span class="noshot"><span>no capture</span></span>')
    # The status badge is internal signal. A visitor does not need to be told
    # which client sites are unfinished.
    if not public:
        a('<span class="stat s-%s">%s</span>'
          % (x["status"], esc(STATUS_LABEL.get(x["status"], x["status"]))))
    a("</div>")

    a('<div class="wbody">')
    if x.get("eyebrow"):
        a('<span class="eyebrow e-%s">%s</span>'
          % (eyebrow_slug(x["eyebrow"]), esc(x["eyebrow"])))
    # a heading inside <a> is valid (transparent content model) and keeps the
    # grid navigable by heading for screen readers
    a('<h3 class="wtitle">%s</h3>' % esc(title))
    if x.get("blurb"):
        a('<span class="blurb">%s</span>' % esc(x["blurb"]))

    if not public:
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
            a('<span class="meta">%s</span>' % " &middot; ".join(bits))

    a('<span class="wlinks">')
    if href:
        a('<span class="go">%s <span class="arw">&rarr;</span></span>' % esc(label))
    else:
        a('<span class="go muted">Not published</span>')
    a("</span>")   # .wlinks

    a("</div>")    # .wbody
    a("</a>" if href else "</article>")
    return "\n".join(A)


def sort_key(x):
    return (STATUS_ORDER.get(x["status"], 9), (x["client"] or x["repo"]).lower())
