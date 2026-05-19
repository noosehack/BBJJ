"use strict";

// ═══════════════════════════════════════════════════════════════════
// MOR KNOWLEDGE BASE — presentation metadata only, not engine logic
// ═══════════════════════════════════════════════════════════════════

const MOR_INFO = {
  PASS:             { name: "Pass",              desc: "No action taken",                     intent: "pass",    verb: "passes" },
  takedown:         { name: "Takedown",          desc: "Double-leg takedown to top position",  intent: "advance", verb: "shoots a takedown" },
  pull_guard:       { name: "Pull Guard",        desc: "Pulls opponent into closed guard",     intent: "advance", verb: "pulls guard" },
  hip_bump:         { name: "Hip Bump Sweep",    desc: "Sweeps from guard to mount",           intent: "advance", verb: "hip-bumps to mount" },
  triangle:         { name: "Triangle Choke",    desc: "Submission from closed guard",         intent: "submit",  verb: "attacks the triangle" },
  ogrd_sweep:       { name: "Butterfly Sweep",   desc: "Sweeps from open guard",               intent: "advance", verb: "hits a butterfly sweep" },
  ogrd_retain:      { name: "Guard Retention",   desc: "Maintains open guard structure",        intent: "control", verb: "retains guard" },
  hgrd_sweep:       { name: "Half Guard Sweep",  desc: "Sweeps from half guard",               intent: "advance", verb: "sweeps from half guard" },
  hgrd_pass:        { name: "Half Guard Pass",   desc: "Passes half guard to side control",     intent: "advance", verb: "passes the half guard" },
  trtl_standup:     { name: "Technical Stand-up", desc: "Stands up from turtle position",       intent: "escape",  verb: "stands up" },
  trtl_sit:         { name: "Sit to Guard",      desc: "Sits out to recover open guard",        intent: "escape",  verb: "sits to guard" },
  sctr_shrimp:      { name: "Shrimp Escape",     desc: "Hip escape from side control",          intent: "escape",  verb: "shrimps out" },
  sctr_mount:       { name: "Advance to Mount",  desc: "Transitions from side control to mount", intent: "advance", verb: "advances to mount" },
  sctr_americana:   { name: "Americana",         desc: "Shoulder lock from side control",       intent: "submit",  verb: "attacks the americana" },
  mnt_bridge:       { name: "Bridge Reversal",   desc: "Bridges to reverse mount to guard",     intent: "escape",  verb: "bridges out" },
  mnt_elbow_knee:   { name: "Elbow-Knee Escape", desc: "Creates space to recover guard",        intent: "escape",  verb: "goes for elbow-knee escape" },
  mnt_sub:          { name: "Mount Submission",  desc: "Submission attempt from mount",          intent: "submit",  verb: "attacks from mount" },
  mnt_pressure:     { name: "Mount Pressure",    desc: "Holds mount with heavy pressure",       intent: "control", verb: "applies pressure" },
  bctr_turn_in:     { name: "Turn-In Escape",    desc: "Turns in to escape back control",       intent: "escape",  verb: "turns in to escape" },
  bctr_rnc:         { name: "Rear Naked Choke",  desc: "Choke from back control",               intent: "submit",  verb: "attacks the RNC" },
  bctr_control:     { name: "Back Control",      desc: "Maintains hooks and control",            intent: "control", verb: "maintains back control" },
};

const INTENT_LABELS = {
  pass:    "INACTIVE",
  advance: "ADVANCING",
  submit:  "SUBMITTING",
  control: "CONTROLLING",
  escape:  "ESCAPING",
  defend:  "DEFENDING",
};

