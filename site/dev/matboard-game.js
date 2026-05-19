"use strict";

const POSITIONS = {
  STDN: { x: 300, y: 30,  val: 0,   label: "STDN", tier: "neutral" },
  OGRD: { x: 120, y: 120, val: 0.5, label: "OGRD", tier: "neutral" },
  CGRD: { x: 300, y: 120, val: 2,   label: "CGRD", tier: "guard" },
  HGRD: { x: 480, y: 120, val: 0.5, label: "HGRD", tier: "neutral" },
  TRTL: { x: 80,  y: 230, val: -1,  label: "TRTL", tier: "bad" },
  SCTR: { x: 300, y: 230, val: 2.5, label: "SCTR", tier: "dominant" },
  MNT:  { x: 300, y: 330, val: 4,   label: "MNT",  tier: "dominant" },
  BCTR: { x: 520, y: 330, val: 5,   label: "BCTR", tier: "dominant" },
};

const EDGES = [
  { from: "STDN", to: "SCTR", label: "takedown" },
  { from: "STDN", to: "CGRD", label: "pull_guard" },
  { from: "CGRD", to: "MNT",  label: "hip_bump" },
  { from: "SCTR", to: "MNT",  label: "sctr_mount" },
  { from: "MNT",  to: "CGRD", label: "mnt_bridge", type: "escape" },
  { from: "MNT",  to: "OGRD", label: "mnt_elbow_knee", type: "escape" },
  { from: "SCTR", to: "HGRD", label: "sctr_shrimp", type: "escape" },
  { from: "BCTR", to: "TRTL", label: "bctr_turn_in", type: "escape" },
  { from: "TRTL", to: "STDN", label: "trtl_standup" },
  { from: "TRTL", to: "OGRD", label: "trtl_sit" },
  { from: "OGRD", to: "SCTR", label: "ogrd_sweep" },
  { from: "HGRD", to: "SCTR", label: "hgrd_sweep" },
];

const TIER_COLORS = {
  dominant: { fill: "#2a1530", stroke: "#e040fb" },
  guard:    { fill: "#1a2a20", stroke: "#4caf50" },
  neutral:  { fill: "#1a1a24", stroke: "#78909c" },
  bad:      { fill: "#2a1a1a", stroke: "#ef5350" },
};

let DATA = null;
let currentGameIdx = 0;
let currentTurn = 0;

function generateExplanation(turn, prevTurn, game) {
  const parts = [];
  const t = turn;
  const morA = t.mor_a === "PASS" ? "passes" : `plays ${t.mor_a}`;
  const morB = t.mor_b === "PASS" ? "passes" : `plays ${t.mor_b}`;
  parts.push(`A ${morA}, B ${morB}.`);

  if (t.pos_before !== t.pos_after) {
    parts.push(`Position changes: ${t.pos_before} → ${t.pos_after}.`);
    const dv = prevTurn ? (t.val - prevTurn.val) : t.val;
    if (dv > 0) parts.push(`VAL rises by ${dv.toFixed(1)} (A improves).`);
    else if (dv < 0) parts.push(`VAL drops by ${Math.abs(dv).toFixed(1)} (B recovers).`);
  }

  if (t.sub_threat > 0 && prevTurn && t.sub_threat > prevTurn.sub_threat) {
    parts.push(`Sub_threat increments to ${t.sub_threat} — submission MOR from offense.`);
  } else if (prevTurn && t.sub_threat < prevTurn.sub_threat && t.pos_before === t.pos_after) {
    parts.push(`Sub_threat decays ${prevTurn.sub_threat} → ${t.sub_threat} — no submission attempted.`);
  } else if (prevTurn && t.sub_threat < prevTurn.sub_threat && t.pos_before !== t.pos_after) {
    parts.push(`Sub_threat resets to ${t.sub_threat} — position changed.`);
  }

  if (t.sub_threat >= 3) {
    parts.push("SUBMISSION ACHIEVED.");
  }

  if (prevTurn && t.initiative !== prevTurn.initiative) {
    parts.push(`Initiative shifts to ${t.initiative}.`);
  }

  const isMorAEscape = ["mnt_bridge", "mnt_elbow_knee", "sctr_shrimp", "bctr_turn_in"].includes(t.mor_a);
  const isMorBEscape = ["mnt_bridge", "mnt_elbow_knee", "sctr_shrimp", "bctr_turn_in"].includes(t.mor_b);
  if (isMorBEscape && t.pos_before === t.pos_after) {
    parts.push("B's escape fails — contested by A's control.");
  } else if (isMorBEscape && t.pos_before !== t.pos_after) {
    parts.push("B escapes successfully.");
  }
  if (isMorAEscape && t.pos_before !== t.pos_after) {
    parts.push("A escapes successfully.");
  }

  return parts.join(" ");
}

