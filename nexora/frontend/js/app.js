/**
 * Nexora — application orchestrator.
 *
 * Wires the Odysseus-style shell (icon rail + sidebar + chat composer +
 * tool modals) to the Nexora /api/v1 backend. No backend behaviour is changed
 * here; this file only reads and drives the documented API surface.
 */
import './state.js';
import './api.js';

import {
  $, $$, on, delegate, esc, formatNumber, formatTokens, formatDuration,
  formatDateTime, relativeTime, humanize, tag, truncate,
} from './ui/dom.js';
import { theme, initThemeChrome } from './ui/theme.js';
import { modals } from './ui/modal.js';
import { shell } from './ui/shell.js';
import { toast } from './ui/toast.js';
import { renderMarkdown } from './ui/markdown.js';
import { PANELS, PANEL_MAP, setActivePanel } from './panels.js';
import { themePanel, bindThemePanel, settingsPanel, bindSettingsPanel } from './ui/prefs.js';

/* ========================================================================== */
const SAMPLE_TASKS = {
  calculator: 'Fix the empty-input failure in the calculator logic and add a regression test for the edge case.',
  api: 'Repair the API validation bug in the request schema and keep the error semantics backward compatible.',
  cli: 'Correct the CLI argument parsing issue and ensure the help text stays accurate for the new flag flow.',
};

const ROUTE_PRESETS = [
  { key: 'auto', label: 'Auto route', tier: 'auto', description: 'Router picks the best-fit Nemotron tier per step.' },
  { key: 'nano', label: 'Nemotron 3 Nano', tier: 'nano', description: 'Fastest tier — quick scans and cheap validation passes.' },
  { key: 'super', label: 'Nemotron 3 Super', tier: 'super', description: 'Balanced reasoning for patch generation and fixes.' },
  { key: 'ultra', label: 'Nemotron 3 Ultra', tier: 'ultra', description: 'Deepest context for multi-file and policy-heavy work.' },
];

/**
 * Provider that owns auto routing. Mirrors PRIMARY_PROVIDER in
 * backend/app/core/provider_registry.py — the registry dispatches strictly on
 * ModelRegistry.provider, so anything else is a secondary provider that has to
 * be selected explicitly in fixed mode.
 */
const PRIMARY_PROVIDER = 'nebius';

const isPrimaryProvider = (model) => (model.provider || PRIMARY_PROVIDER) === PRIMARY_PROVIDER;

const TERMINAL = ['completed', 'failed', 'blocked', 'cancelled', 'timeout_failed', 'interrupted'];
const ACTIVE = [
  'queued', 'analyzing', 'security_review', 'planning', 'awaiting_start',
  'context_build', 'model_step', 'policy_check', 'executing', 'validating',
  'replanning', 'awaiting_approval', 'cancel_requested',
];

/* ========================================================================== */
class NexoraApp {
  constructor() {
    this.state = window.NexoraState;
    this.messages = [];
    this.activePanel = 'runs';
    this.pollTimer = null;
    this.pollMs = 2000;
    this.autoStart = true;
    this.showTimestamps = true;
    this.compactFeed = false;
    this.apiBase = '/api/v1';
    this.health = null;
    this.attachments = [];
    this.historyEl = $('#chat-history');
    this.chatEl = $('#chat-container');
  }

  /* ================================================================ boot */
  async init() {
    this.setupDefaults();
    shell.init();
    initThemeChrome();
    this.setupModals();
    this.bindComposer();
    this.bindRailAndTools();
    this.bindSidebar();
    this.bindGlobalKeys();
    this.registerCommands();

    await this.bootstrapData();
    this.renderAll();
    this.dismissLoader();
  }

  setupDefaults() {
    const saved = (() => {
      try { return JSON.parse(localStorage.getItem('nexora-prefs') || '{}'); } catch { return {}; }
    })();
    Object.assign(this, {
      pollMs: Number(saved.pollMs) || 2000,
      autoStart: saved.autoStart !== false,
      showTimestamps: saved.showTimestamps !== false,
      compactFeed: !!saved.compactFeed,
    });
    this.persistPrefs();
  }

  persistPrefs() {
    try {
      localStorage.setItem('nexora-prefs', JSON.stringify({
        pollMs: this.pollMs,
        autoStart: this.autoStart,
        showTimestamps: this.showTimestamps,
        compactFeed: this.compactFeed,
      }));
    } catch { /* ignore */ }
  }

  dismissLoader() {
    $('#app-loader')?.classList.add('done');
  }

  /* ================================================================ data */
  async bootstrapData() {
    this.bodyBusy(true);
    await this.probeApiBase();
    try {
      this.health = await window.NexoraApi.health();
      this.setConnection(true, this.health?.service || 'Nexora-backend');
    } catch {
      this.health = null;
      this.setConnection(false, 'API unreachable');
    }

    const results = await Promise.allSettled([
      this.loadWorkspaces(),
      this.loadModels(),
      this.loadBudgetProfiles(),
      this.loadRuns(),
    ]);
    const failed = results.filter((r) => r.status === 'rejected');
    if (failed.length) {
      toast(`Some data failed to load (${failed.length}). Showing defaults.`, 'warning');
    }
    this.bodyBusy(false);
  }

  /**
   * The UI is usually served by a standalone static server on :3000 while the
   * API lives on :8000. Probe candidates in order and repoint the client at
   * whichever answers `/health`. `?api=` overrides everything.
   */
  async probeApiBase() {
    if (new URLSearchParams(window.location.search).get('api')) {
      this.apiBase = window.NexoraApi.baseUrl;
      return;
    }
    const suffix = '/api/v1';
    const port = window.location.port || (window.location.protocol === 'https:' ? '443' : '80');
    const candidates = [];

    // Static server on a dev port → try the backend port first so the happy
    // path never issues a doomed same-origin request.
    if (!['80', '443', '8000'].includes(port)) {
      candidates.push(`${window.location.protocol}//${window.location.hostname}:8000${suffix}`);
    }
    candidates.push(`${window.location.origin}${suffix}`);

    for (const base of candidates) {
      try {
        await new window.ApiClient(base).request('/health');
        this.apiBase = window.NexoraApi.setBaseUrl(base);
        if (base !== candidates[candidates.length - 1]) toast(`API base → ${base}`, 'info');
        return;
      } catch {
        /* try the next candidate */
      }
    }
    this.apiBase = window.NexoraApi.baseUrl;
  }