const POS_INFO = {
  STDN: { val: 0,   tier: "neutral",  name: "Standing",      short: "Neutral standing" },
  OGRD: { val: 0.5, tier: "neutral",  name: "Open Guard",    short: "Open guard — B has leg contact" },
  CGRD: { val: 2,   tier: "guard",    name: "Closed Guard",  short: "Closed guard — A controls with legs" },
  HGRD: { val: 0.5, tier: "neutral",  name: "Half Guard",    short: "Half guard — partial leg entanglement" },
  TRTL: { val: -1,  tier: "bad",      name: "Turtle",        short: "Turtle — vulnerable, must recover" },
  SCTR: { val: 2.5, tier: "dominant", name: "Side Control",  short: "Side control — A pins from the side" },
  MNT:  { val: 4,   tier: "dominant", name: "Mount",         short: "Mount — A sits on top, dominant" },
  BCTR: { val: 5,   tier: "dominant", name: "Back Control",  short: "Back control — A has the back, most dominant" },
};

const GRAPH_NODES = {
  STDN: { x: 280, y: 24  },
  OGRD: { x: 100, y: 90  },
  CGRD: { x: 280, y: 90  },
  HGRD: { x: 460, y: 90  },
  TRTL: { x: 60,  y: 180 },
  SCTR: { x: 280, y: 180 },
  MNT:  { x: 200, y: 224 },
  BCTR: { x: 460, y: 210 },
};

const GRAPH_EDGES = [
  { from: "STDN", to: "SCTR" }, { from: "STDN", to: "CGRD" },
  { from: "CGRD", to: "MNT" },  { from: "SCTR", to: "MNT" },
  { from: "MNT",  to: "CGRD", esc: true }, { from: "MNT",  to: "OGRD", esc: true },
  { from: "SCTR", to: "HGRD", esc: true }, { from: "BCTR", to: "TRTL", esc: true },
  { from: "TRTL", to: "STDN" }, { from: "TRTL", to: "OGRD" },
  { from: "OGRD", to: "SCTR" }, { from: "HGRD", to: "SCTR" },
];

const TIER_STYLE = {
  dominant: { fill: "#1e0e28", stroke: "#bb44dd" },
  guard:    { fill: "#0e1e14", stroke: "#4caf50" },
  neutral:  { fill: "#14141e", stroke: "#607888" },
  bad:      { fill: "#1e0e0e", stroke: "#d04040" },
};

// ═══════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════

let DATA = null;
let gameIdx = 0;
let turnIdx = 0;

function game() { return DATA?.games[gameIdx]; }
function turn() { return game()?.turns[turnIdx]; }
function prevTurn() { return turnIdx > 0 ? game()?.turns[turnIdx - 1] : null; }

function morInfo(id) { return MOR_INFO[id] || MOR_INFO.PASS; }
function posInfo(id) { return POS_INFO[id] || POS_INFO.STDN; }

// ═══════════════════════════════════════════════════════════════════
// NARRATIVE GENERATION
// ═══════════════════════════════════════════════════════════════════

