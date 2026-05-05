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
  hide(document.getElementById('lowConfWarning'));
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
      showError(
        detail.message || `Server error (${res.status})`,
        detail.hint || ''
      );
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

  // low confidence warning
  const warn = document.getElementById('lowConfWarning');
  if (data.confidence < 0.5) show(warn); else hide(warn);

  // radical hero
  const radName = document.getElementById('radName');
  radName.textContent = data.radical;

  const confEl = document.getElementById('radConf');
  confEl.textContent = (data.confidence * 100).toFixed(1) + '%';
  confEl.className = 'conf-value';
  if (data.confidence === 0) confEl.classList.add('none');
  else if (data.confidence < 0.3) confEl.classList.add('low');

  document.getElementById('radPov').textContent = 'POV: ' + data.pov;
  document.getElementById('radExplanation').textContent = data.explanation;

  // all matches
  const bar = document.getElementById('matchesBar');
  bar.innerHTML = '';
  (data.all_matches || []).forEach(m => {
    const chip = document.createElement('span');
    chip.className = 'match-chip';
    chip.innerHTML = `<span class="chip-name">${m.radical}</span><span class="chip-conf">${(m.confidence * 100).toFixed(1)}%</span>`;
    bar.appendChild(chip);
  });

  // connections
  const conList = document.getElementById('conList');
  conList.innerHTML = '';
  (data.contacts || []).forEach(c => {
    const row = document.createElement('div');
    row.className = 'row';
    row.innerHTML = `<span class="label">${c.attacker} &rarr; ${c.axis}</span><span class="value">${c.helicity === '0' ? 'closure' : c.helicity} ${(c.confidence * 100).toFixed(0)}%</span>`;
    conList.appendChild(row);
  });
  if (!data.contacts || data.contacts.length === 0) {
    conList.innerHTML = '<span class="label">No connections detected</span>';
  }

  // frame constraints
  const frmList = document.getElementById('frmList');
  frmList.innerHTML = '';
  (data.frame_constraints || []).forEach(f => {
    const row = document.createElement('div');
    row.className = 'row';
    const part = f.part ? ' ' + f.part : '';
    row.innerHTML = `<span class="label">${f.type}${part}</span><span class="value">${(f.confidence * 100).toFixed(0)}%</span>`;
    frmList.appendChild(row);
  });

  // sexpr
  document.getElementById('sexprCode').textContent = data.sexpr;

  // copy button
  document.getElementById('copyBtn').onclick = () => {
    navigator.clipboard.writeText(data.sexpr).then(() => {
      const btn = document.getElementById('copyBtn');
      btn.textContent = 'Copied';
      setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
    });
  };

  show(results);
}
