// Plate time-lapse viewer: three treatments side by side, one plate, stepped through time.
// Images and index from scripts/12_site_media.py (docs/media/plates/, docs/data/plates.json).
(async function () {
  const root = document.getElementById("plates");
  if (!root) return;
  const D = await (await fetch("data/plates.json")).json();
  const TRT = D.treatments, H = D.hours;
  const LAYERS = [["cps", "Exposure-corrected"], ["raw", "As recorded"], ["ratio", "F685/F740 ratio"]];
  let layer = "cps", plate = 1, hi = H.indexOf(24), timer = null;

  const sel = document.getElementById("pl-plate");
  D.plates.forEach(p => sel.add(new Option(`${p}`, p)));
  sel.onchange = () => { plate = +sel.value; preload(); render(); };

  const lg = document.getElementById("pl-layers");
  LAYERS.forEach(([k, lab]) => {
    const b = document.createElement("button");
    b.textContent = lab; b.dataset.k = k;
    b.onclick = () => { layer = k; preload(); render(); };
    lg.appendChild(b);
  });

  const panels = document.getElementById("pl-panels");
  const figs = TRT.map(() => {
    const f = document.createElement("figure");
    f.className = "plate";
    f.innerHTML = `<figcaption></figcaption><div class="plate-img"><img alt="" width="${D.width}" height="${D.height}" decoding="async"><div class="lanes"></div></div>`;
    panels.appendChild(f);
    return f;
  });

  const slider = document.getElementById("pl-hour"), out = document.getElementById("pl-hour-out");
  slider.max = H.length - 1; slider.value = hi;
  slider.oninput = () => { hi = +slider.value; render(); };

  const key = (t, p, h) => `${t}_P${p}_H${String(h).padStart(2, "0")}`;
  const src = (l, t, p, h) => `media/plates/${l}_${key(t, p, h)}.webp`;
  const preloaded = new Set();
  function preload() {
    H.forEach(h => TRT.forEach(t => {
      const s = src(layer, t, plate, h);
      if (!preloaded.has(s)) { preloaded.add(s); const i = new Image(); i.src = s; }
    }));
  }

  function cbar() {
    const L = D.layers[layer];
    document.getElementById("pl-ramp").style.background = `linear-gradient(90deg, ${L.ramp.join(",")})`;
    const lo = document.getElementById("pl-lo"), hiEl = document.getElementById("pl-hi"), u = document.getElementById("pl-units");
    if (layer === "ratio") {
      lo.textContent = `${(2 ** -L.lim).toFixed(2)}×`;
      hiEl.textContent = `${(2 ** L.lim).toFixed(2)}×`;
      u.textContent = `F685/F740 relative to the Control median (${L.ref}); grey = median`;
    } else {
      lo.textContent = "0";
      hiEl.textContent = Math.round(L.max).toLocaleString();
      u.textContent = L.units;
    }
  }

  function render() {
    const h = H[hi];
    out.textContent = h === 0 ? "0 (before)" : `${h} h`;
    slider.value = hi;
    lg.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.k === layer)));
    figs.forEach((f, i) => {
      const t = TRT[i], k = key(t, plate, h);
      const tints = (D.tint_s[k] || []).map(x => x.toFixed(3)).join(" / ");
      f.querySelector("figcaption").innerHTML = `<b>${t}</b> · exposure ${tints} s`;
      const img = f.querySelector("img");
      img.src = src(layer, t, plate, h);
      img.alt = `${t}, plate ${plate}, ${h === 0 ? "before treatment" : h + " h after treatment"}: ${D.layers[layer].label}`;
      const labs = D.labels[k] || [];
      f.querySelector(".lanes").innerHTML = labs.map(l =>
        `<span style="left:${(l.x * 100).toFixed(1)}%" title="${l.text}">${l.lane}</span>`).join("");
    });
    cbar();
  }

  const play = document.getElementById("pl-play");
  play.onclick = () => {
    if (timer) { clearInterval(timer); timer = null; play.textContent = "▶ Play"; play.setAttribute("aria-pressed", "false"); return; }
    play.textContent = "❚❚ Pause"; play.setAttribute("aria-pressed", "true");
    timer = setInterval(() => { hi = (hi + 1) % H.length; render(); }, 1100);
  };

  preload();
  render();
})();