  async loadWorkspaces() {
    const data = await window.NexoraApi.workspaces.list({ active_only: true });
    this.state.set('workspaces', data.workspaces || []);
    if (!this.state.get('selectedWorkspaceId') && this.state.get('workspaces').length) {
      const remembered = localStorage.getItem('nexora-workspace');
      const match = this.state.get('workspaces').find((w) => w.id === remembered);
      this.state.set('selectedWorkspaceId', (match || this.state.get('workspaces')[0]).id);
    }
  }

  async loadModels() {
    const models = await window.NexoraApi.models.list(false);
    this.state.set('models', models || []);
    this.state.set('enabledModels', (models || []).filter((m) => m.is_enabled));
  }

  async loadBudgetProfiles() {
    const profiles = await window.NexoraApi.budgetProfiles.list();
    this.state.set('budgetProfiles', profiles || []);
    const def = profiles.find((p) => p.is_default) || profiles[0] || null;
    this.state.set('defaultBudgetProfile', def);
    const remembered = localStorage.getItem('nexora-profile');
    const match = profiles.find((p) => p.id === remembered);
    this.state.set('selectedBudgetProfileId', (match || def)?.id || null);
  }

  async loadRuns() {
    const data = await window.NexoraApi.runs.list({ page_size: 40 });
    this.state.set('runs', data.runs || []);
  }

  bodyBusy(busy) {
    document.body.classList.toggle('is-loading', busy);
  }

  setConnection(online, label) {
    const dot = $('#conn-dot');
    const text = $('#conn-text');
    const meta = $('#conn-meta');
    if (dot) dot.className = `conn-dot ${online ? 'online' : 'offline'}`;
    if (text) text.textContent = online ? label : label;
    if (meta) meta.textContent = `${this.apiBase} · ${new Date().toLocaleTimeString()}`;
  }

  /* ================================================================ sidebar */
  bindSidebar() {
    delegate($('#nav-workspaces'), 'click', '.list-item', (_e, node) => {
      this.selectWorkspace(node.dataset.workspaceId);
    });

    $$('.sample-task').forEach((btn) => on(btn, 'click', () => {
      const text = SAMPLE_TASKS[btn.dataset.sample];
      if (!text) return;
      const input = $('#message');
      input.value = text;
      this.autoGrow(input);
      this.updateGhost();
      input.focus();
      toast('Sample task loaded into the composer.', 'info');
    }));

    on($('#rail-new-run'), 'click', () => this.newRun());
    on($('#workspace-chip'), 'click', () => this.cycleWorkspace());
    on($('#budget-chip'), 'click', () => this.cycleBudgetProfile());
  }

  selectWorkspace(id) {
    if (!id) return;
    this.state.set('selectedWorkspaceId', id);
    try { localStorage.setItem('nexora-workspace', id); } catch { /* ignore */ }
    this.renderWorkspaces();
    this.updateComposerChips();
  }

  cycleWorkspace() {
    const list = this.state.get('workspaces') || [];
    if (!list.length) return toast('No workspaces available.', 'warning');
    const idx = list.findIndex((w) => w.id === this.state.get('selectedWorkspaceId'));
    this.selectWorkspace(list[(idx + 1) % list.length].id);
  }

  cycleBudgetProfile() {
    const list = this.state.get('budgetProfiles') || [];
    if (!list.length) return toast('No budget profiles available.', 'warning');
    const idx = list.findIndex((p) => p.id === this.state.get('selectedBudgetProfileId'));
    const next = list[(idx + 1) % list.length];
    this.state.set('selectedBudgetProfileId', next.id);
    try { localStorage.setItem('nexora-profile', next.id); } catch { /* ignore */ }
    this.updateComposerChips();
    toast(`Budget profile: ${next.name}`, 'gold');
  }

  renderWorkspaces() {
    const host = $('#nav-workspaces');
    if (!host) return;
    const list = this.state.get('workspaces') || [];
    const selected = this.state.get('selectedWorkspaceId');
    const count = $('#ws-count');
    if (count) count.textContent = String(list.length);

    if (!list.length) {
      host.innerHTML = '<div class="empty-hint">No active workspaces.</div>';
      return;
    }
    host.innerHTML = list.map((w) => `
      <button class="list-item ${w.id === selected ? 'active' : ''}" data-workspace-id="${esc(w.id)}" role="option" aria-selected="${w.id === selected}">
        <span class="lead-ico">◈</span>
        <span class="grow" title="${esc(w.description || w.name)}">${esc(w.name)}</span>
        <span class="item-meta">${esc(w.repository_type || '')}</span>
      </button>`).join('');
  }

  renderRunsList() {
    const host = $('#nav-runs');
    if (!host) return;
    const list = this.state.get('runs') || [];
    const currentId = this.state.get('currentRun')?.id;
    const count = $('#runs-count');
    if (count) count.textContent = String(list.length);

    if (!list.length) {
      host.innerHTML = '<div class="empty-hint">No runs yet — describe a task to start one.</div>';
      return;
    }
    host.innerHTML = list.slice(0, 25).map((run) => `
      <button class="list-item ${run.id === currentId ? 'active' : ''}" data-run-id="${esc(run.id)}" title="${esc(run.task_text)}">
        <span class="lead-ico">${run.status === 'completed' ? '✓' : run.status === 'failed' ? '✕' : '○'}</span>
        <span class="grow">${esc(truncate(run.task_text, 30))}</span>
        <span class="item-meta">${esc(relativeTime(run.created_at))}</span>
      </button>`).join('');
  }

