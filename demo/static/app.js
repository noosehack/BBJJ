const dropZone    = document.getElementById('dropZone');
const fileInput   = document.getElementById('fileInput');
const previewRow  = document.getElementById('previewRow');
const previewOrig = document.getElementById('previewOriginal');
const previewOver = document.getElementById('previewOverlay');
const loading     = document.getElementById('loading');
const errorBlock  = document.getElementById('errorBlock');
const results     = document.getElementById('results');

// ── drag & drop ────────────────────────────────

['dragenter', 'dragover'].forEach(ev =>
  dropZone.addEventListener(ev, e => { e.preventDefault(); dropZone.classList.add('drag-over'); })
);
['dragleave', 'drop'].forEach(ev =>
  dropZone.addEventListener(ev, e => { e.preventDefault(); dropZone.classList.remove('drag-over'); })
);

dropZone.addEventListener('drop', e => {
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) handleFile(file);
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

document.getElementById('resetBtn').addEventListener('click', reset);

// ── state management ───────────────────────────

function show(el)  { el.classList.add('visible'); }
function hide(el)  { el.classList.remove('visible'); }

function reset() {
  hide(previewRow);
  hide(loading);
  hide(errorBlock);
  hide(results);
  dropZone.style.display = '';
  fileInput.value = '';
}

// ── main flow ──────────────────────────────────

async function handleFile(file) {
  reset();
  dropZone.style.display = 'none';
  show(loading);

  previewOrig.src = URL.createObjectURL(file);

  const form = new FormData();
  form.append('image', file);

  try {
    const res = await fetch('/api/infer', { method: 'POST', body: form });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: { message: res.statusText } }));
      const detail = err.detail || {};
      showError(detail.message || `Server error (${res.status})`, detail.hint || '');
      return;
    }

    const data = await res.json();
    renderResults(data);

  } catch (e) {
    showError('Could not reach the server.', 'Make sure the API is running.');
  }
}

function showError(message, hint) {
  hide(loading);
  document.getElementById('errorMessage').textContent = message;
  document.getElementById('errorHint').textContent = hint || '';
  show(errorBlock);
  dropZone.style.display = '';
}

// ── render results ─────────────────────────────

