// Hyperspectral cube viewer: one row-scan as a point cloud of (along row, wavelength, across row),
// stepped through time, with a wavelength slice and per-block spectra. Data: docs/data/cube.json and
// docs/data/cube/*.bin from scripts/12_site_media.py. three.js is loaded on demand; without WebGL
// the static figure is shown instead.
const root = document.getElementById("cube");

function webglOK() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl")));
  } catch (e) { return false; }
}

if (root) {
  if (!webglOK()) root.classList.add("no-webgl");
  else {
    const io = new IntersectionObserver(es => {
      if (es.some(e => e.isIntersecting)) { io.disconnect(); start().catch(err => { console.error(err); root.classList.add("no-webgl"); }); }
    }, { rootMargin: "300px" });
    io.observe(root);
  }
}

// Intensity ramp shared with the plate images (scripts/12_site_media.py RAMP_INTENSITY).
const RAMP = ["#000000", "#3b0a0c", "#7f1416", "#c42a1f", "#ef6a3c", "#fbb28f", "#fff1e8"];
function lut() {
  const c = RAMP.map(h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16) / 255));
  const out = new Float32Array(256 * 3);
  for (let q = 0; q < 256; q++) {
    const t = q / 255 * (c.length - 1), i = Math.min(Math.floor(t), c.length - 2), f = t - i;
    for (let k = 0; k < 3; k++) out[q * 3 + k] = c[i][k] * (1 - f) + c[i + 1][k] * f;
  }
  return out;
}