function buildNarrative(t, prev) {
  const ma = morInfo(t.mor_a);
  const mb = morInfo(t.mor_b);
  const posChanged = t.pos_before !== t.pos_after;
  const lines = [];

  // Who did what
  if (t.mor_a !== "PASS" && t.mor_b !== "PASS") {
    lines.push(`<span style="color:var(--a-color)">A ${ma.verb}</span> while <span style="color:var(--b-color)">B ${mb.verb}</span>.`);
  } else if (t.mor_a !== "PASS") {
    lines.push(`<span style="color:var(--a-color)">A ${ma.verb}</span>. B is passive.`);
  } else if (t.mor_b !== "PASS") {
    lines.push(`<span style="color:var(--b-color)">B ${mb.verb}</span>. A is passive.`);
  } else {
    lines.push("Both players are inactive. No pressure from either side.");
  }

  // Contest description
  if (t.mor_a !== "PASS" && t.mor_b !== "PASS") {
    const aEsc = ma.intent === "escape";
    const bEsc = mb.intent === "escape";
    const aSub = ma.intent === "submit";
    const bSub = mb.intent === "submit";
    const aCtrl = ma.intent === "control";
    const bCtrl = mb.intent === "control";

    if (bEsc && !posChanged) {
      lines.push(`B's escape attempt is <strong>denied</strong> — A's ${aCtrl ? "control" : "pressure"} holds.`);
    } else if (bEsc && posChanged) {
      lines.push(`B <strong>breaks free</strong>. ${ma.intent === "submit" ? "A's submission attempt left an opening." : "A couldn't maintain position."}`);
    } else if (aEsc && posChanged) {
      lines.push(`A <strong>escapes</strong> successfully.`);
    } else if (aSub && bSub) {
      lines.push("Both attempt submissions — a rare mutual threat.");
    }
  }

  // Transition
  if (posChanged) {
    const pBefore = posInfo(t.pos_before);
    const pAfter = posInfo(t.pos_after);
    const valDelta = t.val - (prev ? prev.val : 0);
    if (valDelta > 0) {
      lines.push(`Position advances: ${pBefore.name} → <strong>${pAfter.name}</strong>. A improves by ${valDelta.toFixed(1)} points.`);
    } else if (valDelta < 0) {
      lines.push(`Position retreats: ${pBefore.name} → <strong>${pAfter.name}</strong>. A loses ${Math.abs(valDelta).toFixed(1)} points.`);
    } else {
      lines.push(`Position changes: ${pBefore.name} → <strong>${pAfter.name}</strong>.`);
    }
  }

  // Sub_threat
  if (prev) {
    if (t.sub_threat > prev.sub_threat) {
      lines.push(`Submission pressure builds: <strong>${t.sub_threat}/3</strong>.`);
    } else if (t.sub_threat < prev.sub_threat && posChanged) {
      lines.push("Submission pressure resets — position changed.");
    } else if (t.sub_threat < prev.sub_threat && !posChanged) {
      lines.push(`Submission pressure fades (${prev.sub_threat} → ${t.sub_threat}). A stopped attacking.`);
    }
  }
  if (t.sub_threat >= 3) {
    lines.push('<strong style="color:var(--lose)">SUBMISSION! The accumulated pressure forces a tap.</strong>');
  }

  // Initiative shift
  if (prev && t.initiative !== prev.initiative) {
    lines.push(`<em>Initiative shifts to ${t.initiative}.</em>`);
  }

  return lines.join(" ");
}

function buildTeaching(t, prev) {
  const ma = morInfo(t.mor_a);
  const mb = morInfo(t.mor_b);
  const posChanged = t.pos_before !== t.pos_after;
  const parts = [];

  // Strategic framing
  if (ma.intent === "submit" && mb.intent === "escape") {
    if (posChanged) parts.push("A went for a submission but B found the escape — the risk of attacking.");
    else parts.push("A attacks while B tries to escape, but control holds — B must find another way out.");
  } else if (ma.intent === "control" && mb.intent === "escape") {
    parts.push(posChanged
      ? "A focused on control but B still escaped — sometimes defense isn't enough."
      : "A chose safety over submission, keeping B trapped. Smart positional play.");
  } else if (ma.intent === "advance" && t.mor_b === "PASS") {
    parts.push(posChanged
      ? "A advances unopposed. B's passivity costs position."
      : "A tried to advance but the position held.");
  } else if (ma.intent === "submit" && t.mor_b === "PASS") {
    parts.push("A attacks a passive opponent. Submission pressure accumulates.");
  } else if (t.mor_a === "PASS" && mb.intent === "escape") {
    parts.push(posChanged
      ? "A paused, B seized the moment and escaped."
      : "B tries to escape but A's position is structurally sound even without active control.");
  } else if (t.mor_a === "PASS" && t.mor_b === "PASS") {
    if (prev && prev.sub_threat > 0 && t.sub_threat < prev.sub_threat) {
      parts.push("Both stall. Submission pressure decays — momentum lost.");
    } else {
      parts.push("Stalemate. Neither player commits.");
    }
  }

  // Val-based summary
  if (posChanged) {
    const dv = t.val - (prev ? prev.val : 0);
    if (dv >= 3) parts.push("Massive positional swing.");
    else if (dv <= -3) parts.push("Dramatic reversal — B turns the tables.");
  }

  return parts.join(" ") || `A ${ma.verb}, B ${mb.verb}.`;
}

