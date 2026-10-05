/**
 * Theme + Settings modal content. These are UI-preference panels rather than
 * run-data panels, so they live next to the theme controller.
 */
import { esc } from './dom.js';
import { theme, PATTERNS } from './theme.js';

const TONE_SWATCHES = [
  { id: 'neon-gold', label: 'Neon blue + gold', a: '#00d4ff', b: '#ffd700' },
  { id: 'electric', label: 'Electric violet', a: '#8b5cf6', b: '#22d3ee' },
  { id: 'plasma', label: 'Plasma', a: '#f97316', b: '#eab308' },
  { id: 'matrix', label: 'Matrix', a: '#22c55e', b: '#a3e635' },
  { id: 'arctic', label: 'Arctic', a: '#38bdf8', b: '#e2e8f0' },
];

const ACTIVE_SWATCH = 'neon-gold';

/**
 * Swatch application is intentionally a no-op for non-active swatches: the
 * product ships one canonical palette. The others stay visible so the design
 * system has a documented extension point.
 */
function applySwatch(id) {
  if (id !== ACTIVE_SWATCH) return false;
  const swatch = TONE_SWATCHES.find((s) => s.id === id);
  if (!swatch) return false;
  const root = document.documentElement;
  root.style.setProperty('--accent', swatch.a);
  root.style.setProperty('--accent-strong', swatch.b);
  root.style.setProperty('--gold', swatch.b);
  return true;
}

export function themePanel() {
  const s = theme.settings;
  return `
    <div class="admin-card">
      <h3>Appearance</h3>
      <div class="field-row two-up">
        <label class="field">
          <span>Mode</span>
          <select data-pref="mode">
            <option value="dark" ${s.mode === 'dark' ? 'selected' : ''}>Dark</option>
            <option value="light" ${s.mode === 'light' ? 'selected' : ''}>Light</option>
          </select>
        </label>
        <label class="field">
          <span>Density</span>
          <select data-pref="density">
            <option value="default" ${s.density === 'default' ? 'selected' : ''}>Default</option>
            <option value="compact" ${s.density === 'compact' ? 'selected' : ''}>Compact</option>
            <option value="spacious" ${s.density === 'spacious' ? 'selected' : ''}>Spacious</option>
          </select>
        </label>
      </div>
      <div class="field-row two-up" style="margin-top:8px">
        <label class="field">
          <span>Text size</span>
          <select data-pref="textSize">
            <option value="default" ${s.textSize === 'default' ? 'selected' : ''}>Default</option>
            <option value="large" ${s.textSize === 'large' ? 'selected' : ''}>Large (125%)</option>
          </select>
        </label>
        <label class="field">
          <span>Background</span>
          <select data-pref="bgPattern">
            ${PATTERNS.map((p) => `<option value="${p}" ${s.bgPattern === p ? 'selected' : ''}>${esc(p)}</option>`).join('')}
          </select>
        </label>
      </div>
    </div>

    <div class="admin-card">
      <h3>Palette</h3>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px">
        ${TONE_SWATCHES.map((sw) => `
          <button class="row-card" data-swatch="${sw.id}" style="display:flex;align-items:center;gap:9px;cursor:pointer;border-left-color:${sw.id === ACTIVE_SWATCH ? sw.a : 'var(--border)'}">
            <span style="width:26px;height:26px;border-radius:6px;flex-shrink:0;background:linear-gradient(135deg,${sw.a},${sw.b})"></span>
            <span class="grow" style="font-size:11.5px">${esc(sw.label)}</span>
            ${sw.id === ACTIVE_SWATCH ? '<span class="tag tag-allow">active</span>' : ''}
          </button>`).join('')}
      </div>
    </div>

    <div class="admin-card">
      <h3>Glow intensity</h3>
      <label class="field">
        <span>Neon blue — <b id="glow-val">${s.glow}%</b></span>
        <input type="range" min="0" max="100" step="5" value="${s.glow}" data-pref="glow">
      </label>
      <label class="field" style="margin-top:8px">
        <span>Gold — <b id="gold-val">${s.goldGlow}%</b></span>
        <input type="range" min="0" max="100" step="5" value="${s.goldGlow}" data-pref="goldGlow">
      </label>
      <label class="field" style="margin-top:8px">
        <span>Background effect — <b id="bgint-val">${s.bgIntensity}%</b></span>
        <input type="range" min="0" max="100" step="5" value="${s.bgIntensity}" data-pref="bgIntensity">
      </label>
    </div>

    <div class="admin-card">
      <h3>Accessibility</h3>
      <div style="display:flex;flex-direction:column;gap:8px">
        <label class="row-card" style="display:flex;align-items:center;gap:10px;cursor:pointer">
          <span class="switch"><input type="checkbox" data-pref="reducedMotion" ${s.reducedMotion ? 'checked' : ''}><span class="slider"></span></span>
          <span class="grow" style="font-size:11.5px">Reduce motion</span>
        </label>
        <label class="row-card" style="display:flex;align-items:center;gap:10px;cursor:pointer">
          <span class="switch"><input type="checkbox" data-pref="highContrast" ${s.highContrast ? 'checked' : ''}><span class="slider"></span></span>
          <span class="grow" style="font-size:11.5px">High contrast borders</span>
        </label>
      </div>
    </div>`;
}