function renderResults(data) {
  hide(loading);

  // overlay
  previewOver.src = data.overlay_url;
  show(previewRow);

  // Pose quality status bar
  const qualBar = document.getElementById('poseQualityBar');
  const q = data.pose_quality || 'unknown';
  const qd = data.pose_detail || {};
  const qLabels = {
    good: 'Pose quality: Good',
    uncertain: 'Pose quality: Uncertain — classification may be unreliable',
    poor: 'Pose quality: Poor — keypoints likely incorrect',
  };
  const qDetail = qd.conf_a != null
    ? ` (A: ${(qd.conf_a * 100).toFixed(0)}% conf/${qd.high_conf_kps_a} kps, B: ${(qd.conf_b * 100).toFixed(0)}% conf/${qd.high_conf_kps_b} kps)`
    : '';
  qualBar.textContent = (qLabels[q] || 'Pose quality: unknown') + qDetail;
  qualBar.className = 'pose-quality-bar quality-' + q;

  // Classifier source
  const sourceMap = {
    'learned_geometry': 'Geometry Classifier (203 features)',
    'geo_ordered_cr_cw': 'Geometry + Ordered CR Classifier (635 features)',
    'invariant_geo_cr': 'Invariant Classifier (424 features, no body-frame projections)',
  };
  const source = sourceMap[data.classifier_source] || data.classifier_source;
  document.getElementById('verdictSource').textContent = source;

  // Verdict
  document.getElementById('verdictRadical').textContent = data.radical;
  const scoreEl = document.getElementById('verdictScore');
  scoreEl.textContent = (data.confidence * 100).toFixed(1) + '%';
  scoreEl.className = 'verdict-score';
  if (data.confidence < 0.3) scoreEl.classList.add('low');
  else if (data.confidence >= 0.7) scoreEl.classList.add('high');

  document.getElementById('verdictPov').textContent = 'POV: ' + data.pov;
  document.getElementById('verdictExplanation').textContent = data.explanation;

  // Top predictions bar (top 3 prominent, rest smaller)
  const bar = document.getElementById('topPredictions');
  bar.innerHTML = '';
  (data.top_predictions || []).slice(0, 5).forEach((p, i) => {
    const chip = document.createElement('span');
    const cls = i === 0 ? 'match-chip active' : i < 3 ? 'match-chip runner-up' : 'match-chip';
    chip.className = cls;
    chip.innerHTML = `<span class="chip-name">${p.radical}</span><span class="chip-conf">${(p.confidence * 100).toFixed(1)}%</span>`;
    bar.appendChild(chip);
  });

  // ── Orientation panel ──
  const orient = data.orientation;
  const orientEl = document.getElementById('orientationContent');
  orientEl.innerHTML = '';

  const orientRows = [
    ['Torso alignment', orientLabel(orient.torso_axis_dot), orient.orientation_label],
    ['Facing relation', facingLabel(orient.facing_dot), fmtDot(orient.facing_dot)],
    ['Shoulder axes', fmtDot(orient.sh_axis_dot), orient.sh_axis_dot > 0.5 ? 'aligned' : orient.sh_axis_dot < -0.5 ? 'opposed' : 'oblique'],
    ['Hip axes', fmtDot(orient.hp_axis_dot), orient.hp_axis_dot > 0.5 ? 'aligned' : orient.hp_axis_dot < -0.5 ? 'opposed' : 'oblique'],
    ['Vertical dominance', fmtNum(orient.vert_dominance), orient.top_label.replace('_', ' ')],
    ['Center distance', fmtNum(orient.center_dist) + ' torso-lengths', ''],
    ['Hip distance', fmtNum(orient.hip_dist) + ' torso-lengths', ''],
  ];

  orientRows.forEach(([label, value, note]) => {
    const row = document.createElement('div');
    row.className = 'row';
    row.innerHTML = `<span class="label">${label}</span><span class="value">${value} <span class="note">${note}</span></span>`;
    orientEl.appendChild(row);
  });

  // ── Conditions panel ──
  const condSub = document.getElementById('conditionsSub');
  condSub.textContent = 'Geometry checks for ' + data.radical;
  const condEl = document.getElementById('conditionsContent');
  condEl.innerHTML = '';

  if (data.conditions && data.conditions.length > 0) {
    data.conditions.forEach(c => {
      const row = document.createElement('div');
      row.className = 'row condition-row';
      const status = c.met
        ? '<span class="cond-pass">PASS</span>'
        : '<span class="cond-fail">FAIL</span>';
      row.innerHTML = `
        <div class="cond-main">
          ${status}
          <span class="cond-name">${c.name}</span>
          <span class="cond-val">${fmtNum(c.value)} ${c.threshold}</span>
        </div>
        <div class="cond-desc">${c.description}</div>`;
      condEl.appendChild(row);
    });
  } else {
    condEl.innerHTML = '<div class="row"><span class="label dim">No specific conditions defined</span></div>';
  }

  // ── Body frames panel ──
  const framesEl = document.getElementById('framesContent');
  framesEl.innerHTML = '';

  [['Athlete A (Me)', data.body_frame_a], ['Athlete B (Op)', data.body_frame_b]].forEach(([title, bf]) => {
    const section = document.createElement('div');
    section.className = 'frame-section';
    section.innerHTML = `
      <div class="frame-title">${title}</div>
      <div class="row"><span class="label">Torso angle</span><span class="value">${bf.torso_angle_deg.toFixed(1)}&deg;</span></div>
      <div class="row"><span class="label">Torso length</span><span class="value">${bf.torso_len.toFixed(0)}px</span></div>
      <div class="row"><span class="label">Shoulder width</span><span class="value">${bf.sh_width.toFixed(0)}px</span></div>
      <div class="row"><span class="label">Hip width</span><span class="value">${bf.hp_width.toFixed(0)}px</span></div>
      <div class="row"><span class="label">Facing conf</span><span class="value">${(bf.facing_conf * 100).toFixed(0)}%</span></div>
      <div class="row"><span class="label">Center</span><span class="value">(${bf.center[0].toFixed(0)}, ${bf.center[1].toFixed(0)})</span></div>
    `;
    framesEl.appendChild(section);
  });

  show(results);
}

// ── helpers ────────────────────────────────────

function fmtNum(n) { return n >= 0 ? '+' + n.toFixed(2) : n.toFixed(2); }
function fmtDot(d) { return (d * 100).toFixed(0) + '%'; }

function orientLabel(dot) {
  if (dot > 0.5) return 'same direction';
  if (dot < -0.5) return 'opposed';
  return 'perpendicular/oblique';
}

function facingLabel(dot) {
  if (dot < -0.3) return 'face-to-face';
  if (dot > 0.3) return 'same way';
  return 'angled';
}
