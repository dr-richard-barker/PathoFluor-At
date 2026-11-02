// Plate trajectories: each plate's change from its own hour-0 scan, through 1-48 h, in three
// features (docs/data/trajectories.json, from tables/seedling_plate_changes.csv).
const root = document.getElementById("traj");

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

async function start() {
  const THREE = await import("three");
  const { OrbitControls } = await import("three/addons/controls/OrbitControls.js");
  const D = await (await fetch("data/trajectories.json")).json();
  const TRT = ["Control", "flg22", "Pathogen"], VAR = { Control: "--series-1", flg22: "--series-2", Pathogen: "--series-3" };
  const css = n => getComputedStyle(root).getPropertyValue(n).trim();
  const AX = ["fwhm", "f685", "sw"];

  // symmetric scale per axis, so every path starts at the centre
  const R = 3;
  const span = Object.fromEntries(AX.map(a => [a, Math.max(...D.plates.flatMap(p => p.points.map(q => Math.abs(q[a])))) || 1]));
  const pos = q => new THREE.Vector3(q.fwhm / span.fwhm * R, q.f685 / span.f685 * R, q.sw / span.sw * R);

  const canvas = document.getElementById("tj-gl"), wrap = document.getElementById("tj-wrap"), tip = document.getElementById("tj-tip");
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x0b0b0d, 1);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1.6, 0.1, 200);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;

  function label(text, size = 0.3, color = "#d8d8dc") {
    const c = document.createElement("canvas"), g = c.getContext("2d"), px = 44;
    g.font = `${px}px -apple-system, Segoe UI, Roboto, sans-serif`;
    c.width = Math.ceil(g.measureText(text).width) + 8; c.height = px + 12;
    g.font = `${px}px -apple-system, Segoe UI, Roboto, sans-serif`;
    g.fillStyle = color; g.textBaseline = "middle"; g.fillText(text, 4, c.height / 2);
    const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
    s.scale.set(size * c.width / c.height, size, 1);
    return s;
  }

  // axes through the origin, with end labels and the span value
  const axCol = 0x55555f;
  const dirs = { fwhm: new THREE.Vector3(1, 0, 0), f685: new THREE.Vector3(0, 1, 0), sw: new THREE.Vector3(0, 0, 1) };
  const short = { fwhm: "red-peak width", f685: "685 nm emission", sw: "short-wave fraction" };
  const unit = { fwhm: "nm", f685: "counts/s", sw: "×10⁻³" };
  const axLabels = { fwhm: [], f685: [], sw: [] };
  AX.forEach(a => {
    const d = dirs[a];
    scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([d.clone().multiplyScalar(-R), d.clone().multiplyScalar(R)]),
      new THREE.LineBasicMaterial({ color: axCol })));
    const fmt = v => (Math.abs(v) >= 100 ? Math.round(v).toLocaleString() : v.toFixed(2));
    const lp = label(`+${fmt(span[a])} ${unit[a]}`, 0.24, "#a8a8b0"); lp.position.copy(d.clone().multiplyScalar(R + 0.35)); scene.add(lp);
    const ln = label(`−${fmt(span[a])}`, 0.24, "#a8a8b0"); ln.position.copy(d.clone().multiplyScalar(-R - 0.35)); scene.add(ln);
    const lt = label(short[a], 0.3); lt.position.copy(d.clone().multiplyScalar(R + 0.35)).add(new THREE.Vector3(0, 0.32, 0)); scene.add(lt);
    axLabels[a].push(lp, ln, lt);
  });
  const o = label("hour 0 (each plate's own baseline)", 0.22, "#a8a8b0"); o.position.set(0.2, -0.3, 0); scene.add(o);

  // paths
  const group = new THREE.Group(); scene.add(group);
  const pickables = [];
  function build() {
    group.clear(); pickables.length = 0;
    D.plates.forEach(p => {
      const col = new THREE.Color(css(VAR[p.treatment]) || "#888");
      const pts = p.points.map(pos);
      group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: col })));
      p.points.forEach((q, i) => {
        if (i === 0) return;
        const last = i === p.points.length - 1;
        const m = new THREE.Mesh(new THREE.SphereGeometry(last ? 0.11 : 0.07, 16, 12), new THREE.MeshBasicMaterial({ color: col }));
        m.position.copy(pts[i]); m.userData = { p, q };
        group.add(m); pickables.push(m);
      });
    });
    document.getElementById("tj-legend").innerHTML = TRT.map(t =>
      `<span style="--c:${css(VAR[t])}">${t} (${D.plates.filter(p => p.treatment === t).length} plates)</span>`).join("")
      + `<span style="--c:#888">larger dot = 48 h</span>`;
  }
  build();

  // views: oblique 3D and the three flat projections
  // [name, camera position, axis seen end-on (its labels are hidden in that view)]
  const VIEWS = [
    ["3D", [7, 5.5, 9], null],
    ["Width × emission", [0, 0, 13], "sw"],
    ["Width × short-wave", [0, 13, 0.001], "f685"],
    ["Emission × short-wave", [13, 0, 0], "fwhm"],
  ];
  const vg = document.getElementById("tj-views");
  VIEWS.forEach(([name, p, endOn], i) => {
    const b = document.createElement("button"); b.textContent = name; b.setAttribute("aria-pressed", String(i === 0));
    b.onclick = () => {
      camera.position.set(...p); controls.target.set(0, 0, 0); controls.update();
      AX.forEach(a => axLabels[a].forEach(l => { l.visible = a !== endOn; }));
      vg.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
    };
    vg.appendChild(b);
  });
  camera.position.set(...VIEWS[0][1]); controls.update();

  // hover
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  canvas.addEventListener("mousemove", ev => {
    const r = canvas.getBoundingClientRect();
    mouse.set((ev.clientX - r.left) / r.width * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(mouse, camera);
    const hit = ray.intersectObjects(pickables)[0];
    if (!hit) { tip.style.display = "none"; return; }
    const { p, q } = hit.object.userData;
    tip.innerHTML = `<b>${p.treatment} plate ${p.plate}, ${q.hour} h</b><br>Δ red-peak width ${q.fwhm.toFixed(2)} nm`
      + `<br>Δ 685 nm emission ${Math.round(q.f685).toLocaleString()} counts/s<br>Δ short-wave fraction ${q.sw.toFixed(2)} ×10⁻³`;
    tip.style.display = "block";
    tip.style.left = Math.min(ev.clientX - r.left + 12, r.width - 220) + "px";
    tip.style.top = (ev.clientY - r.top + 12) + "px";
  });
  canvas.addEventListener("mouseleave", () => { tip.style.display = "none"; });

  function resize() {
    const w = wrap.clientWidth, h = wrap.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(wrap);
  resize();
  new MutationObserver(build).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  let visible = true;
  new IntersectionObserver(es => { visible = es.some(e => e.isIntersecting); }).observe(wrap);
  (function loop() {
    requestAnimationFrame(loop);
    if (!visible) return;
    controls.update();
    renderer.render(scene, camera);
  })();
}
