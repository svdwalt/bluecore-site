/* BlueCore site assistant widget.
 * Talks to the chat proxy (BlueCore-Chat) over HTTPS. The proxy holds the LLM key and enforces
 * origin, Turnstile, rate and budget limits; this file only renders and streams.
 * Configure the two constants below. While CHAT_ENDPOINT still contains "TAILNET" the widget
 * stays hidden, so the page can be published before the tunnel is live. */
(function () {
  const CHAT_ENDPOINT = 'https://bluecore-chat.tailab0ebc.ts.net';
  const TURNSTILE_SITEKEY = '';           // Cloudflare Turnstile site key; empty = no challenge
  const MAX_TURNS = 12;

  if (CHAT_ENDPOINT.includes('TAILNET')) return;

  const css = `
  #bc-chat-btn{position:fixed;right:18px;bottom:18px;z-index:50;font-family:var(--mono,monospace);font-size:.85rem;
    letter-spacing:.12em;color:var(--text,#dff0ff);background:var(--panel,rgba(2,6,16,.85));border:1px solid var(--blue,#2b6bff);
    padding:.65rem 1rem;cursor:pointer;box-shadow:0 0 18px rgba(43,107,255,.35);transition:box-shadow .2s,transform .2s}
  #bc-chat-btn:hover{box-shadow:0 0 28px rgba(77,163,255,.6);transform:translateY(-1px)}
  #bc-chat{position:fixed;right:18px;bottom:72px;z-index:51;width:min(380px,calc(100vw - 36px));height:min(520px,calc(100vh - 100px));
    display:flex;flex-direction:column;background:var(--panel,rgba(2,6,16,.92));backdrop-filter:blur(6px);
    border:1px solid var(--blue,#2b6bff);box-shadow:0 0 30px rgba(43,107,255,.35);font-family:var(--mono,monospace);color:var(--text,#dff0ff)}
  #bc-chat[hidden]{display:none}
  #bc-chat header{display:flex;align-items:center;justify-content:space-between;padding:.6rem .9rem;border-bottom:1px solid var(--blue-dim,#123a8a);
    font-size:.75rem;letter-spacing:.18em;color:var(--blue-bright,#4da3ff)}
  #bc-chat header button{background:none;border:0;color:var(--text-dim,#8fb4e8);font:inherit;cursor:pointer;font-size:1rem}
  #bc-log{flex:1;overflow-y:auto;padding:.8rem .9rem;display:flex;flex-direction:column;gap:.6rem;font-size:.85rem;line-height:1.5}
  .bc-m{max-width:92%;padding:.5rem .7rem;white-space:pre-wrap;word-wrap:break-word;border:1px solid var(--blue-faint,#0a1f4d)}
  .bc-u{align-self:flex-end;background:rgba(43,107,255,.18);border-color:var(--blue-dim,#123a8a)}
  .bc-a{align-self:flex-start;background:rgba(2,6,16,.6)}
  .bc-a.bc-busy::after{content:'▌';animation:bcblink 1s steps(2) infinite;color:var(--blue-bright,#4da3ff)}
  .bc-err{align-self:center;color:var(--muted,#5b7fc4);font-size:.75rem;text-align:center}
  @keyframes bcblink{50%{opacity:0}}
  #bc-form{display:flex;border-top:1px solid var(--blue-dim,#123a8a)}
  #bc-in{flex:1;background:transparent;border:0;outline:0;color:var(--text,#dff0ff);font:inherit;font-size:.9rem;padding:.7rem .9rem}
  #bc-in::placeholder{color:var(--muted,#5b7fc4)}
  #bc-send{background:none;border:0;border-left:1px solid var(--blue-dim,#123a8a);color:var(--blue-bright,#4da3ff);font:inherit;padding:0 1rem;cursor:pointer}
  #bc-send:disabled{opacity:.4;cursor:default}
  #bc-note{font-size:.62rem;color:var(--muted,#5b7fc4);padding:.35rem .9rem .5rem;line-height:1.4}
  #bc-ts{padding:0 .9rem}
  @media (max-width:560px){#bc-chat{right:0;bottom:0;width:100vw;height:100vh;border:0}#bc-chat-btn{right:12px;bottom:12px}}`;

  const style = document.createElement('style'); style.textContent = css; document.head.appendChild(style);

  const btn = document.createElement('button');
  btn.id = 'bc-chat-btn'; btn.type = 'button'; btn.textContent = '> CHAT';
  btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-controls', 'bc-chat');

  const panel = document.createElement('section');
  panel.id = 'bc-chat'; panel.hidden = true; panel.setAttribute('aria-label', 'BlueCore assistant');
  panel.innerHTML = `
    <header><span>BLUECORE // ASSISTANT</span><button type="button" id="bc-close" aria-label="Close chat">✕</button></header>
    <div id="bc-log" role="log" aria-live="polite"></div>
    <div id="bc-ts"></div>
    <form id="bc-form"><input id="bc-in" type="text" autocomplete="off" maxlength="1200" placeholder="Ask about ISE, 802.1X, MAB..." aria-label="Your message"><button id="bc-send" type="submit">SEND</button></form>
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
