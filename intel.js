/* BlueCore threat pulse. Reads a cached, curated snapshot from the BlueCore-Chat proxy
 * (GET /intel) and fills #threat-pulse. Nothing the visitor does reaches the intel service.
 * While INTEL_ENDPOINT still contains "TAILNET" the section stays hidden (same kill-switch as chat.js).
 * The JSON is untrusted: every field is type-checked and only ever written via textContent. */
(function () {
  const INTEL_ENDPOINT = 'https://bluecore-chat.tailab0ebc.ts.net';
  const MAX_LIST_ROWS = 5;      // rows per by_malware list
  const MAX_TABLE_ROWS = 6;     // rows in the newest-C2 table

  if (INTEL_ENDPOINT.includes('TAILNET')) return;

  const section = document.getElementById('threat-pulse');
  if (!section) return;

  const nf = new Intl.NumberFormat('en-GB');
  const isObj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const isNum = v => typeof v === 'number' && Number.isFinite(v);
  const str = (v, fallback) => (typeof v === 'string' && v.trim()) ? v.trim() : fallback;

  // 'feodo.total' -> data.feodo.total, or undefined if any hop is not an object.
  function pick(data, path) {
    let cur = data;
    for (const key of path.split('.')) {
      if (!isObj(cur)) return undefined;
      cur = cur[key];
    }
    return cur;
  }
  const fmtNum = v => isNum(v) ? nf.format(v) : '—';

  // "2026-09-14 11:20:03" or ISO -> "2026-09-14 11:20"
  function shortTime(v) {
    const s = str(v, '');
    const m = s.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})/);
    return m ? m[1] + ' ' + m[2] : (s || '—');
  }

  function fillFields(data) {
    section.querySelectorAll('[data-f]').forEach(el => {
      el.textContent = fmtNum(pick(data, el.getAttribute('data-f')));
    });
  }

  function fillLists(data) {
    section.querySelectorAll('[data-list]').forEach(ul => {
      const rows = pick(data, ul.getAttribute('data-list'));
      ul.textContent = '';
      const items = Array.isArray(rows) ? rows.filter(r => isObj(r) && typeof r.name === 'string' && isNum(r.count)) : [];
      if (!items.length) { ul.hidden = true; return; }
      ul.hidden = false;
      for (const r of items.slice(0, MAX_LIST_ROWS)) {
        const li = document.createElement('li');
        const name = document.createElement('span'); name.className = 'kv-name'; name.textContent = r.name;
        const count = document.createElement('span'); count.className = 'kv-count'; count.textContent = nf.format(r.count);
        li.append(name, count); ul.appendChild(li);
      }
    });
  }

  function fillNewest(data) {
    const box = document.getElementById('tp-newest');
    if (!box) return;
    const tbody = box.querySelector('tbody');
    const rows = pick(data, 'feodo.newest');
    const items = Array.isArray(rows) ? rows.filter(r => isObj(r) && typeof r.ip === 'string' && r.ip.trim()) : [];
    if (!tbody || !items.length) { box.hidden = true; return; }
    tbody.textContent = '';
    for (const r of items.slice(0, MAX_TABLE_ROWS)) {
      const tr = document.createElement('tr');
      for (const v of [r.ip.trim(), str(r.malware, '—'), str(r.country, '—'), shortTime(r.first_seen)]) {
        const td = document.createElement('td'); td.textContent = v; tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    box.hidden = false;
  }

  function fillUpdated(data) {
    const el = document.getElementById('tp-updated');
    if (!el) return;
    const t = Date.parse(str(data.generated_at, ''));
    if (!Number.isFinite(t)) { el.textContent = '—'; return; }
    const mins = Math.max(0, Math.round((Date.now() - t) / 60000));
    const ago = mins < 60 ? mins + ' min ago' : Math.round(mins / 60) + ' h ago';
    const d = new Date(t), pad = n => String(n).padStart(2, '0');
    el.textContent = ago + ' (' + pad(d.getUTCHours()) + ':' + pad(d.getUTCMinutes()) + ' UTC)';
  }

  function fillThreatfoxSub(data) {
    const el = document.getElementById('tp-threatfox-sub');
    const days = pick(data, 'threatfox.days');
    if (el && isNum(days) && days !== 1) el.textContent = 'reported, last ' + nf.format(days) + ' days';
  }

  function render(data) {
    if (!isObj(data)) return false;
    // Hide any card whose section is missing; the table follows the feodo card.
    const cards = { 'tp-feodo': 'feodo', 'tp-threatfox': 'threatfox', 'tp-tor': 'torexit' };
    let visible = 0;
    for (const id in cards) {
      const card = document.getElementById(id);
      if (!card) continue;
      const present = isObj(data[cards[id]]);
      card.hidden = !present;
      if (present) visible++;
    }
    if (!visible) return false;
    fillFields(data);
    fillLists(data);
    fillNewest(data);
    fillThreatfoxSub(data);
    fillUpdated(data);
    return true;
  }

  // Plain GET, no custom headers, no cache option: stays a CORS simple request and honours
  // the server's Cache-Control max-age.
  fetch(INTEL_ENDPOINT + '/intel')
    .then(res => { if (!res.ok) throw new Error('intel ' + res.status); return res.json(); })
    .then(data => { if (render(data)) section.removeAttribute('hidden'); })
    .catch(err => { console.debug('threat pulse unavailable:', err && err.message ? err.message : err); });
})();