function renderGraph(game, turnIdx) {
  const svg = document.getElementById("graph-svg");
  svg.innerHTML = "";

  const visited = new Set();
  const traversedEdges = new Set();
  let currentPos = null;

  if (game && game.turns.length > 0) {
    visited.add(game.turns[0].pos_before);
    for (let i = 0; i <= turnIdx && i < game.turns.length; i++) {
      const t = game.turns[i];
      visited.add(t.pos_after);
      if (t.pos_before !== t.pos_after) {
        traversedEdges.add(`${t.pos_before}-${t.pos_after}`);
      }
    }
    currentPos = game.turns[Math.min(turnIdx, game.turns.length - 1)].pos_after;
  }

  for (const e of EDGES) {
    const f = POSITIONS[e.from];
    const t = POSITIONS[e.to];
    const key = `${e.from}-${e.to}`;
    const cls = traversedEdges.has(key) ? "edge-line traversed" : "edge-line";
    const dx = t.x - f.x;
    const dy = t.y - f.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    const nx = dx / len;
    const ny = dy / len;
    const x1 = f.x + nx * 22;
    const y1 = f.y + ny * 22;
    const x2 = t.x - nx * 22;
    const y2 = t.y - ny * 22;

    const isEscape = e.type === "escape";
    const ox = isEscape ? ny * 12 : 0;
    const oy = isEscape ? -nx * 12 : 0;

    const mx = (x1 + x2) / 2 + ox;
    const my = (y1 + y2) / 2 + oy;
    const path = `M${x1},${y1} Q${mx},${my} ${x2},${y2}`;

    const pathEl = document.createElementNS("http://www.w3.org/2000/svg", "path");
    pathEl.setAttribute("d", path);
    pathEl.setAttribute("class", cls);
    if (isEscape) pathEl.style.strokeDasharray = "6,3";

    const arrowSize = 6;
    const at = 0.85;
    const px = (1 - at) * (1 - at) * x1 + 2 * (1 - at) * at * mx + at * at * x2;
    const py = (1 - at) * (1 - at) * y1 + 2 * (1 - at) * at * my + at * at * y2;
    const tangentX = 2 * (1 - at) * (mx - x1) + 2 * at * (x2 - mx);
    const tangentY = 2 * (1 - at) * (my - y1) + 2 * at * (y2 - my);
    const tlen = Math.sqrt(tangentX * tangentX + tangentY * tangentY);
    const tnx = tangentX / tlen;
    const tny = tangentY / tlen;

    const arrowPath = `M${x2},${y2} L${x2 - tnx * arrowSize + tny * arrowSize * 0.5},${y2 - tny * arrowSize - tnx * arrowSize * 0.5} M${x2},${y2} L${x2 - tnx * arrowSize - tny * arrowSize * 0.5},${y2 - tny * arrowSize + tnx * arrowSize * 0.5}`;
    const arrowEl = document.createElementNS("http://www.w3.org/2000/svg", "path");
    arrowEl.setAttribute("d", arrowPath);
    arrowEl.setAttribute("class", cls);
    arrowEl.style.fill = "none";

    svg.appendChild(pathEl);
    svg.appendChild(arrowEl);
  }

  for (const [id, pos] of Object.entries(POSITIONS)) {
    const tier = TIER_COLORS[pos.tier];
    const isCurrent = id === currentPos;
    const isVisited = visited.has(id);

    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", pos.x);
    circle.setAttribute("cy", pos.y);
    circle.setAttribute("r", 20);
    circle.setAttribute("fill", tier.fill);
    circle.setAttribute("stroke", tier.stroke);
    let cls = "node-circle";
    if (isCurrent) cls += " current";
    else if (isVisited) cls += " visited";
    if (pos.tier === "dominant") cls += " dominant";
    circle.setAttribute("class", cls);
    svg.appendChild(circle);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", pos.x);
    label.setAttribute("y", pos.y + 1);
    label.setAttribute("class", "node-label");
    label.setAttribute("dominant-baseline", "central");
    label.textContent = pos.label;
    svg.appendChild(label);

    const valLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
    valLabel.setAttribute("x", pos.x);
    valLabel.setAttribute("y", pos.y + 32);
    valLabel.setAttribute("class", "node-val");
    valLabel.textContent = `val=${pos.val}`;
    svg.appendChild(valLabel);
  }
}

function renderGameList() {
  const list = document.getElementById("game-list");
  list.innerHTML = "";
  if (!DATA) return;
  DATA.games.forEach((g, i) => {
    const div = document.createElement("div");
    div.className = "game-item" + (i === currentGameIdx ? " active" : "");
    const label = document.createElement("span");
    label.textContent = g.label;
    div.appendChild(label);

    const tag = document.createElement("span");
    tag.className = "tag ";
    if (g.condition === "submission") { tag.className += "tag-sub"; tag.textContent = "SUB"; }
    else if (g.condition === "draw") { tag.className += "tag-draw"; tag.textContent = "DRAW"; }
    else { tag.className += "tag-pts"; tag.textContent = "PTS"; }
    div.appendChild(tag);

    div.addEventListener("click", () => { selectGame(i); });
    list.appendChild(div);
  });
}

