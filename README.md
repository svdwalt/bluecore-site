# bluecore.joburg

Landing page for BlueCore, served by GitHub Pages from this repo.

## Files

- `index.html` — the whole site: inline CSS, inline JS, no dependencies, no build step.
  Edit the copy directly in the HTML.
- `favicon.svg` — tab icon.
- `CNAME` — custom domain for GitHub Pages. Do not delete; Pages drops the domain without it.
- `.nojekyll` — tells Pages to serve files as-is.
- `robots.txt` — allow all crawlers.

## Preview locally

```
python3 -m http.server 8090
open http://127.0.0.1:8090/
```

## Deploy

Push to `main`. GitHub Pages rebuilds within about a minute.

```
git add -A && git commit -m "Update copy" && git push
```

Check status: `gh api repos/svdwalt/bluecore-site/pages --jq '.status'`

## DNS (at 1-grid)

These records must exist for the custom domain. Only the `@` A records and the `www` CNAME
belong to this site. MX and TXT records carry mail (1-grid + Microsoft 365) and must never
be changed for the website.

| Type  | Name | Value              |
|-------|------|--------------------|
| A     | @    | 185.199.108.153    |
| A     | @    | 185.199.109.153    |
| A     | @    | 185.199.110.153    |
| A     | @    | 185.199.111.153    |
| CNAME | www  | svdwalt.github.io  |

After DNS propagates, turn on "Enforce HTTPS" in the repo's Pages settings (or
`gh api -X PUT repos/svdwalt/bluecore-site/pages -F https_enforced=true`).