function buildOutcome(t, prev) {
  const posChanged = t.pos_before !== t.pos_after;
  if (t.sub_threat >= 3) return { text: "SUBMISSION", cls: "outcome-submit" };
  if (posChanged) {
    const dv = t.val - (prev ? prev.val : 0);
    if (dv > 0) return { text: `ADVANCE  ${t.pos_before} → ${t.pos_after}  (+${dv.toFixed(1)})`, cls: "outcome-advance" };
    if (dv < 0) return { text: `ESCAPE  ${t.pos_before} → ${t.pos_after}  (${dv.toFixed(1)})`, cls: "outcome-escape" };
    return { text: `TRANSITION  ${t.pos_before} → ${t.pos_after}`, cls: "outcome-hold" };
  }
  if (t.sub_threat > 0 && prev && t.sub_threat > prev.sub_threat) {
    return { text: `PRESSURE  sub ${t.sub_threat}/3`, cls: "outcome-submit" };
  }
  return { text: "POSITION HELD", cls: "outcome-hold" };
}

// ═══════════════════════════════════════════════════════════════════
// RENDERING
// ═══════════════════════════════════════════════════════════════════

function posBadgeClass(pos) {
  const tier = posInfo(pos).tier;
  return "pos-badge pos-" + tier;
}

function renderDuality() {
  const t = turn();
  if (!t) return;
  const prev = prevTurn();
  const ma = morInfo(t.mor_a);
  const mb = morInfo(t.mor_b);

  // Player A
  document.getElementById("pa-mor").textContent = ma.name;
  document.getElementById("pa-mor-desc").textContent = ma.desc;
  const paIntent = document.getElementById("pa-intent");
  paIntent.textContent = INTENT_LABELS[ma.intent] || "";
  paIntent.className = "player-intent intent-" + ma.intent;
  document.getElementById("pa-val").textContent = t.val;
  document.getElementById("pa-sub").textContent = t.sub_threat;
  document.getElementById("pa-sub").style.color = t.sub_threat >= 2 ? "var(--lose)" : "";

  // Player A role
  const aOff = ["SCTR","MNT","BCTR","CGRD"].includes(t.pos_after);
  document.getElementById("pa-role").textContent = aOff ? (ma.intent === "submit" ? "ATTACKER" : "TOP PLAYER") : "PLAYER A";

  // Player B
  document.getElementById("pb-mor").textContent = mb.name;
  document.getElementById("pb-mor-desc").textContent = mb.desc;
  const pbIntent = document.getElementById("pb-intent");
  pbIntent.textContent = INTENT_LABELS[mb.intent] || "";
  pbIntent.className = "player-intent intent-" + mb.intent;
  document.getElementById("pb-val").textContent = (-t.val).toFixed(1);

  const bDef = aOff && t.mor_b !== "PASS";
  document.getElementById("pb-role").textContent = bDef ? (mb.intent === "escape" ? "ESCAPING" : "BOTTOM PLAYER") : "PLAYER B";

  // Advantage bar: val range roughly -1 to 5, map to 0-100%
  const pct = Math.max(0, Math.min(100, ((t.val + 1) / 6) * 100));
  const fill = document.getElementById("adv-fill");
  fill.style.left = "0";
  fill.style.width = pct + "%";
  fill.style.background = t.val > 0 ? "var(--a-color)" : t.val < 0 ? "var(--b-color)" : "var(--neutral)";
  fill.style.opacity = "0.3";
  document.getElementById("adv-marker").style.left = (pct - 1.5) + "%";

  // Momentum
  const momEl = document.getElementById("mom-val");
  const mom = t.momentum;
  momEl.textContent = (mom > 0 ? "+" : "") + mom;
  momEl.className = "mom-val " + (mom > 0 ? "mom-pos" : mom < 0 ? "mom-neg" : "mom-zero");

  // Initiative
  const initEl = document.getElementById("initiative-badge");
  initEl.textContent = "INITIATIVE: " + t.initiative;
  initEl.className = "initiative-badge init-" + t.initiative.toLowerCase();
}

