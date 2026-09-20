/* BlueCore live lab. Reads a one-bit status from the BlueCore-Chat proxy (GET /lab: is the lab's
 * Cisco ISE admin GUI answering, and its public URL) and reveals #live-lab only while it is up,
 * so the site never shows a dead link when the lab is powered off.
 * While LAB_ENDPOINT still contains "TAILNET" the section stays hidden (same kill-switch as chat.js).
 * The JSON is untrusted: every field is type-checked, text goes in via textContent and the link is
 * only set when it is an https URL. */
(function () {
  const LAB_ENDPOINT = 'https://bluecore-chat.tailab0ebc.ts.net';

  if (LAB_ENDPOINT.includes('TAILNET')) return;

  const section = document.getElementById('live-lab');
  if (!section) return;

  const isObj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const str = (v, fallback) => (typeof v === 'string' && v.trim()) ? v.trim() : fallback;

  function pick(data, path) {
    let cur = data;
    for (const key of path.split('.')) {
      if (!isObj(cur)) return undefined;
      cur = cur[key];
    }
    return cur;
  }

  function render(data) {
    if (!isObj(data) || !isObj(data.ise) || data.ise.up !== true) return false;
    const url = str(data.ise.url, '');
    if (!/^https:\/\/[a-z0-9.-]+(:\d+)?\//i.test(url)) return false;
    section.querySelectorAll('[data-f]').forEach(el => {
      el.textContent = str(pick(data, el.getAttribute('data-f')), '—');
    });
    section.querySelectorAll('a[data-href]').forEach(a => {
      a.href = url;
      a.target = '_blank';
      a.rel = 'noopener';
    });
    return true;
  }

  // Plain GET, no custom headers: stays a CORS simple request and honours the server's max-age.
  fetch(LAB_ENDPOINT + '/lab')
    .then(res => { if (!res.ok) throw new Error('lab ' + res.status); return res.json(); })
    .then(data => {
      if (!render(data)) return;
      section.removeAttribute('hidden');
      const navLink = document.getElementById('nav-lab');
      if (navLink) navLink.hidden = false;
    })
    .catch(err => { console.debug('live lab unavailable:', err && err.message ? err.message : err); });
})();