function renderReplay(game) {
  const tbody = document.getElementById("turn-body");
  tbody.innerHTML = "";
  game.turns.forEach((t, i) => {
    const tr = document.createElement("tr");
    if (i === currentTurn) tr.className = "current-turn";
    tr.addEventListener("click", () => { setTurn(i); });

    const posChanged = t.pos_before !== t.pos_after;
    const posText = posChanged
      ? `${t.pos_before} → ${t.pos_after}`
      : t.pos_after;
    const subText = t.sub_threat >= 3 ? `${t.sub_threat}!` : String(t.sub_threat);

    tr.innerHTML = `
      <td>${t.turn}</td>
      <td class="mor-a">${t.mor_a}</td>
      <td class="mor-b">${t.mor_b}</td>
      <td class="${posChanged ? "pos-change" : ""}">${posText}</td>
      <td>${t.val}</td>
      <td class="${t.sub_threat >= 3 ? "sub-highlight" : ""}">${subText}</td>
      <td>${t.momentum}</td>
      <td>${t.initiative}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderTeaching(game) {
  const el = document.getElementById("teaching-content");
  el.innerHTML = "";
  game.turns.forEach((t, i) => {
    const prev = i > 0 ? game.turns[i - 1] : null;
    const explanation = generateExplanation(t, prev, game);
    const div = document.createElement("div");
    div.className = "teaching-row";
    div.innerHTML = `<span class="turn-num">T${t.turn}</span> <span class="explanation">${explanation}</span>`;
    el.appendChild(div);
  });
}

function renderDebug(game) {
  const el = document.getElementById("debug-content");
  const turn = game.turns[currentTurn];
  if (!turn) { el.textContent = "No turn data."; return; }
  const lines = [
    `TURN_FPT Turn ${turn.turn}`,
    `  mor_a: ${turn.mor_a}`,
    `  mor_b: ${turn.mor_b}`,
    `  pos_before: ${turn.pos_before}`,
    `  pos_after: ${turn.pos_after}`,
    `  val_a: ${turn.val}`,
    `  val_b: ${(-turn.val).toFixed(1)}`,
    `  sub_threat: ${turn.sub_threat}`,
    `  momentum: ${turn.momentum}`,
    `  initiative: ${turn.initiative}`,
    ``,
    `GAME: ${game.label}`,
    `  winner: ${game.winner}`,
    `  condition: ${game.condition}`,
    `  final_val_a: ${game.final_val_a}`,
    `  final_val_b: ${game.final_val_b}`,
    `  num_turns: ${game.num_turns}`,
  ];
  if (game.submission_turn) lines.push(`  submission_turn: ${game.submission_turn}`);
  el.textContent = lines.join("\n");
}

function renderResult(game) {
  const el = document.getElementById("result-banner");
  const winText = game.winner === "DRAW" ? "DRAW" : `${game.winner} wins`;
  const condText = game.condition;
  const valText = `val A=${game.final_val_a} B=${game.final_val_b}`;
  const turnText = `${game.num_turns} turns`;
  el.innerHTML = `
    <span class="winner">${winText}</span>
    <span class="condition">${condText}</span>
    <span>${valText}</span>
    <span>${turnText}</span>
  `;
}

function setTurn(idx) {
  const game = DATA.games[currentGameIdx];
  currentTurn = Math.max(0, Math.min(idx, game.turns.length - 1));
  document.getElementById("turn-slider").value = currentTurn;
  document.getElementById("turn-label").textContent = `Turn ${currentTurn + 1}/${game.turns.length}`;
  document.getElementById("btn-prev").disabled = currentTurn === 0;
  document.getElementById("btn-next").disabled = currentTurn >= game.turns.length - 1;

  renderGraph(game, currentTurn);
  renderReplay(game);
  renderDebug(game);
}

function selectGame(idx) {
  currentGameIdx = idx;
  currentTurn = 0;
  const game = DATA.games[idx];
  const slider = document.getElementById("turn-slider");
  slider.max = game.turns.length - 1;
  slider.value = 0;
  renderGameList();
  renderResult(game);
  renderReplay(game);
  renderTeaching(game);
  renderDebug(game);
  setTurn(0);
}

function initControls() {
  document.getElementById("btn-prev").addEventListener("click", () => setTurn(currentTurn - 1));
  document.getElementById("btn-next").addEventListener("click", () => setTurn(currentTurn + 1));
  document.getElementById("turn-slider").addEventListener("input", (e) => setTurn(+e.target.value));

  document.querySelectorAll(".tab-bar button").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-bar button").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    });
  });

  document.getElementById("debug-toggle").addEventListener("click", () => {
    document.getElementById("debug-content").classList.toggle("open");
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") setTurn(currentTurn - 1);
    else if (e.key === "ArrowRight") setTurn(currentTurn + 1);
    else if (e.key === "ArrowUp") { e.preventDefault(); selectGame(Math.max(0, currentGameIdx - 1)); }
    else if (e.key === "ArrowDown") { e.preventDefault(); selectGame(Math.min(DATA.games.length - 1, currentGameIdx + 1)); }
  });
}

async function loadData() {
  const resp = await fetch("../../data/matboard/playtests_p1.json");
  DATA = await resp.json();
  renderGameList();
  selectGame(0);
}

initControls();
loadData();