function renderContest() {
  const t = turn();
  if (!t) return;
  const prev = prevTurn();
  const posChanged = t.pos_before !== t.pos_after;

  // Position badges
  const pbefore = document.getElementById("pos-before");
  pbefore.textContent = t.pos_before;
  pbefore.className = posBadgeClass(t.pos_before);

  const pafter = document.getElementById("pos-after");
  pafter.textContent = t.pos_after;
  pafter.className = posBadgeClass(t.pos_after);

  const arrow = document.getElementById("transition-arrow");
  arrow.textContent = posChanged ? "→" : "—";
  arrow.className = "arrow" + (posChanged ? " changed" : "");

  // Narrative
  document.getElementById("contest-narrative").innerHTML = buildNarrative(t, prev);

  // Outcome
  const out = buildOutcome(t, prev);
  const outEl = document.getElementById("contest-outcome");
  outEl.textContent = out.text;
  outEl.className = "contest-outcome " + out.cls;
}

function renderPressure() {
  const t = turn();
  if (!t) return;
  document.querySelectorAll(".pressure-seg").forEach(seg => {
    const lvl = +seg.dataset.level;
    seg.classList.toggle("lit", lvl <= t.sub_threat);
  });
}

function renderTeachingPanel() {
  const t = turn();
  if (!t) return;
  document.getElementById("teach-text").textContent = buildTeaching(t, prevTurn());
}

function renderGraph() {
  const svg = document.getElementById("graph-svg");
  svg.innerHTML = "";
  const g = game();
  if (!g) return;

  const visited = new Set();
  const travEdges = new Set();
  visited.add(g.turns[0]?.pos_before);
  for (let i = 0; i <= turnIdx && i < g.turns.length; i++) {
    visited.add(g.turns[i].pos_after);
    if (g.turns[i].pos_before !== g.turns[i].pos_after)
      travEdges.add(g.turns[i].pos_before + "-" + g.turns[i].pos_after);
  }
  const curPos = g.turns[Math.min(turnIdx, g.turns.length - 1)]?.pos_after;

  // Edges
  for (const e of GRAPH_EDGES) {
    const f = GRAPH_NODES[e.from], t = GRAPH_NODES[e.to];
    const key = e.from + "-" + e.to;
    const trav = travEdges.has(key);
    const dx = t.x - f.x, dy = t.y - f.y;
    const len = Math.hypot(dx, dy);
    const nx = dx / len, ny = dy / len;
    const r = 17;
    const ox = e.esc ? ny * 10 : 0, oy = e.esc ? -nx * 10 : 0;
    const x1 = f.x + nx * r, y1 = f.y + ny * r;
    const x2 = t.x - nx * r, y2 = t.y - ny * r;
    const mx = (x1 + x2) / 2 + ox, my = (y1 + y2) / 2 + oy;

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", `M${x1},${y1} Q${mx},${my} ${x2},${y2}`);
    path.setAttribute("class", "g-edge" + (trav ? " traversed" : "") + (e.esc ? " escape-edge" : ""));
    svg.appendChild(path);

    // arrowhead
    const at = 0.82;
    const px = (1-at)*(1-at)*x1 + 2*(1-at)*at*mx + at*at*x2;
    const py = (1-at)*(1-at)*y1 + 2*(1-at)*at*my + at*at*y2;
    const tx2 = 2*(1-at)*(mx-x1) + 2*at*(x2-mx);
    const ty2 = 2*(1-at)*(my-y1) + 2*at*(y2-my);
    const tl = Math.hypot(tx2, ty2);
    const tnx = tx2/tl, tny = ty2/tl;
    const as = 5;
    const ah = document.createElementNS("http://www.w3.org/2000/svg", "path");
    ah.setAttribute("d", `M${x2},${y2} L${x2-tnx*as+tny*as*0.5},${y2-tny*as-tnx*as*0.5} M${x2},${y2} L${x2-tnx*as-tny*as*0.5},${y2-tny*as+tnx*as*0.5}`);
    ah.setAttribute("class", "g-edge" + (trav ? " traversed" : "") + (e.esc ? " escape-edge" : ""));
    ah.style.fill = "none";
    svg.appendChild(ah);
  }

  // Nodes
  for (const [id, pos] of Object.entries(GRAPH_NODES)) {
    const pi = posInfo(id);
    const st = TIER_STYLE[pi.tier];
    const isCur = id === curPos;
    const isVis = visited.has(id);

    const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    c.setAttribute("cx", pos.x); c.setAttribute("cy", pos.y); c.setAttribute("r", 16);
    c.setAttribute("fill", st.fill); c.setAttribute("stroke", st.stroke);
    c.setAttribute("class", "g-node" + (isCur ? " current" : isVis ? " visited" : ""));
    if (isCur) c.setAttribute("stroke", "var(--a-color)");
    svg.appendChild(c);

    const lab = document.createElementNS("http://www.w3.org/2000/svg", "text");
    lab.setAttribute("x", pos.x); lab.setAttribute("y", pos.y + 1);
    lab.setAttribute("class", "g-nlabel");
    lab.textContent = id;
    svg.appendChild(lab);

    const vl = document.createElementNS("http://www.w3.org/2000/svg", "text");
    vl.setAttribute("x", pos.x); vl.setAttribute("y", pos.y + 28);
    vl.setAttribute("class", "g-vlabel");
    vl.textContent = pi.val;
    svg.appendChild(vl);
  }
}

