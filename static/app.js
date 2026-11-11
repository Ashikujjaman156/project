(() => {
  const d = document, root = d.documentElement;
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));

  // toasts
  d.querySelectorAll(".flash").forEach((f, i) => {
    const kill = () => { f.classList.add("out"); setTimeout(() => f.remove(), 300); };
    f.addEventListener("click", kill); setTimeout(kill, 5500 + i * 600);
  });

  // page scroll progress bar
  const bar = d.createElement("div"); bar.className = "progress"; bar.setAttribute("aria-hidden", "true");
  d.body.appendChild(bar);

  // split big headings into words that rise in one after another
  if (!calm) d.querySelectorAll(".big").forEach(h => {
    const text = h.textContent.trim(); h.classList.remove("reveal");
    h.setAttribute("aria-label", text); h.textContent = "";
    text.split(/\s+/).forEach((w, i, all) => {
      const s = d.createElement("span"); s.className = "wd"; s.style.setProperty("--i", i);
      s.setAttribute("aria-hidden", "true"); s.textContent = w; h.appendChild(s);
      if (i < all.length - 1) h.appendChild(d.createTextNode(" "));
    });
  });

  // staggered reveals for rows, tables, facts, team, steps
  d.querySelectorAll(".list .row,.olist .orow,.tablewrap tbody tr,.facts>div,.team-list li,.steps li").forEach((el, i) => {
    el.classList.add("reveal"); el.style.transitionDelay = (i % 8) * 60 + "ms";
  });

  const io = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return;
    const el = e.target; el.classList.add("in"); io.unobserve(el);
    if (el.dataset.count && !calm) count(el);
    if (el.style.transitionDelay) setTimeout(() => { el.classList.remove("reveal", "in"); el.style.transitionDelay = ""; }, 1400);
  }), { threshold: .2 });
  d.querySelectorAll(".reveal,.big,[data-count]").forEach(el => io.observe(el));
  function count(el) {
    const end = +el.dataset.count, t0 = performance.now();
    (function tick(t) {
      const p = clamp((t - t0) / 1300), e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(end * e); if (p < 1) requestAnimationFrame(tick);
    })(t0);
  }

  // pointer parallax
  if (!calm && matchMedia("(pointer: fine)").matches)
    d.querySelectorAll(".stage,.side,.pagehead").forEach(s => s.addEventListener("pointermove", e => {
      const r = s.getBoundingClientRect();
      s.style.setProperty("--mx", ((e.clientX - r.left) / r.width - .5) * 2);
      s.style.setProperty("--my", ((e.clientY - r.top) / r.height - .5) * 2);
    }));

  // scroll-driven scenes
  const top = d.querySelector(".top"), heads = [...d.querySelectorAll(".stage,.pagehead")];
  const home = d.querySelector(".stage"), steps = d.querySelector(".steps"), foot = d.querySelector(".foot");
  const wins = home ? [...home.querySelectorAll(".w:not(.hold)")] : [];
  const order = wins.map((_, i) => i).sort((a, b) => (a * 7919) % wins.length - (b * 7919) % wins.length);
  let lit = -1, last = scrollY, queued = false;

  if (calm && steps) { steps.style.setProperty("--sp", 1); [...steps.children].forEach(li => li.classList.add("on")); }

  function frame() {
    queued = false;
    const y = scrollY, vh = innerHeight;
    root.style.setProperty("--pg", clamp(y / Math.max(1, root.scrollHeight - vh)).toFixed(4));
    if (top) {
      top.classList.toggle("scrolled", y > 40);
      if (y > last + 6 && y > 240) top.classList.add("hide"); else if (y < last - 6 || y < 80) top.classList.remove("hide");
    }
    last = y;
    if (calm) return;
    heads.forEach(s => {
      const r = s.getBoundingClientRect();
      if (r.bottom < -50 || r.top > vh) return;
      s.style.setProperty("--hp", clamp(-r.top / Math.max(1, r.height * .85)).toFixed(3));
    });
    if (home) {   // windows light up as you scroll
      const r = home.getBoundingClientRect(), n = Math.floor(clamp(-r.top / (r.height * .7)) * wins.length);
      if (n !== lit) { lit = n; order.forEach((w, i) => wins[w].classList.toggle("lit", i < n)); }
    }
    if (steps) {
      const r = steps.getBoundingClientRect(), p = clamp((vh * .78 - r.top) / (r.height + vh * .1));
      steps.style.setProperty("--sp", p.toFixed(3));
      [...steps.children].forEach((li, i) => li.classList.toggle("on", p >= i / steps.children.length + .02));
    }
    if (foot) {
      const w = foot.querySelector(".word"), r = foot.getBoundingClientRect();
      w.style.setProperty("--fp", clamp((vh - r.top) / (r.height * 1.1)).toFixed(3));
    }
  }
  addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(frame); } }, { passive: true });
  addEventListener("resize", frame); frame();
})();
