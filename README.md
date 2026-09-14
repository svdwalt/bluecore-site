# bluecore.joburg

Landing page for BlueCore, served by GitHub Pages from this repo.

## Files

- `index.html` — the whole site: inline CSS, inline JS, no dependencies, no build step.
  Edit the copy directly in the HTML.
- `chat.js` — site assistant widget, talks to the BlueCore-Chat proxy.
- `intel.js` — fills the "Threat pulse" section from the same proxy (see below).
- `favicon.svg` — tab icon.
- `CNAME` — custom domain for GitHub Pages. Do not delete; Pages drops the domain without it.
- `.nojekyll` — tells Pages to serve files as-is.
- `robots.txt` — allow all crawlers.

## Threat pulse

The `#threat-pulse` section in `index.html` ships with the `hidden` attribute and only
appears when `intel.js` gets a 2xx JSON response from the proxy's `GET /intel`. Any error
(offline proxy, non-2xx, bad JSON, no usable sections) leaves it hidden with nothing else
shown, so the page never looks broken when the lab is down.

Data path: browser → BlueCore-Chat proxy on the ZBook (via Tailscale Funnel) → intelmcp on
a lab PC. The proxy refreshes its snapshot every 30 minutes server-side and serves it with a
5-minute browser cache; `intel.js` makes a plain GET with no custom headers so that cache
is honoured. Nothing the visitor does reaches the intel service. All indicators are
defanged before they reach the page (e.g. `45.155.205[.]233`) and `intel.js` only writes
data through `textContent`.

Kill-switch: put the placeholder `TAILNET` in `INTEL_ENDPOINT` at the top of `intel.js`
(same convention as `CHAT_ENDPOINT` in `chat.js`) and the script exits before fetching.

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