function renderTimeline() {
  const el = document.getElementById("tl-turns");
  el.innerHTML = "";
  const g = game();
  if (!g) return;

  g.turns.forEach((t, i) => {
    const prev = i > 0 ? g.turns[i - 1] : null;
    const posChanged = t.pos_before !== t.pos_after;
    const div = document.createElement("div");
    div.className = "tl-turn" + (i === turnIdx ? " active" : "");
    div.addEventListener("click", () => setTurn(i));

    const posText = posChanged
      ? `<span class="tl-pos-change">${t.pos_before}→${t.pos_after}</span>`
      : t.pos_after;
    const subText = t.sub_threat >= 3
      ? `<span class="tl-sub-warn">SUB!</span>`
      : t.sub_threat > 0 ? `sub:${t.sub_threat}` : "";

    div.innerHTML = `
      <div class="tl-num">T${t.turn}</div>
      <div class="tl-body">
        <div class="tl-mors">
          <span class="tl-mora">${morInfo(t.mor_a).name}</span>
          <span class="tl-vs">vs</span>
          <span class="tl-morb">${morInfo(t.mor_b).name}</span>
        </div>
        <div class="tl-detail">
          <span>${posText}</span>
          <span>val:${t.val}</span>
          ${subText ? `<span>${subText}</span>` : ""}
        </div>
      </div>`;
    el.appendChild(div);
  });

  // Scroll active into view
  const active = el.querySelector(".active");
  if (active) active.scrollIntoView({ block: "nearest" });
}

function renderResult() {
  const g = game();
  if (!g) return;
  const el = document.getElementById("tl-result");
  const cls = g.condition === "submission" ? "tl-result-sub"
    : g.condition === "draw" ? "tl-result-draw" : "tl-result-pts";
  el.className = "tl-result " + cls;
  el.textContent = g.condition === "submission"
    ? `${g.winner} SUB T${g.submission_turn || g.num_turns}`
    : g.condition === "draw" ? "DRAW"
    : `${g.winner} PTS ${g.final_val_a}`;
}

