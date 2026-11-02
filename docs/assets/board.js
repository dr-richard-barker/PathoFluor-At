// Monitoring replay board: held-out P(infected) per plate and hour (docs/data/alarm.json,
// from tables/alarm_replay.csv). Colour = probability in five steps; ▲ + outline = flagged.
(async function () {
  const root = document.getElementById("board");
  if (!root) return;
  const D = await (await fetch("data/alarm.json")).json();
  const hours = [...new Set(D.cells.map(c => c.hour))].sort((a, b) => a - b);
  const GROUPS = [["Pathogen", "Bacteria (P. syringae)"], ["Control", "Mock"], ["flg22", "flg22 (never in training)"]];
  const grid = document.getElementById("bd-grid"), tip = document.getElementById("bd-tip");
  const status = document.getElementById("bd-status");
  const cell = (t, p, h) => D.cells.find(c => c.treatment === t && c.plate === p && c.hour === h);
  let shown = hours.length, timer = null;

  function lum(hex) {
    const v = hex.replace("#", "").match(/../g).map(x => parseInt(x, 16) / 255)
      .map(c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
  }

  function build() {
    const css = n => getComputedStyle(root).getPropertyValue(n).trim();
    let html = `<div class="h" role="columnheader"></div>` + hours.map(h => `<div class="h" role="columnheader">${h} h</div>`).join("");
    GROUPS.forEach(([t, lab]) => {
      html += `<div class="grp">${lab}</div>`;
      const plates = [...new Set(D.cells.filter(c => c.treatment === t).map(c => c.plate))].sort();
      plates.forEach(p => {
        html += `<div class="rl" role="rowheader">${t} ${p}</div>`;
        hours.forEach((h, j) => {
          const c = cell(t, p, h), hide = j >= shown ? " hide" : "";
          if (!c || c.p === null) { html += `<div class="c ex${hide}" role="cell" title="excluded: hour-0 scans partly upright rescans">excl.</div>`; return; }
          const step = Math.min(4, Math.floor(c.p * 5)), bg = css(`--a${step}`) || "#888";
          const fg = lum(bg) > 0.3 ? "#111" : "#fff", flag = c.p > D.threshold;
          html += `<div class="c${flag ? " flag" : ""}${hide}" role="cell" style="background:${bg};color:${fg}" data-k="${t}|${p}|${h}">`
            + `${c.p.toFixed(2)}${flag ? " ▲" : ""}</div>`;
        });
      });
    });
    grid.innerHTML = html;
  }

  function summary(h) {
    const at = t => D.cells.filter(c => c.treatment === t && c.hour === h && c.p !== null);
    const f = t => `${at(t).filter(c => c.p > D.threshold).length} of ${at(t).length}`;
    return `At ${h} h: ${f("Pathogen")} Pathogen plates flagged · ${f("Control")} Control · ${f("flg22")} flg22`;
  }

  function update() {
    build();
    status.textContent = shown > 0 ? summary(hours[shown - 1]) : "Before treatment: every plate scanned for its baseline.";
  }

  grid.addEventListener("mousemove", ev => {
    const el = ev.target.closest(".c[data-k]");
    if (!el || el.classList.contains("hide")) { tip.style.display = "none"; return; }
    const [t, p, h] = el.dataset.k.split("|"), c = cell(t, +p, +h);
    const r = grid.getBoundingClientRect();
    tip.innerHTML = `<b>${t} plate ${p}, ${h} h</b><br>P(infected) = ${c.p.toFixed(3)}${c.p > D.threshold ? " (flagged)" : ""}<br>${c.n} hand-drawn Col-0 spectra<br><span style="color:var(--muted)">${c.scoring}</span>`;
    tip.style.display = "block";
    tip.style.left = Math.min(ev.clientX - r.left + 12, r.width - 230) + "px";
    tip.style.top = (ev.clientY - r.top + 12) + "px";
  });
  grid.addEventListener("mouseleave", () => { tip.style.display = "none"; });

  const play = document.getElementById("bd-play");
  play.onclick = () => {
    if (timer) { clearInterval(timer); timer = null; play.textContent = "▶ Play the monitoring run"; play.setAttribute("aria-pressed", "false"); return; }
    shown = 0; update();
    play.textContent = "❚❚ Pause"; play.setAttribute("aria-pressed", "true");
    timer = setInterval(() => {
      shown += 1; update();
      if (shown >= hours.length) { clearInterval(timer); timer = null; play.textContent = "▶ Play the monitoring run"; play.setAttribute("aria-pressed", "false"); }
    }, 1500);
  };
  document.getElementById("bd-all").onclick = () => {
    if (timer) { clearInterval(timer); timer = null; play.textContent = "▶ Play the monitoring run"; play.setAttribute("aria-pressed", "false"); }
    shown = hours.length; update();
  };

  new MutationObserver(update).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", update);
  update();
})();