  bindRunsList() {
    delegate($('#nav-runs'), 'click', '.list-item', (_e, node) => {
      this.selectRun(node.dataset.runId);
    });
  }

  /* ================================================================ composer */
  bindComposer() {
    const input = $('#message');
    const ghost = $('#message-ghost');
    const send = $('#send-btn');

    on(input, 'input', () => { this.autoGrow(input); this.updateGhost(); });
    on(input, 'keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        this.submit();
      }
    });
    on(send, 'click', () => {
      if (this.isRunActive()) this.stopRun();
      else this.submit();
    });

    this.updateGhost(ghost, input);

    // routing mode
    delegate($('#routing-mode-toggle'), 'click', 'button', (_e, node) => {
      $$('#routing-mode-toggle button').forEach((b) => b.classList.toggle('active', b === node));
      this.state.set('routingMode', node.dataset.mode);
      this.renderModelPicker();
      if (node.dataset.mode === 'fixed' && !this.state.get('selectedModelId')) {
        toast('Pick a model target in the routing menu.', 'info');
      }
    });

    // model picker
    const mpBtn = $('#model-picker-btn');
    const mpMenu = $('#model-picker-menu');
    on(mpBtn, 'click', (e) => {
      e.stopPropagation();
      mpMenu.classList.toggle('hidden');
      $('#model-picker-search')?.focus();
    });
    on($('#model-picker-search'), 'input', () => this.renderModelPicker());
    on($('#model-picker-refresh'), 'click', async (e) => {
      e.stopPropagation();
      await this.loadModels();
      this.renderModelPicker();
      toast('Model registry reloaded.', 'success');
    });
    delegate(mpMenu, 'click', '.model-picker-item', (_e, node) => {
      this.state.set('selectedModelId', node.dataset.modelId || null);
      mpMenu.classList.add('hidden');
      this.renderModelPickerLabel();
      const model = (this.state.get('models') || []).find((m) => m.id === node.dataset.modelId);
      toast(model ? `Model target: ${model.display_name}` : 'Auto routing', 'info');
    });
    on(document, 'click', (e) => {
      if (!mpMenu.classList.contains('hidden') && !mpMenu.contains(e.target) && !mpBtn.contains(e.target)) {
        mpMenu.classList.add('hidden');
      }
    });

    // tools overflow
    const toolsBtn = $('#overflow-plus-btn');
    const toolsMenu = $('#overflow-menu');
    on(toolsBtn, 'click', (e) => {
      e.stopPropagation();
      toolsMenu.classList.toggle('hidden');
      toolsBtn.classList.toggle('expanded', !toolsMenu.classList.contains('hidden'));
      toolsBtn.setAttribute('aria-expanded', String(!toolsMenu.classList.contains('hidden')));
    });
    delegate(toolsMenu, 'click', '.overflow-menu-item', (_e, node) => {
      toolsMenu.classList.add('hidden');
      toolsBtn.classList.remove('expanded');
      const tool = node.dataset.toolAction;
      if (tool === 'new') this.newRun();
      else if (tool === 'toggle-sidebar') shell.collapse();
      else this.openPanel(tool);
    });
    on(document, 'click', (e) => {
      if (!toolsMenu.classList.contains('hidden') && !toolsMenu.contains(e.target) && !toolsBtn.contains(e.target)) {
        toolsMenu.classList.add('hidden');
        toolsBtn.classList.remove('expanded');
      }
    });

    this.renderOverflowMenu();
    this.bindPinnedBar();
  }

  autoGrow(input) {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, window.innerHeight * 0.4)}px`;
  }

  updateGhost(ghost = $('#message-ghost'), input = $('#message')) {
    if (!ghost || !input) return;
    const placeholder = input.placeholder || '';
    const value = input.value;
    if (value.length >= (placeholder.length * 0.6)) {
      ghost.textContent = '';
      return;
    }
    const typed = value.length;
    ghost.innerHTML = `${esc(value)}<span style="opacity:.45">${esc(placeholder.slice(typed))}</span>`;
  }

  /* ---------------------------------------------------------- model picker */
  renderModelPicker() {
    const list = $('#model-picker-list');
    if (!list) return;
    const models = this.state.get('models') || [];
    const query = ($('#model-picker-search')?.value || '').trim().toLowerCase();
    const mode = this.state.get('routingMode') || 'auto';

    const entries = mode === 'fixed'
      ? models.filter((m) => !query || `${m.display_name} ${m.tier} ${m.provider}`.toLowerCase().includes(query))
        .slice()
        // Primary provider first, then secondary, so auto-adjacent ordering
        // never buries the models auto routing would actually pick.
        .sort((a, b) => Number(isPrimaryProvider(b)) - Number(isPrimaryProvider(a)))
        .map((m) => ({
          id: m.id,
          name: m.display_name,
          meta: [
            m.provider,
            isPrimaryProvider(m) ? null : 'secondary',
            `tier ${m.tier}`,
            `${formatTokens(m.context_capacity)} ctx`,
            m.is_enabled ? null : 'disabled',
          ].filter(Boolean).join(' · '),
          disabled: !m.is_enabled,
        }))
      : ROUTE_PRESETS.map((p) => ({ id: p.key, name: p.label, meta: p.description, gold: p.key === 'auto' }));

    if (!entries.length) {
      list.innerHTML = '<div class="cmdk-empty">No models match.</div>';
      return;
    }

    const selected = this.state.get('selectedModelId');
    const activeKey = mode === 'fixed' ? selected : (selected || 'auto');

    // In auto mode only the primary provider's tiers are reachable, so surface
    // the secondary providers as an explicit, non-clickable reminder.
    const secondary = models.filter((m) => !isPrimaryProvider(m) && m.is_enabled);
    const secondaryNote = mode === 'auto' && secondary.length
      ? `<div class="cmdk-empty">${secondary.length} secondary model${secondary.length > 1 ? 's' : ''} `
        + `(${esc([...new Set(secondary.map((m) => m.provider))].join(', '))}) — switch to Fixed routing to target them.</div>`
      : '';

    list.innerHTML = entries.map((e) => `
      <button class="model-picker-item ${e.id === activeKey ? 'selected' : ''}" data-model-id="${esc(e.id)}" ${e.disabled ? 'disabled' : ''}>
        <span class="mp-name" ${e.gold ? 'style="color:var(--gold)"' : ''}>${esc(e.name)}</span>
        <span class="mp-meta">${esc(e.meta)}</span>
      </button>`).join('') + secondaryNote;
  }

  renderModelPickerLabel() {
    const label = $('#model-picker-label');
    if (!label) return;
    const mode = this.state.get('routingMode') || 'auto';
    const models = this.state.get('models') || [];
    const id = this.state.get('selectedModelId');
    const model = models.find((m) => m.id === id);
    if (mode === 'auto') {
      label.textContent = model ? `Auto · ${model.tier || model.display_name}` : 'Auto route';
      label.title = isPrimaryProvider(model || { provider: PRIMARY_PROVIDER })
        ? `Router selects the best-fit ${PRIMARY_PROVIDER} tier`
        : `Auto routing uses the primary provider (${PRIMARY_PROVIDER})`;
      return;
    }
    label.textContent = model ? model.display_name : 'Pick model';
    label.title = model
      ? `${model.model_id} · ${model.provider || PRIMARY_PROVIDER}${isPrimaryProvider(model) ? '' : ' (secondary)'}`
      : 'No model selected';
  }

  /* ---------------------------------------------------------- tools menus */
  renderOverflowMenu() {
    const menu = $('#overflow-menu');
    if (!menu) return;
    const items = [
      { tool: 'runs', icon: '⌁', label: 'Runs' },
      { tool: 'plan', icon: '◈', label: 'Execution plan' },
      { tool: 'policy', icon: '⛨', label: 'Policy decisions', gold: true },
      { tool: 'security', icon: '⛊', label: 'Security review', gold: true },
      { tool: 'approvals', icon: '✓', label: 'Approvals', gold: true },
      { tool: 'patch', icon: '⧉', label: 'Patch diff' },
      { tool: 'tests', icon: '⚗', label: 'Validation' },
      { tool: 'evidence', icon: '▦', label: 'Evidence & metrics' },
      { tool: 'audit', icon: '⛓', label: 'Audit trail' },
      { sep: true },
      { tool: 'theme', icon: '☀', label: 'Theme' },
      { tool: 'settings', icon: '⚙', label: 'Settings' },
      { sep: true },
      { tool: 'new', icon: '＋', label: 'New run', hint: 'Ctrl+N' },
      { tool: 'toggle-sidebar', icon: '⇔', label: 'Toggle sidebar', hint: 'Ctrl+B' },
    ];
    menu.innerHTML = items.map((i) => {
      if (i.sep) return '<div class="overflow-menu-sep"></div>';
      const pending = i.tool === 'approvals' ? this.pendingApprovalCount() : 0;
      return `
        <button class="overflow-menu-item" data-tool-action="${i.tool}">
          <span class="ico" ${i.gold ? 'style="color:var(--gold)"' : ''}>${i.icon}</span>
          <span class="grow">${esc(i.label)}</span>
          ${pending ? `<span class="tag tag-pending">${pending}</span>` : ''}
          ${i.hint ? `<span class="kbd-hint">${esc(i.hint)}</span>` : ''}
        </button>`;
    }).join('');
  }

  renderPinnedBar() {
    const bar = $('#pinned-tools-bar');
    if (!bar) return;
    if (!this.pinned) this.pinned = new Set();
    const pinned = ['policy', 'security', 'approvals'];
    bar.innerHTML = pinned.map((id) => {
      const panel = PANEL_MAP[id];
      const on = this.pinned.has(id);
      return `<button class="pinned-chip ${on ? 'on' : ''}" data-pin="${id}" title="Pin ${esc(panel?.label || id)}">${esc(panel?.icon || '◆')} ${esc(panel?.label || id)}</button>`;
    }).join('');
  }

  bindPinnedBar() {
    const bar = $('#pinned-tools-bar');
    if (!bar) return;
    delegate(bar, 'click', '.pinned-chip', (_e, node) => {
      const id = node.dataset.pin;
      if (!this.pinned) this.pinned = new Set();
      if (this.pinned.has(id)) this.pinned.delete(id);
      else this.pinned.add(id);
      this.renderPinnedBar();
    });
  }

  /* ================================================================ modals */
  setupModals() {
    const root = $('#tool-modal');
    modals.register('tool', root, {
      // `onOpen` fires the first time the modal is shown, `onRefresh` on every
      // later `open()` while it is already up. Both must honour the requested
      // panel: ModalManager.open() dispatches to onRefresh (not onOpen) once the
      // modal is open, so without it switching panels from the icon rail, the
      // keyboard shortcuts or the command palette is a silent no-op.
      onOpen: (id) => this.renderToolModal(id),
      onRefresh: (id) => this.renderToolModal(id),
    });
    modals.bindGlobalKeys();

    on($('#tool-modal-close'), 'click', () => modals.close('tool'));
    on($('#tool-modal-prev'), 'click', () => this.cyclePanel(-1));
    on($('#tool-modal-next'), 'click', () => this.cyclePanel(1));
    delegate($('#tool-modal-tabs'), 'click', '.admin-tab', (_e, node) => {
      this.renderToolModal(node.dataset.tab);
    });
    delegate($('#tool-modal-footer'), 'click', '[data-modal-close]', () => modals.close('tool'));
  }

  panelOrder() {
    return [...PANELS.map((p) => p.id), 'theme', 'settings'];
  }

  cyclePanel(delta) {
    const order = this.panelOrder();
    const idx = order.indexOf(this.activePanel);
    const next = order[(idx + delta + order.length) % order.length];
    this.renderToolModal(next);
  }

  openPanel(id) {
    this.activePanel = id;
    setActivePanel(PANEL_MAP[id] ? id : null);
    modals.open('tool', id);
    if (PANEL_MAP[id]) setActivePanel(id);
  }

  viewModel() {
    const profileId = this.state.get('selectedBudgetProfileId');
    const profiles = this.state.get('budgetProfiles') || [];
    return {
      state: this.state,
      runs: this.state.get('runs') || [],
      currentRun: this.state.get('currentRun'),
      currentRunDetail: this.state.get('currentRunDetail'),
      selectedProfile: profiles.find((p) => p.id === profileId) || this.state.get('defaultBudgetProfile'),
      workspaces: this.state.get('workspaces') || [],
      models: this.state.get('models') || [],
      health: this.health,
      apiBase: this.apiBase,
      pollMs: this.pollMs,
      autoStart: this.autoStart,
      showTimestamps: this.showTimestamps,
      compactFeed: this.compactFeed,
      actions: {
        selectRun: (id) => this.selectRun(id),
        decideApproval: (id, approve) => this.decideApproval(id, approve),
        refresh: () => this.bootstrapData(),
        reloadRuns: () => this.loadRuns(),
        clearChat: () => this.clearChat(),
      },
    };
  }

  renderToolModal(forceId = null) {
    const id = forceId || this.activePanel;
    this.activePanel = id;
    const body = $('#tool-modal-body');
    const tabs = $('#tool-modal-tabs');
    const title = $('#tool-modal-title');
    const subtitle = $('#tool-modal-subtitle');
    if (!body) return;

    // tabs
    tabs.innerHTML = this.panelOrder().map((pid) => {
      const panel = PANEL_MAP[pid];
      const label = panel ? panel.label : (pid === 'theme' ? 'Theme' : 'Settings');
      const icon = panel ? panel.icon : (pid === 'theme' ? '☀' : '⚙');
      const gold = pid === 'theme';
      return `<button class="admin-tab ${gold ? 'gold-tab' : ''} ${pid === id ? 'active' : ''}" data-tab="${pid}">${esc(icon)} ${esc(label)}</button>`;
    }).join('');

    const panel = PANEL_MAP[id];
    title.innerHTML = panel
      ? `<span>${esc(panel.icon)}</span> ${esc(panel.label)}`
      : (id === 'theme' ? '<span>☀</span> Theme' : '<span>⚙</span> Settings');
    const run = this.state.get('currentRun');
    subtitle.textContent = run ? `${truncate(run.task_text, 46)} · ${run.status}` : 'no active run';

    if (id === 'theme') {
      body.innerHTML = themePanel();
      bindThemePanel(body, () => this.applyThemeClasses());
    } else if (id === 'settings') {
      body.innerHTML = settingsPanel(this.viewModel());
      bindSettingsPanel(body, {
        onSetting: (key, value) => this.setPreference(key, value),
        onAction: (action) => this.runSettingsAction(action),
      });
    } else if (panel) {
      const ctx = this.viewModel();
      body.innerHTML = panel.render(ctx);
      panel.bind?.(body, ctx);
    }

    $('#tool-modal-footer').innerHTML = '';
    if (panel && (id === 'runs')) {
      $('#tool-modal-footer').innerHTML = '<button class="btn btn-sm" data-modal-close>Close</button>';
    }

    setActivePanel(PANEL_MAP[id] ? id : null);
    body.scrollTop = 0;
  }

  setPreference(key, value) {
    if (key === 'pollMs') this.pollMs = value;
    if (key === 'autoStart') this.autoStart = value;
    if (key === 'showTimestamps') this.showTimestamps = value;
    if (key === 'compactFeed') {
      this.compactFeed = value;
      this.historyEl.classList.toggle('compact-feed', value);
    }
    this.persistPrefs();
    if (key === 'pollMs' && this.isRunActive()) {
      this.restartPolling(this.state.get('currentRun').id);
    }
  }

  async runSettingsAction(action) {
    if (action === 'refresh') {
      await this.bootstrapData();
      this.renderAll();
      toast('Reloaded workspaces, models and profiles.', 'success');
    } else if (action === 'reload-runs') {
      await this.loadRuns();
      this.renderRunsList();
      this.renderToolModal();
      toast('Runs reloaded.', 'success');
    } else if (action === 'clear-chat') {
      this.clearChat();
      toast('Chat transcript cleared.', 'info');
    }
  }

  applyThemeClasses() {
    document.body.classList.toggle('hc', !!theme.settings.highContrast);
  }

  /* ================================================================ rail */
  bindRailAndTools() {
    delegate(document, 'click', '[data-tool]', (_e, node) => {
      this.openPanel(node.dataset.tool);
    });
    this.bindRunsList();
  }

  bindGlobalKeys() {
    on(document, 'keydown', (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.target.matches('input, textarea')) return;
      const map = { 1: 'runs', 2: 'plan', 3: 'policy', 4: 'security', 5: 'evidence', 6: 'patch', 7: 'tests', 8: 'approvals', 9: 'audit' };
      if (map[e.key]) {
        e.preventDefault();
        this.openPanel(map[e.key]);
      } else if (e.key.toLowerCase() === 't') {
        e.preventDefault();
        this.openPanel('theme');
      } else if (e.key.toLowerCase() === 'n') {
        e.preventDefault();
        this.newRun();
      }
    });
  }

  registerCommands() {
    shell.registerCommands([
      ...this.panelOrder().map((id) => {
        const panel = PANEL_MAP[id];
        return {
          label: `Open ${panel ? panel.label : id === 'theme' ? 'Theme' : 'Settings'}`,
          group: 'panel',
          icon: panel ? panel.icon : (id === 'theme' ? '☀' : '⚙'),
          gold: id === 'theme',
          run: () => this.openPanel(id),
        };
      }),
      { label: 'New run', group: 'action', icon: '＋', hint: 'Ctrl+N', run: () => this.newRun() },
      { label: 'Toggle sidebar', group: 'action', icon: '⇔', hint: 'Ctrl+B', run: () => shell.collapse() },
      { label: 'Cycle theme (dark / light)', group: 'action', icon: '◐', run: () => { theme.toggleMode(); this.applyThemeClasses(); toast(`Theme: ${theme.label}`, 'info'); } },
      { label: 'Cycle background pattern', group: 'action', icon: '▦', run: () => toast(`Background: ${theme.cyclePattern()}`, 'info') },
      { label: 'Reload model registry', group: 'data', icon: '↻', run: async () => { await this.loadModels(); this.renderModelPickerLabel(); toast('Models reloaded.', 'success'); } },
      { label: 'Reload runs', group: 'data', icon: '↻', run: async () => { await this.loadRuns(); this.renderRunsList(); toast('Runs reloaded.', 'success'); } },
      { label: 'Cancel active run', group: 'action', icon: '■', run: () => this.stopRun() },
    ].concat((this.state.get('workspaces') || []).map((w) => ({
      label: `Switch to ${w.name}`,
      group: 'workspace',
      icon: '◈',
      run: () => this.selectWorkspace(w.id),
    }))));
  }

  /* ================================================================ chat */
  pushMessage(role, text, meta = {}) {
    const msg = { id: `m${Date.now().toString(36)}${(this.messages.length + 1).toString(36)}`, role, text, at: new Date().toISOString(), ...meta };
    this.messages.push(msg);
    this.renderMessage(msg, true);
    return msg;
  }

  clearChat(quiet = false) {
    this.messages = [];
    this.historyEl.innerHTML = '';
    this.chatEl.classList.add('welcome-active');
    if (!quiet) this.pushMessage('system', 'Transcript cleared.');
  }

  renderMessage(msg, animate = false) {
    if (!this.historyEl) return;
    const node = document.createElement('div');
    const cls = msg.role === 'user' ? 'msg-user' : msg.role === 'system' ? 'msg-system' : 'msg-ai';
    const gold = msg.gold ? ' msg-gold' : '';
    node.className = `msg ${cls}${gold}`;
    node.dataset.msgId = msg.id || '';

    const roleLabel = msg.role === 'user' ? 'You'
      : msg.role === 'system' ? 'Nexora'
        : (msg.roleLabel || 'Nexora · policy-gated agent');

    const actions = msg.actions?.length
      ? `<div class="msg-actions">${msg.actions.map((a, i) => `<button class="btn btn-sm ${a.variant || ''}" data-msg-action="${esc(msg.id)}:${i}">${esc(a.label)}</button>`).join('')}</div>`
      : '';

    const stamp = this.showTimestamps && msg.at
      ? `<div class="timestamp">${esc(formatDateTime(msg.at))}</div>`
      : '';

    node.innerHTML = `
      <div class="role">${esc(roleLabel)}</div>
      <div class="body md">${renderMarkdown(msg.text)}</div>
      ${actions}${stamp}`;

    if (!animate) node.style.animation = 'none';
    this.historyEl.appendChild(node);
    this.chatEl.classList.remove('welcome-active');
    this.scrollToBottom();
    this.bindMessageActions(node, msg);
  }

  updateMessage(id, text, meta = {}) {
    const msg = this.messages.find((m) => m.id === id);
    if (!msg) return null;
    if (text !== undefined) msg.text = text;
    Object.assign(msg, meta);
    const node = this.historyEl.querySelector(`[data-msg-id="${CSS.escape(id)}"]`);
    if (node) {
      node.querySelector('.body').innerHTML = renderMarkdown(msg.text);
      if (meta.actions) {
        const actions = `<div class="msg-actions">${msg.actions.map((a, i) => `<button class="btn btn-sm ${a.variant || ''}" data-msg-action="${esc(msg.id)}:${i}">${esc(a.label)}</button>`).join('')}</div>`;
        const existing = node.querySelector('.msg-actions');
        if (existing) existing.outerHTML = actions;
        else node.querySelector('.timestamp')?.insertAdjacentHTML('beforebegin', actions);
        this.bindMessageActions(node, msg);
      }
    }
    this.scrollToBottom();
    return msg;
  }

  bindMessageActions(node, msg) {
    node.querySelectorAll('[data-msg-action]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const idx = Number(btn.dataset.msgAction.split(':')[1]);
        msg.actions?.[idx]?.onClick?.();
      });
    });
  }

  scrollToBottom() {
    if (!this.historyEl) return;
    requestAnimationFrame(() => { this.historyEl.scrollTop = this.historyEl.scrollHeight; });
  }

  /* ================================================================ run lifecycle */
  async submit() {
    const input = $('#message');
    const text = (input.value || '').trim();
    const workspaceId = this.state.get('selectedWorkspaceId');

    if (this.isRunActive()) return toast('A run is already active — stop it first.', 'warning');
    if (!text) { input.focus(); return toast('Describe the task first.', 'error'); }
    if (!workspaceId) { toast('Select a workspace first.', 'error'); return this.openPanel('runs'); }

    const mode = this.state.get('routingMode') || 'auto';
    const modelId = this.state.get('selectedModelId');
    const profileId = this.state.get('selectedBudgetProfileId') || this.state.get('defaultBudgetProfile')?.id;

    input.value = '';
    this.autoGrow(input);
    this.updateGhost();

    this.pushMessage('user', text);
    const pending = this.pushMessage('ai', '`_Creating run…_`', { gold: true, roleLabel: 'Nexora · dispatching' });

    const payload = {
      workspace_id: workspaceId,
      task_text: text,
      routing_mode: mode === 'fixed' ? 'fixed' : 'auto',
      requested_model_id: mode === 'fixed' && modelId ? modelId : null,
      budget_profile_id: profileId || null,
    };

    try {
      const run = await window.NexoraApi.runs.create(payload);
      this.state.set('currentRun', run);
      this.pushMessage('system', `Run \`${run.id}\` created · status **${run.status}** · stage _${run.current_stage || 'queued'}_.`);

      await this.selectRun(run.id, { silent: true });

      this.updateMessage(pending.id, this.describeRun(run), {
        roleLabel: 'Nexora · run created',
        actions: [
          { label: 'Plan', onClick: () => this.openPanel('plan') },
          { label: 'Policy', onClick: () => this.openPanel('policy') },
          { label: 'Security', onClick: () => this.openPanel('security') },
          { label: 'Evidence', onClick: () => this.openPanel('evidence') },
        ],
      });

      if (this.autoStart) await this.startRun(run.id);
      await this.loadRuns();
      this.renderRunsList();
    } catch (error) {
      this.updateMessage(pending.id, `**Run creation failed**\n\n\`${error.message}\``, { gold: false });
      toast(`Run creation failed: ${error.message}`, 'error');
    }
  }

  describeRun(run) {
    const model = (this.state.get('models') || []).find((m) => m.id === run.requested_model_id);
    const profile = (this.state.get('budgetProfiles') || []).find((p) => p.id === run.budget_profile_id);
    const lines = [
      `Run \`${run.id}\` accepted by the gateway.`,
      '',
      `- **Status** — ${tag(run.status)}`,
      `- **Stage** — ${run.current_stage || 'queued'}`,
      `- **Routing** — ${run.routing_mode}${model ? ` → ${model.display_name} (${model.provider || PRIMARY_PROVIDER}${isPrimaryProvider(model) ? '' : ', secondary'})` : ''}`,
      `- **Budget** — ${profile ? `${profile.name} (${profile.max_steps} steps / ${profile.max_tool_calls} tool calls)` : 'default'}`,
      `- **Task hash** — \`${String(run.task_hash || '').slice(0, 24)}\``,
    ];
    if (run.status === 'awaiting_start') {
      lines.push('', 'Execution is waiting for an explicit start.');
    }
    return lines.join('\n');
  }

  isRunActive() {
    const status = this.state.get('currentRun')?.status;
    return ACTIVE.includes(status);
  }

  async startRun(runId) {
    try {
      const run = await window.NexoraApi.runs.start(runId);
      this.state.set('currentRun', run);
      this.pushMessage('system', `Execution started for \`${runId}\`.`);
      this.startPolling(runId);
      this.updateRunStatusUI();
      return run;
    } catch (error) {
      toast(`Could not start run: ${error.message}`, 'error');
      return null;
    }
  }

  async stopRun() {
    const run = this.state.get('currentRun');
    if (!run) return toast('No active run to cancel.', 'warning');
    this.stopPolling();
    try {
      const updated = await window.NexoraApi.runs.cancel(run.id);
      this.state.set('currentRun', updated);
      this.pushMessage('system', `Cancellation requested for \`${run.id}\`.`);
      toast('Run cancelled.', 'warning');
      this.startPolling(run.id);
    } catch (error) {
      toast(`Cancel failed: ${error.message}`, 'error');
    }
    this.updateRunStatusUI();
  }

  async selectRun(runId, options = {}) {
    if (!runId) return null;
    try {
      const detail = await window.NexoraApi.runs.get(runId);
      this.state.set('currentRunDetail', detail);
      this.state.set('currentRun', detail.run);
      if (!options.silent) {
        this.pushMessage('system', `Loaded run \`${runId}\` (${detail.run.status}).`);
      }
      if (this.isRunActive()) this.startPolling(runId);
      else this.stopPolling();
      this.afterRunUpdate();
      return detail;
    } catch (error) {
      if (!options.silent) toast(`Could not load run: ${error.message}`, 'error');
      return null;
    }
  }

  startPolling(runId) {
    this.stopPolling();
    this.pollTimer = setInterval(async () => {
      if (document.hidden) return;
      try {
        const detail = await window.NexoraApi.runs.get(runId);
        const before = this.state.get('currentRun')?.status;
        this.state.set('currentRunDetail', detail);
        this.state.set('currentRun', detail.run);

        if (before !== detail.run.status) {
          this.pushMessage('system', `Stage **${detail.run.status}**${detail.run.current_stage ? ` · _${detail.run.current_stage}_` : ''} for \`${runId}\`.`);
        }

        this.afterRunUpdate();

        if (TERMINAL.includes(detail.run.status)) {
          this.stopPolling();
          this.pushMessage('system', `Run \`${runId}\` finished with **${detail.run.status}**.`);
          toast(`Run ${detail.run.status}.`, detail.run.status === 'completed' ? 'success' : 'warning');
          this.loadRuns().then(() => this.renderRunsList());
        }
      } catch (error) {
        console.error('poll failed', error);
      }
    }, this.pollMs);
    this.updateRunStatusUI();
  }

  restartPolling(runId) {
    if (this.isRunActive()) this.startPolling(runId);
  }

  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    this.updateRunStatusUI();
  }

  afterRunUpdate() {
    this.updateRunStatusUI();
    this.updateCost();
    this.updateRailBadges();
    this.renderRunsList();
    if (modals.isOpen('tool')) this.renderToolModal();
  }

  updateRunStatusUI() {
    const run = this.state.get('currentRun');
    const pill = $('#chat-status');
    const send = $('#send-btn');
    const metaTitle = $('#chat-meta-title');
    const bar = $('#chat-input-bar');

    if (pill) {
      const status = run?.status || 'idle';
      pill.textContent = run ? `${status}${run.current_stage ? ` · ${run.current_stage}` : ''}` : 'idle';
      pill.className = 'chat-status-pill';
      if (TERMINAL.includes(status)) pill.classList.add(status === 'completed' ? 'st-ok' : 'st-bad');
      else if (status !== 'idle') pill.classList.add('st-running');
    }

    if (send) {
      const active = this.isRunActive();
      send.classList.toggle('stop-mode', active);
      send.title = active ? 'Cancel run' : 'Run task';
      send.setAttribute('aria-label', active ? 'Cancel run' : 'Run task');
      send.innerHTML = active
        ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>';
    }

    if (metaTitle) {
      metaTitle.textContent = run ? truncate(run.task_text, 58) : 'Nexora · secure coding agent';
      metaTitle.title = run ? run.task_text : '';
    }

    if (bar) bar.classList.toggle('glow-gold', run?.status === 'awaiting_approval');
    document.body.classList.toggle('policy-locked', run?.status === 'awaiting_start');
  }

  updateCost() {
    const run = this.state.get('currentRun');
    const chip = $('#chat-cost');
    if (!chip) return;
    const total = (run?.input_tokens_used || 0) + (run?.output_tokens_used || 0);
    if (!run || !total) { chip.hidden = true; return; }
    chip.hidden = false;
    chip.textContent = `${formatTokens(total)} tok`;
    chip.title = `${formatNumber(run.input_tokens_used)} in · ${formatNumber(run.output_tokens_used)} out · ${formatDuration(run.total_elapsed_ms)}`;
  }

  pendingApprovalCount() {
    const approvals = this.state.get('currentRunDetail')?.approvals || [];
    return approvals.filter((a) => a.status === 'pending').length;
  }

  updateRailBadges() {
    const pending = this.pendingApprovalCount();
    const btn = document.querySelector('[data-tool="approvals"]');
    if (btn) btn.classList.toggle('rail-badge', pending > 0);
    const security = document.querySelector('[data-tool="security"]');
    if (security) {
      const decision = this.state.get('currentRunDetail')?.security_decision?.decision;
      security.classList.toggle('rail-badge', ['blocked', 'needs_approval'].includes(decision));
      security.classList.toggle('rail-badge-hot', decision === 'needs_approval');
    }
    this.renderOverflowMenu();
  }

  async decideApproval(approvalId, approve) {
    const run = this.state.get('currentRun');
    if (!run) return toast('No active run.', 'warning');
    try {
      await window.NexoraApi.runs.approve(run.id, approvalId, approve);
      toast(approve ? 'Action approved.' : 'Action rejected.', approve ? 'success' : 'warning');
      await this.selectRun(run.id, { silent: true });
      this.startPolling(run.id);
    } catch (error) {
      toast(`Approval failed: ${error.message}`, 'error');
    }
  }

  newRun() {
    this.state.set('currentRun', null);
    this.state.set('currentRunDetail', null);
    this.stopPolling();
    this.clearChat(true);
    this.pushMessage('system', 'New run. Pick a workspace and describe the task.');
    const input = $('#message');
    input?.focus();
    this.renderRunsList();
    this.updateRunStatusUI();
  }

  /* ================================================================ render */
  updateComposerChips() {
    const ws = (this.state.get('workspaces') || []).find((w) => w.id === this.state.get('selectedWorkspaceId'));
    const chip = $('#workspace-chip');
    if (chip) {
      chip.textContent = ws ? truncate(ws.name, 20) : 'No workspace';
      chip.title = ws?.repository_url || 'Select a workspace';
    }
    const profile = (this.state.get('budgetProfiles') || [])
      .find((p) => p.id === this.state.get('selectedBudgetProfileId'))
      || this.state.get('defaultBudgetProfile');
    const budget = $('#budget-chip');
    if (budget) {
      budget.textContent = profile ? profile.name : 'No profile';
      budget.title = profile ? `${profile.max_steps} steps · ${profile.max_tool_calls} tool calls · ${profile.max_input_tokens} in / ${profile.max_output_tokens} out tokens` : 'Select a budget profile';
    }
  }

  renderAll() {
    this.renderWorkspaces();
    this.renderRunsList();
    this.renderModelPicker();
    this.renderModelPickerLabel();
    this.renderOverflowMenu();
    this.renderPinnedBar();
    this.updateComposerChips();
    this.updateRunStatusUI();
    this.updateCost();
    this.updateRailBadges();
    this.applyThemeClasses();
    this.historyEl.classList.toggle('compact-feed', this.compactFeed);
    this.renderWelcomeTip();
    if (modals.isOpen('tool')) this.renderToolModal();
  }

  renderWelcomeTip() {
    const tip = $('#welcome-tip');
    if (!tip) return;
    const tips = [
      'Tip: Ctrl+K opens the command palette.',
      'Tip: Ctrl+B toggles the sidebar.',
      'Tip: Ctrl+Enter submits the composer without leaving the keyboard.',
      'Tip: Keys 1–9 jump straight to a tool panel.',
      'Tip: Shift+Enter adds a line break.',
    ];
    tip.textContent = tips[Math.floor(Math.random() * tips.length)];
  }
}

/* ========================================================================== */
/* boot                                                                       */
/* ========================================================================== */
let app = null;

function boot() {
  app = new NexoraApp();
  window.NexoraApp = app;
  app.init().catch((error) => {
    console.error('Nexora failed to start', error);
    toast(`Startup error: ${error.message}`, 'error');
    $('#app-loader')?.classList.add('done');
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}

export { NexoraApp, ROUTE_PRESETS, SAMPLE_TASKS };