function renderDebug() {
  const t = turn();
  if (!t) return;
  const g = game();
  const lines = [
    `TURN_FPT #${t.turn}`,
    `  mor_a:       ${t.mor_a}`,
    `  mor_b:       ${t.mor_b}`,
    `  pos_before:  ${t.pos_before}`,
    `  pos_after:   ${t.pos_after}`,
    `  val_a:       ${t.val}`,
    `  val_b:       ${(-t.val).toFixed(1)}`,
    `  sub_threat:  ${t.sub_threat}`,
    `  momentum:    ${t.momentum}`,
    `  initiative:  ${t.initiative}`,
    "",
    `GAME: ${g.label}`,
    `  winner:      ${g.winner}`,
    `  condition:   ${g.condition}`,
    `  num_turns:   ${g.num_turns}`,
    `  final_val_a: ${g.final_val_a}`,
    `  final_val_b: ${g.final_val_b}`,
  ];
  document.getElementById("debug-content").textContent = lines.join("\n");
}

function renderGameBar() {
  const bar = document.getElementById("game-bar");
  bar.innerHTML = "";
  if (!DATA) return;
  DATA.games.forEach((g, i) => {
    const btn = document.createElement("button");
    btn.className = "gbar-item" + (i === gameIdx ? " active" : "");

    const id = g.label.split(" ")[0];
    const tagCls = g.condition === "submission" ? "gbar-tag-sub"
      : g.condition === "draw" ? "gbar-tag-draw" : "gbar-tag-pts";
    const tagText = g.condition === "submission" ? "SUB"
      : g.condition === "draw" ? "DRAW" : "PTS";

    btn.innerHTML = `${id}<span class="gbar-tag ${tagCls}">${tagText}</span>`;
    btn.addEventListener("click", () => selectGame(i));
    bar.appendChild(btn);
  });
}

// ═══════════════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════════════

function renderAll() {
  renderDuality();
  renderContest();
  renderPressure();
  renderTeachingPanel();
  renderGraph();
  renderTimeline();
  renderDebug();
  updateNav();
}

function updateNav() {
  const g = game();
  if (!g) return;
  const slider = document.getElementById("turn-slider");
  slider.max = g.turns.length - 1;
  slider.value = turnIdx;
  document.getElementById("turn-label").textContent = `T${turnIdx + 1} / ${g.turns.length}`;
  document.getElementById("btn-prev").disabled = turnIdx === 0;
  document.getElementById("btn-next").disabled = turnIdx >= g.turns.length - 1;
}

function setTurn(i) {
  const g = game();
  if (!g) return;
  turnIdx = Math.max(0, Math.min(i, g.turns.length - 1));
  renderAll();
}

function selectGame(i) {
  gameIdx = i;
  turnIdx = 0;
  renderGameBar();
  renderResult();
  renderAll();
}

// ═══════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════

document.getElementById("btn-prev").addEventListener("click", () => setTurn(turnIdx - 1));
document.getElementById("btn-next").addEventListener("click", () => setTurn(turnIdx + 1));
document.getElementById("turn-slider").addEventListener("input", e => setTurn(+e.target.value));
document.getElementById("debug-toggle").addEventListener("click", () => {
  document.getElementById("debug-content").classList.toggle("open");
});

document.addEventListener("keydown", e => {
  if (e.key === "ArrowLeft" || e.key === "h") setTurn(turnIdx - 1);
  else if (e.key === "ArrowRight" || e.key === "l") setTurn(turnIdx + 1);
  else if (e.key === "ArrowUp" || e.key === "k") { e.preventDefault(); selectGame(Math.max(0, gameIdx - 1)); }
  else if (e.key === "ArrowDown" || e.key === "j") { e.preventDefault(); selectGame(Math.min(DATA.games.length - 1, gameIdx + 1)); }
  else if (e.key === "Home") setTurn(0);
  else if (e.key === "End") setTurn(game().turns.length - 1);
});

(async function init() {
  const resp = await fetch("../../data/matboard/playtests_p1.json");
  DATA = await resp.json();
  renderGameBar();
  renderResult();
  renderAll();
})();