async function start() {
  const THREE = await import("three");
  const { OrbitControls } = await import("three/addons/controls/OrbitControls.js");
  const M = await (await fetch("data/cube.json")).json();
  const WL = M.wavelength_nm, NB = WL.length, W = M.width, HH = M.height;
  const HOURS = [...new Set(M.cubes.map(c => c.hour))].sort((a, b) => a - b);
  const LUT = lut();
  const cache = new Map();
  let trt = "Control", hi = HOURS.indexOf(24), band = WL.indexOf(685);
  let cur = null;

  async function load(t, h) {
    const k = `${t}|${h}`;
    if (cache.has(k)) return cache.get(k);
    const meta = M.cubes.find(c => c.treatment === t && c.hour === h);
    const buf = await (await fetch(meta.file)).arrayBuffer();
    const n = meta.n;
    const d = { meta, n, X: new Uint16Array(buf, 0, n), Y: new Uint16Array(buf, 2 * n, n), Q: new Uint8Array(buf, 4 * n, n * NB) };
    d.index = new Map();
    for (let i = 0; i < n; i++) d.index.set(d.X[i] * 4096 + d.Y[i], i);
    cache.set(k, d);
    return d;
  }

  // ---- scene. Scene axes: x = along row, y = wavelength (up), z = across row.
  const canvas = document.getElementById("cb-gl"), wrap = document.getElementById("cb-wrap");
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x0b0b0d, 1);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1.6, 0.1, 200);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  const SX = 10 / W, SY = 6 / (WL[NB - 1] - WL[0]);
  const xOf = X => (X - W / 2) * SX, zOf = Y => (Y - HH / 2) * SX, yOf = wl => (wl - WL[0]) * SY;
  const home = () => { camera.position.set(9.5, 7.5, 13); controls.target.set(0, 2.7, 0); controls.update(); };
  home();

  function label(text, size = 0.32, color = "#d8d8dc") {
    const c = document.createElement("canvas"), g = c.getContext("2d"), px = 48;
    g.font = `${px}px -apple-system, Segoe UI, Roboto, sans-serif`;
    c.width = Math.ceil(g.measureText(text).width) + 8; c.height = px + 12;
    g.font = `${px}px -apple-system, Segoe UI, Roboto, sans-serif`;
    g.fillStyle = color; g.textBaseline = "middle"; g.fillText(text, 4, c.height / 2);
    const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
    s.scale.set(size * c.width / c.height, size, 1);
    return s;
  }

  // frame and axes
  const x0 = xOf(0), x1 = xOf(W), z0 = zOf(0), z1 = zOf(HH), yTop = yOf(WL[NB - 1]);
  const frame = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(x1 - x0, yTop, z1 - z0)),
    new THREE.LineBasicMaterial({ color: 0x3a3a42 }));
  frame.position.set((x0 + x1) / 2, yTop / 2, (z0 + z1) / 2);
  scene.add(frame);
  const ticks = [];
  [500, 550, 600, 650, 700, 750, 800].forEach(w => {
    ticks.push(new THREE.Vector3(x1, yOf(w), z1), new THREE.Vector3(x1 + 0.25, yOf(w), z1));
    const s = label(`${w} nm`, 0.28, "#a8a8b0"); s.position.set(x1 + 0.8, yOf(w), z1); scene.add(s);
  });
  scene.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(ticks), new THREE.LineBasicMaterial({ color: 0x8a8a92 })));
  const lx = label("along the row →", 0.42); lx.position.set(0, -0.45, z1 + 0.5); scene.add(lx);
  const lz = label("across the row →", 0.42); lz.position.set(x0 - 0.6, -0.45, 0); scene.add(lz);
  const ly = label("wavelength", 0.34); ly.position.set(x1 + 0.9, yTop + 0.5, z1); scene.add(ly);

  // slicing plane
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, z1 - z0),
    new THREE.MeshBasicMaterial({ color: 0x9fc7ff, transparent: true, opacity: 0.12, side: THREE.DoubleSide, depthWrite: false }));
  plane.rotation.x = -Math.PI / 2;
  const planeEdge = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(x0, 0, z0), new THREE.Vector3(x1, 0, z0), new THREE.Vector3(x1, 0, z1), new THREE.Vector3(x0, 0, z1)]),
    new THREE.LineBasicMaterial({ color: 0x9fc7ff }));
  const planeGroup = new THREE.Group(); planeGroup.add(plane, planeEdge);
  plane.position.set((x0 + x1) / 2, 0, (z0 + z1) / 2);
  scene.add(planeGroup);

  const mat = new THREE.PointsMaterial({ size: 0.06, vertexColors: true, sizeAttenuation: true });
  let points = null;
  const QMIN = 40;   // hide dim points (below (40/255)^2 = 2.5% of the scale maximum)

  function buildPoints(d) {
    let m = 0;
    for (let i = 0; i < d.Q.length; i++) if (d.Q[i] >= QMIN) m++;
    const pos = new Float32Array(m * 3), col = new Float32Array(m * 3);
    let j = 0;
    for (let i = 0; i < d.n; i++) {
      const x = xOf(d.X[i]), z = zOf(d.Y[i]);
      for (let b = 0; b < NB; b++) {
        const q = d.Q[i * NB + b];
        if (q < QMIN) continue;
        pos[j * 3] = x; pos[j * 3 + 1] = yOf(WL[b]); pos[j * 3 + 2] = z;
        col[j * 3] = LUT[q * 3]; col[j * 3 + 1] = LUT[q * 3 + 1]; col[j * 3 + 2] = LUT[q * 3 + 2];
        j++;
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    if (points) { scene.remove(points); points.geometry.dispose(); }
    points = new THREE.Points(g, mat);
    scene.add(points);
  }

  // ---- slice image and spectrum
  const sc = document.getElementById("cb-slice"), sg = sc.getContext("2d");
  sc.width = W; sc.height = HH;
  function drawSlice() {
    const img = sg.createImageData(W, HH);
    for (let k = 3; k < img.data.length; k += 4) img.data[k] = 255;
    const d = cur;
    for (let i = 0; i < d.n; i++) {
      const q = d.Q[i * NB + band], o = (d.Y[i] * W + d.X[i]) * 4;
      if (d.Y[i] >= HH || d.X[i] >= W) continue;
      img.data[o] = LUT[q * 3] * 255; img.data[o + 1] = LUT[q * 3 + 1] * 255; img.data[o + 2] = LUT[q * 3 + 2] * 255;
    }
    sg.putImageData(img, 0, 0);
  }

  const svg = document.getElementById("cb-spec"), ns = "http://www.w3.org/2000/svg";
  const el = (t, a) => { const e = document.createElementNS(ns, t); for (const k in a) e.setAttribute(k, a[k]); return e; };
  const SW = 360, SH = 170, P = { l: 58, r: 10, t: 10, b: 30 };
  function drawSpec(i) {
    svg.innerHTML = "";
    const vmax = M.vmax_cps;
    const ys = i === null ? null : Array.from({ length: NB }, (_, b) => (cur.Q[i * NB + b] / 255) ** 2 * vmax);
    const hi = ys ? Math.max(...ys) * 1.08 || 1 : vmax;
    const x = w => P.l + (w - WL[0]) / (WL[NB - 1] - WL[0]) * (SW - P.l - P.r);
    const y = v => SH - P.b - v / hi * (SH - P.t - P.b);
    const gr = el("g", { class: "grid" });
    for (let k = 0; k <= 3; k++) {
      const v = hi * k / 3; gr.appendChild(el("line", { x1: P.l, x2: SW - P.r, y1: y(v), y2: y(v) }));
      const t = el("text", { x: P.l - 4, y: y(v) + 4, "text-anchor": "end" }); t.textContent = Math.round(v).toLocaleString(); svg.appendChild(t);
    }
    svg.appendChild(gr);
    [500, 600, 700, 800].forEach(w => { const t = el("text", { x: x(w), y: SH - P.b + 14, "text-anchor": "middle" }); t.textContent = w; svg.appendChild(t); });
    const xl = el("text", { x: (P.l + SW - P.r) / 2, y: SH - 2, "text-anchor": "middle" }); xl.textContent = "Wavelength (nm)"; svg.appendChild(xl);
    const yl = el("text", { x: 10, y: (P.t + SH - P.b) / 2, transform: `rotate(-90 10 ${(P.t + SH - P.b) / 2})`, "text-anchor": "middle" });
    yl.textContent = "counts s⁻¹"; svg.appendChild(yl);
    svg.appendChild(el("line", { x1: x(WL[band]), x2: x(WL[band]), y1: P.t, y2: SH - P.b, stroke: "#9fc7ff", "stroke-width": 1 }));
    if (!ys) {
      const t = el("text", { x: (P.l + SW) / 2, y: SH / 2, "text-anchor": "middle" }); t.textContent = "Hover over the slice to see a spectrum"; svg.appendChild(t);
      return;
    }
    const d = ys.map((v, b) => (b ? "L" : "M") + x(WL[b]).toFixed(1) + "," + y(v).toFixed(1)).join("");
    svg.appendChild(el("path", { d, fill: "none", stroke: "#ef6a3c", "stroke-width": 2, "stroke-linejoin": "round" }));
  }
  sc.addEventListener("mousemove", ev => {
    const r = sc.getBoundingClientRect();
    const X = Math.floor((ev.clientX - r.left) / r.width * W), Y = Math.floor((ev.clientY - r.top) / r.height * HH);
    let best = null;
    for (let dx = -2; dx <= 2 && best === null; dx++) for (let dy = -2; dy <= 2 && best === null; dy++) {
      const i = cur.index.get((X + dx) * 4096 + (Y + dy)); if (i !== undefined) best = i;
    }
    drawSpec(best);
  });
  sc.addEventListener("mouseleave", () => drawSpec(null));

  // ---- controls
  const hs = document.getElementById("cb-hour"), ho = document.getElementById("cb-hour-out");
  const ws = document.getElementById("cb-wl"), wo = document.getElementById("cb-wl-out");
  hs.max = HOURS.length - 1; hs.value = hi; ws.max = NB - 1; ws.value = band;
  async function refresh() {
    cur = await load(trt, HOURS[hi]);
    const h = HOURS[hi];
    ho.textContent = (h === 0 ? "0 (before)" : `${h} h`) + (cur.meta.direction ? "" : " (lane order unconfirmed)");
    ["Control", "Pathogen"].forEach(t => document.getElementById(`cb-${t}`).setAttribute("aria-pressed", String(t === trt)));
    buildPoints(cur);
    setBand();
  }
  function setBand() {
    wo.textContent = `${WL[band]} nm`;
    planeGroup.position.y = yOf(WL[band]);
    drawSlice(); drawSpec(null);
  }
  hs.oninput = () => { hi = +hs.value; refresh(); };
  ws.oninput = () => { band = +ws.value; setBand(); };
  ["Control", "Pathogen"].forEach(t => { document.getElementById(`cb-${t}`).onclick = () => { trt = t; refresh(); }; });
  document.getElementById("cb-reset").onclick = home;

  function resize() {
    const w = wrap.clientWidth, h = wrap.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(wrap);
  resize();

  let visible = true;
  new IntersectionObserver(es => { visible = es.some(e => e.isIntersecting); }).observe(wrap);
  (function loop() {
    requestAnimationFrame(loop);
    if (!visible) return;
    controls.update();
    renderer.render(scene, camera);
  })();

  await refresh();
}