export function bindThemePanel(root, onChange) {
  root.querySelectorAll('[data-pref]').forEach((input) => {
    const key = input.dataset.pref;
    input.addEventListener('input', () => {
      let value;
      if (input.type === 'checkbox') value = input.checked;
      else if (input.type === 'range') value = Number(input.value);
      else value = input.value;
      theme.set({ [key]: value });
      syncLabels(root);
      onChange?.(key, value);
    });
  });

  root.querySelectorAll('[data-swatch]').forEach((btn) => {
    btn.addEventListener('click', () => {
      applySwatch(btn.dataset.swatch);
    });
  });

  syncLabels(root);
}

function syncLabels(root) {
  const map = { glow: '#glow-val', goldGlow: '#gold-val', bgIntensity: '#bgint-val' };
  Object.entries(map).forEach(([key, sel]) => {
    const node = root.querySelector(sel);
    if (node) node.textContent = `${theme.settings[key]}%`;
  });
}

/* ========================================================================== */
/* Settings panel                                                             */
/* ========================================================================== */
export function settingsPanel(ctx) {
  return `
    <div class="admin-card">
      <h3>Connection</h3>
      ${ctx.health ? `
        <div class="stat-grid">
          <div class="stat-tile good"><div class="st-label">Status</div><div class="st-value" style="font-size:14px">${esc(ctx.health.status || 'unknown')}</div></div>
          <div class="stat-tile"><div class="st-label">Service</div><div class="st-value" style="font-size:14px">${esc(ctx.health.service || '—')}</div></div>
        </div>`
        : '<div class="empty-hint">Backend not reachable.</div>'}
      <div style="margin-top:10px">
        <label class="field">
          <span>API base path</span>
          <input type="text" data-setting="apiBase" value="${esc(ctx.apiBase)}" readonly>
        </label>
      </div>
    </div>

    <div class="admin-card">
      <h3>Run behaviour</h3>
      <label class="field">
        <span>Polling interval — <b id="poll-val">${ctx.pollMs} ms</b></span>
        <input type="range" min="800" max="10000" step="200" value="${ctx.pollMs}" data-setting="pollMs">
      </label>
      <div style="display:flex;flex-direction:column;gap:8px;margin-top:10px">
        <label class="row-card" style="display:flex;align-items:center;gap:10px;cursor:pointer">
          <span class="switch"><input type="checkbox" data-setting="autoStart" ${ctx.autoStart ? 'checked' : ''}><span class="slider"></span></span>
          <span class="grow" style="font-size:11.5px">Auto-start run after creation</span>
        </label>
        <label class="row-card" style="display:flex;align-items:center;gap:10px;cursor:pointer">
          <span class="switch"><input type="checkbox" data-setting="showTimestamps" ${ctx.showTimestamps ? 'checked' : ''}><span class="slider"></span></span>
          <span class="grow" style="font-size:11.5px">Show timestamps on messages</span>
        </label>
        <label class="row-card" style="display:flex;align-items:center;gap:10px;cursor:pointer">
          <span class="switch"><input type="checkbox" data-setting="compactFeed" ${ctx.compactFeed ? 'checked' : ''}><span class="slider"></span></span>
          <span class="grow" style="font-size:11.5px">Compact chat feed</span>
        </label>
      </div>
    </div>

    <div class="admin-card">
      <h3>Keyboard</h3>
      <div class="kv-grid">
        <dt>Ctrl / ⌘ + K</dt><dd>Command palette</dd>
        <dt>Ctrl / ⌘ + B</dt><dd>Toggle sidebar</dd>
        <dt>Ctrl / ⌘ + Enter</dt><dd>Submit task</dd>
        <dt>Esc</dt><dd>Close modal / palette</dd>
      </div>
    </div>

    <div class="admin-card">
      <h3>Data</h3>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-sm" data-action="refresh">Reload workspaces &amp; models</button>
        <button class="btn btn-sm" data-action="reload-runs">Reload runs</button>
        <button class="btn btn-sm btn-danger" data-action="clear-chat">Clear chat transcript</button>
      </div>
    </div>`;
}

export function bindSettingsPanel(root, handlers) {
  root.querySelectorAll('[data-setting]').forEach((input) => {
    const key = input.dataset.setting;
    input.addEventListener('input', () => {
      let value;
      if (input.type === 'checkbox') value = input.checked;
      else if (input.type === 'range') value = Number(input.value);
      else value = input.value;
      const label = root.querySelector('#poll-val');
      if (label && key === 'pollMs') label.textContent = `${value} ms`;
      handlers.onSetting?.(key, value);
    });
  });
  root.querySelectorAll('[data-action]').forEach((btn) => {
    btn.addEventListener('click', () => handlers.onAction?.(btn.dataset.action));
  });
}