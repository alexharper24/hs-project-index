# hs-project-index

A local dashboard of every project in `C:\Git_Repos`. One page, generated from the
actual state of the folder, so it does not go stale as projects are added.

**Not a client site and never published.** It lists client work, draft sites that are
still `noindex`, local filesystem paths, and per-project notes. See "Deliberate
decisions" below.

## Run it

```bash
python build.py
```

Then either open `index.html` directly, or serve it:

```bash
python -m http.server 8210 --directory hs-project-index
```

`preview_start({name: "index"})` is registered in the root `.claude/launch.json` on
port **8210**.

## What the page gives you

- Every project grouped by category, with a status badge and a colour-coded left edge.
- **Live site** button where a `CNAME` exists.
- **Preview :PORT** button for every `launch.json` entry pointing at that folder.
  The link only works once the server is running, so start it first with
  `preview_start({name})`.
- **Repo** button to the git remote.
- **Copy path** button for the local folder, so you can paste it into a `cd`.
- Filter box (press `/` to focus, `Escape` to clear) and an "only with open items"
  checkbox that surfaces projects with unchecked README boxes.

## Derived versus hand-maintained

`build.py` derives from disk, so these are always current:

| Field | Source |
|---|---|
| status (live / draft / pushed / no-git / other) | `.git` presence, `CNAME`, ratio of `noindex` pages |
| commits, last commit date, last subject, uncommitted flag | `git` |
| remote | `git remote get-url origin` |
| live domain | `CNAME` |
| page count and noindex count | walk for `*.html`, skipping preview and `_harvest` files |
| open items | unchecked `- [ ]` lines in the project's `README.md` |
| preview ports | root `.claude/launch.json` (JSONC, comments stripped) |

`projects.json` holds what cannot be derived: **client name, category, grade, note.**
Add a project there when `build.py` reports it as `UNSORTED`, which it prints on every
run. Grades come from a portfolio audit and go stale, so re-audit before trusting one.

## Deliberate decisions (do not "fix" these back)

- **No remote, and it must stay that way.** Same reasoning as `hs-proposals`. The page
  exposes client names, draft-site status, and local paths. `.gitignore` excludes the
  generated `index.html` so an accidental push carries no client data.
- **`noindex,nofollow` on the page** and no sitemap, canonical, or OG tags. Those exist
  to help a page get found. This one must not be.
- **Buttons are 31px on desktop and 44px on touch and narrow widths.** The 44px
  minimum is applied under `@media (hover:none)` and `@media (max-width:600px)` only.
  Pointer devices do not need it, and forcing 44px everywhere makes a dense dashboard
  much taller.
- **Generated, not hand-written.** A hand-written list of 37 projects is stale within a
  week. During the session that built this, the folder count changed three times.

## Notes for future sessions

- Two bugs in the root `launch.json` were found while wiring this up. One is fixed:
  the `phillips` entry served on 8166 but declared `"port": 8178`, which is the
  `hs-proposals` server, so `preview_start({name:"phillips"})` opened client pricing.
  If you add entries, **make the `http.server` argument and the `port` field match.**
- `.tools` switches to `flex-direction:column` under 600px, and in a column flex
  container a `flex-basis` of `320px` is applied to **height**. That rendered the
  search box 320px tall until `flex:none` was added in the narrow block. Watch for it
  anywhere a flex row becomes a column.
- Serving over `python -m http.server` sends `Last-Modified`/`ETag`, so the browser
  will hand you a **cached `index.html`** after a rebuild. Bump the `?v=` in
  `build.py` and load the page with a throwaway query string when verifying, or you
  will measure the old stylesheet. This is the trap already recorded in the root
  `CLAUDE.md`.

## Pending

- [ ] Categories for any project added after 2026-09-04. `build.py` prints `UNSORTED`.
- [ ] `puppyconnection-website-repo` and `cornerstonesvcs-website-repo` show as
      `no-git`. They need `git init` and a push, which is tracked separately.
- [ ] Optionally show the `site-checks` error count per project. Left out because
      running the checker across 37 folders on every build is slow.
