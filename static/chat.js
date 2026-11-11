(() => {
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.querySelectorAll(".chat").forEach(init);

  function init(root) {
    const log = root.querySelector(".chat-log"), form = root.querySelector(".chat-form");
    const input = form.querySelector("input"), send = form.querySelector("button");
    const chips = root.querySelector(".chat-chips");
    let history = [], busy = false;

    const bubble = (role, text) => {
      const m = document.createElement("div"); m.className = "msg " + role; m.textContent = text;
      log.appendChild(m); log.scrollTop = log.scrollHeight; return m;
    };
    const greet = () => bubble("bot", root.dataset.greeting);
    greet();

    function typewrite(el, text) {
      if (calm) { el.textContent = text; return Promise.resolve(); }
      return new Promise(res => {
        let i = 0; const step = Math.max(2, Math.ceil(text.length / 160));
        const t = setInterval(() => {
          i += step; el.textContent = text.slice(0, i); log.scrollTop = log.scrollHeight;
          if (i >= text.length) { clearInterval(t); res(); }
        }, 16);
      });
    }

    async function ask(text) {
      if (busy || !text.trim()) return;
      busy = true; send.disabled = true; if (chips) chips.hidden = true;
      bubble("user", text); history.push({ role: "user", content: text }); input.value = "";
      const typing = bubble("bot typing", ""); typing.innerHTML = "<i></i><i></i><i></i>";
      try {
        let reply;
        if (root.dataset.demo) {
          await new Promise(r => setTimeout(r, 900));
          reply = "This is a preview, so I can’t reach the AI from here. In the running app I answer using the open jobs and, once you log in, your CGPA and applications.";
        } else {
          const r = await fetch(root.dataset.endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRF-Token": root.dataset.csrf },
            body: JSON.stringify({ messages: history.slice(-12) })
          });
          const data = await r.json().catch(() => ({}));
          if (!r.ok) throw new Error(data.error || "Something went wrong. Please try again.");
          reply = data.reply;
        }
        typing.className = "msg bot"; typing.textContent = "";
        await typewrite(typing, reply); history.push({ role: "assistant", content: reply });
      } catch (e) {
        typing.className = "msg bot err"; typing.textContent = e.message || "Something went wrong.";
        history.pop();
      } finally { busy = false; send.disabled = false; input.focus({ preventScroll: true }); }
    }

    form.addEventListener("submit", e => { e.preventDefault(); ask(input.value); });
    root.querySelectorAll(".chat-chips .q").forEach(b => b.addEventListener("click", () => ask(b.textContent)));
    root.querySelector(".chat-clear").addEventListener("click", () => {
      if (busy) return; history = []; log.textContent = ""; greet(); if (chips) chips.hidden = false;
    });
  }
})();
