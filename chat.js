/* BlueCore site assistant widget.
 * Talks to the chat proxy (BlueCore-Chat) over HTTPS. The proxy holds the LLM key and enforces
 * origin, Turnstile, rate and budget limits; this file only renders and streams.
 * Configure the two constants below. While CHAT_ENDPOINT still contains "TAILNET" the widget
 * stays hidden, so the page can be published before the tunnel is live. */
(function () {
  const CHAT_ENDPOINT = 'https://bluecore-chat.tailab0ebc.ts.net';
  const TURNSTILE_SITEKEY = '0x4AAAAAAEtAcasVDfJqcVl5';           // Cloudflare Turnstile site key; empty = no challenge
  const MAX_TURNS = 12;

  if (CHAT_ENDPOINT.includes('TAILNET')) return;

  const css = `
  #bc-chat-btn{position:fixed;right:18px;bottom:18px;z-index:50;font-family:var(--hand,cursive);font-size:1.15rem;
    color:var(--ink,#2b2b2b);background:var(--amber-bg,#fff2c2);border:2px solid var(--ink,#2b2b2b);
    border-radius:255px 15px 225px 15px / 15px 225px 15px 255px;box-shadow:2px 3px 0 -1px rgba(43,43,43,.28);
    padding:.45rem 1.1rem;cursor:pointer;transition:transform .15s}
  #bc-chat-btn:hover{transform:translateY(-1px)}
  #bc-chat{position:fixed;right:18px;bottom:72px;z-index:51;width:min(380px,calc(100vw - 36px));height:min(520px,calc(100vh - 100px));
    display:flex;flex-direction:column;background:var(--paper,#fff);border:2px solid var(--ink,#2b2b2b);
    border-radius:15px 225px 15px 255px / 255px 15px 225px 15px;box-shadow:2px 3px 0 -1px rgba(43,43,43,.28);
    font-family:var(--sans,sans-serif);color:var(--ink,#2b2b2b);overflow:hidden}
  #bc-chat[hidden]{display:none}
  #bc-chat header{display:flex;align-items:center;justify-content:space-between;padding:.5rem 1.1rem;border-bottom:2px dashed var(--rule,#d9d2be);
    font-family:var(--hand,cursive);font-size:1.2rem;color:var(--amber,#8a6d1f)}
  #bc-chat header button{background:none;border:0;color:var(--ink-soft,#5a564d);font:inherit;cursor:pointer;font-size:1.1rem}
  #bc-log{flex:1;overflow-y:auto;padding:.8rem 1rem;display:flex;flex-direction:column;gap:.6rem;font-size:.95rem;line-height:1.5}
  .bc-m{max-width:92%;padding:.5rem .8rem;white-space:pre-wrap;word-wrap:break-word;border:1.5px solid var(--ink,#2b2b2b);border-radius:12px}
  .bc-u{align-self:flex-end;background:var(--blue-bg,#dbe9f7);border-bottom-right-radius:3px}
  .bc-a{align-self:flex-start;background:var(--green-bg,#e3f2df);border-bottom-left-radius:3px}
  .bc-a.bc-busy::after{content:'▌';animation:bcblink 1s steps(2) infinite;color:var(--amber,#8a6d1f)}
  .bc-err{align-self:center;color:var(--red,#b93a2b);font-size:.85rem;text-align:center}
  @keyframes bcblink{50%{opacity:0}}
  #bc-form{display:flex;border-top:2px dashed var(--rule,#d9d2be)}
  #bc-in{flex:1;background:transparent;border:0;outline:0;color:var(--ink,#2b2b2b);font:inherit;font-size:.95rem;padding:.7rem 1rem}
  #bc-in::placeholder{color:var(--ink-soft,#5a564d)}
  #bc-send{background:none;border:0;border-left:2px dashed var(--rule,#d9d2be);color:var(--blue,#1a4d8f);font-family:var(--hand,cursive);font-size:1.1rem;padding:0 1rem;cursor:pointer}
  #bc-send:disabled{opacity:.4;cursor:default}
  #bc-note{font-size:.78rem;color:var(--ink-soft,#5a564d);padding:.35rem 1rem .6rem;line-height:1.4}
  #bc-ts{padding:0 1rem}
  @media (max-width:560px){#bc-chat{right:0;bottom:0;width:100vw;height:100vh;border:0;border-radius:0}#bc-chat-btn{right:12px;bottom:12px}}`;

  const style = document.createElement('style'); style.textContent = css; document.head.appendChild(style);

  const btn = document.createElement('button');
  btn.id = 'bc-chat-btn'; btn.type = 'button'; btn.textContent = 'Ask me';
  btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-controls', 'bc-chat');

  const panel = document.createElement('section');
  panel.id = 'bc-chat'; panel.hidden = true; panel.setAttribute('aria-label', 'BlueCore assistant');
  panel.innerHTML = `
    <header><span>BlueCore assistant</span><button type="button" id="bc-close" aria-label="Close chat">✕</button></header>
    <div id="bc-log" role="log" aria-live="polite"></div>
    <div id="bc-ts"></div>
    <form id="bc-form"><input id="bc-in" type="text" autocomplete="off" maxlength="1200" placeholder="Ask about ISE, 802.1X, MAB..." aria-label="Your message"><button id="bc-send" type="submit">Send</button></form>
    <div id="bc-note">Answers come from an AI model running on BlueCore's own lab hardware and may be wrong. Please don't paste confidential data.</div>`;
  document.body.append(btn, panel);

  const log = panel.querySelector('#bc-log'), form = panel.querySelector('#bc-form'),
        input = panel.querySelector('#bc-in'), send = panel.querySelector('#bc-send');
  const history = [];
  let opened = false, busy = false, tsWidget = null, tsToken = '';

  function add(cls, text) {
    const el = document.createElement('div'); el.className = 'bc-m ' + cls; el.textContent = text;
    log.appendChild(el); log.scrollTop = log.scrollHeight; return el;
  }
  function note(text) { const el = document.createElement('div'); el.className = 'bc-err'; el.textContent = text; log.appendChild(el); log.scrollTop = log.scrollHeight; }

  function loadTurnstile() {
    if (!TURNSTILE_SITEKEY) return;
    const s = document.createElement('script');
    s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?onload=bcTurnstileReady'; s.async = true;
    window.bcTurnstileReady = function () {
      tsWidget = turnstile.render('#bc-ts', { sitekey: TURNSTILE_SITEKEY, appearance: 'interaction-only', theme: 'dark',
        callback: t => { tsToken = t; }, 'expired-callback': () => { tsToken = ''; turnstile.reset(tsWidget); } });
    };
    document.head.appendChild(s);
  }
  async function token() {
    if (!TURNSTILE_SITEKEY) return null;
    for (let i = 0; i < 40 && !tsToken; i++) await new Promise(r => setTimeout(r, 250));
    const t = tsToken; tsToken = ''; if (tsWidget !== null) turnstile.reset(tsWidget);
    return t;
  }

  async function open() {
    panel.hidden = false; btn.setAttribute('aria-expanded', 'true'); input.focus();
    if (opened) return; opened = true;
    loadTurnstile();
    try {
      const h = await fetch(CHAT_ENDPOINT + '/health', { cache: 'no-store' }).then(r => r.json());
      if (!h.ok) throw 0;
      add('bc-a', 'Hi. Ask me about BlueCore, Cisco ISE, 802.1X, EAP-TLS or MAB.');
    } catch { note('The assistant is offline right now. Try again later.'); send.disabled = true; }
  }
  function close() { panel.hidden = true; btn.setAttribute('aria-expanded', 'false'); btn.focus(); }
  btn.addEventListener('click', () => panel.hidden ? open() : close());
  panel.querySelector('#bc-close').addEventListener('click', close);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden) close(); });

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const text = input.value.trim(); if (!text || busy) return;
    busy = true; send.disabled = true; input.value = '';
    add('bc-u', text); history.push({ role: 'user', content: text });
    while (history.length > MAX_TURNS) history.shift();
    if (history[0].role !== 'user') history.shift();
    const bubble = add('bc-a bc-busy', '');
    try {
      const res = await fetch(CHAT_ENDPOINT + '/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history, turnstile: await token() }) });
      if (!res.ok) { let m = 'Something went wrong.'; try { m = (await res.json()).error || m; } catch {} throw new Error(m); }
      const reader = res.body.getReader(), dec = new TextDecoder(); let buf = '', out = '';
      for (;;) {
        const { value, done } = await reader.read(); if (done) break;
        buf += dec.decode(value, { stream: true });
        let i; while ((i = buf.indexOf('\n\n')) >= 0) {
          const line = buf.slice(0, i).trim(); buf = buf.slice(i + 2);
          if (!line.startsWith('data:')) continue;
          const data = line.slice(5).trim(); if (data === '[DONE]') continue;
          let j; try { j = JSON.parse(data); } catch { continue; }
          if (j.error) throw new Error(j.error);
          if (j.t) { out += j.t; bubble.textContent = out; log.scrollTop = log.scrollHeight; }
        }
      }
      if (out) history.push({ role: 'assistant', content: out }); else { bubble.remove(); note('No answer came back. Try again.'); }
    } catch (err) { bubble.remove(); history.pop(); note(err.message || 'Something went wrong.'); }
    finally { bubble.classList.remove('bc-busy'); busy = false; send.disabled = false; input.focus(); }
  });
})();
