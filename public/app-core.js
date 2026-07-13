const STAGES = [
  { key: 'triagem', label: 'Triagem', detail: 'Anamnese estruturada' },
  { key: 'exames', label: 'Exames', detail: 'Marcadores laboratoriais' },
  { key: 'suplementacao', label: 'Suplementação', detail: 'Protocolo e interações' },
  { key: 'nutricao', label: 'Nutrição', detail: 'Plano alimentar' },
  { key: 'treino', label: 'Treino', detail: 'Estratégia física' },
  { key: 'consolidacao', label: 'Consolidação', detail: 'Síntese multidisciplinar' },
];

const DETAIL_TABS = [
  { key: 'overview', label: 'Visão geral' },
  ...STAGES.map(stage => ({ key: stage.key, label: stage.label })),
  { key: 'report', label: 'Laudo' },
  { key: 'pdf', label: 'Exames PDF' },
];

const STATUS = {
  queued: 'Na fila',
  running: 'Em processamento',
  review_required: 'Aguardando revisão',
  approved: 'Aprovado',
  failed: 'Falhou',
  cancelled: 'Cancelado',
};

const PAGE_META = {
  operation: { eyebrow: 'Dashboard clínico', title: 'Central de atendimentos' },
  patients: { eyebrow: 'Gestão clínica', title: 'Pacientes' },
  reports: { eyebrow: 'Documentos clínicos', title: 'Relatórios e laudos' },
};

const state = {
  csrf: null,
  selectedId: null,
  poll: null,
  processing: false,
  jobs: [],
  selectedFiles: [],
  currentJob: null,
  activePage: 'operation',
  activeTab: 'overview',
  approvalDraft: { reviewer: '', regNumber: '', regType: 'CRM', notes: '' },
};

const $ = id => document.getElementById(id);
const splitList = id => $(id).value.split(',').map(value => value.trim()).filter(Boolean);
const formatBytes = value => !value ? '—' : value < 1024 ? `${value} B` : value < 1048576 ? `${(value / 1024).toFixed(1)} KB` : `${(value / 1048576).toFixed(1)} MB`;
const dateText = value => value ? new Date(value).toLocaleString('pt-BR') : '—';

function notify(message) {
  const element = $('flash');
  element.textContent = message;
  element.classList.remove('hidden');
  clearTimeout(element._t);
  element._t = setTimeout(() => element.classList.add('hidden'), 6200);
}

function setBadge(element, status) {
  element.className = `badge ${status || ''}`;
  element.textContent = STATUS[status] || String(status || 'Aguardando');
}

function text(tag, value, className = '') {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const method = (options.method || 'GET').toUpperCase();
  const binaryBody = options.body instanceof Blob || options.body instanceof ArrayBuffer;
  if (options.body && !(options.body instanceof FormData) && !binaryBody && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (state.csrf && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) headers.set('X-CSRF-Token', state.csrf);

  let response;
  try {
    response = await fetch(path, { ...options, headers, credentials: 'same-origin' });
  } catch {
    throw new Error('Falha de conexão com o servidor. Verifique a internet e tente novamente.');
  }

  const contentType = response.headers.get('content-type') || '';
  let data;
  try { data = contentType.includes('json') ? await response.json() : await response.text(); } catch { data = {}; }
  if (!response.ok) throw new Error(data.detail || data || `HTTP ${response.status}`);
  return data;
}

function isEditingField() {
  const active = document.activeElement;
  return Boolean(active && active.matches('input, textarea, select'));
}

function initNavigation() {
  const main = document.querySelector('main');
  if (!$('pageOperation')) {
    const operation = document.createElement('section');
    operation.id = 'pageOperation';
    operation.className = 'page-view';
    while (main.firstChild) operation.append(main.firstChild);
    main.append(operation);

    const patients = document.createElement('section');
    patients.id = 'pagePatients';
    patients.className = 'page-view hidden';
    patients.innerHTML = `
      <section class="page-intro">
        <div><div class="eyebrow">Base de pacientes</div><h2>Pacientes e histórico clínico</h2><p>Localize rapidamente cada paciente, seus atendimentos, documentos e situação de revisão.</p></div>
        <button class="btn btn-lime" id="patientsNewCase" type="button">Novo atendimento</button>
      </section>
      <article class="card view-card">
        <div class="card-head view-toolbar">
          <div><div class="eyebrow">Cadastros</div><h3>Pacientes registrados</h3></div>
          <label class="search-field"><span>Buscar</span><input id="patientSearch" type="search" placeholder="Nome do paciente"></label>
        </div>
        <div class="card-body"><div id="patientsGrid" class="patients-grid"></div></div>
      </article>`;
    main.append(patients);

    const reports = document.createElement('section');
    reports.id = 'pageReports';
    reports.className = 'page-view hidden';
    reports.innerHTML = `
      <section class="page-intro">
        <div><div class="eyebrow">Revisão profissional</div><h2>Relatórios e laudos</h2><p>Acompanhe laudos em revisão, documentos aprovados e responsáveis pela assinatura.</p></div>
      </section>
      <section id="reportMetrics" class="report-metrics"></section>
      <article class="card view-card">
        <div class="card-head view-toolbar">
          <div><div class="eyebrow">Documentos</div><h3>Laudos gerados</h3></div>
          <label class="search-field"><span>Buscar</span><input id="reportSearch" type="search" placeholder="Paciente ou status"></label>
        </div>
        <div class="card-body"><div id="reportsGrid" class="reports-grid"></div></div>
      </article>`;
    main.append(reports);
  }

  document.querySelectorAll('.nav button').forEach((button, index) => {
    const page = ['operation', 'patients', 'reports'][index];
    button.dataset.page = page;
    button.onclick = () => selectPage(page);
  });

  $('patientsNewCase')?.addEventListener('click', () => {
    selectPage('operation');
    $('nome').focus();
    $('nome').scrollIntoView({ behavior: 'smooth', block: 'center' });
  });

  $('patientSearch')?.addEventListener('input', () => renderPatientsPage(state.jobs));
  $('reportSearch')?.addEventListener('input', () => renderReportsPage(state.jobs));
}

function initSpecialtyTabs() {
  const tabs = document.querySelector('.tabs');
  if (!tabs || tabs.dataset.ready === 'true') return;
  tabs.dataset.ready = 'true';
  tabs.replaceChildren();

  const outputPanel = $('panelOutputs');
  if (outputPanel) outputPanel.remove();

  const reportPanel = $('panelReport');
  STAGES.forEach(stage => {
    const panel = document.createElement('div');
    panel.id = `panel${stage.key.charAt(0).toUpperCase()}${stage.key.slice(1)}`;
    panel.className = 'panel hidden specialty-panel';
    panel.dataset.panel = stage.key;
    reportPanel.parentElement.insertBefore(panel, reportPanel);
  });

  [['panelOverview', 'overview'], ['panelReport', 'report'], ['panelPdf', 'pdf']].forEach(([id, name]) => {
    const panel = $(id);
    if (panel) panel.dataset.panel = name;
  });

  DETAIL_TABS.forEach(tab => {
    const button = document.createElement('button');
    button.className = `tab${tab.key === state.activeTab ? ' active' : ''}`;
    button.dataset.tab = tab.key;
    button.type = 'button';
    button.textContent = tab.label;
    button.addEventListener('click', () => selectTab(tab.key));
    tabs.append(button);
  });
}

function selectPage(name) {
  state.activePage = PAGE_META[name] ? name : 'operation';
  document.querySelectorAll('.page-view').forEach(page => {
    page.classList.toggle('hidden', page.id !== `page${state.activePage.charAt(0).toUpperCase()}${state.activePage.slice(1)}`);
  });
  document.querySelectorAll('.nav button').forEach(button => button.classList.toggle('active', button.dataset.page === state.activePage));
  document.querySelector('.topbar .eyebrow').textContent = PAGE_META[state.activePage].eyebrow;
  document.querySelector('.page-title').textContent = PAGE_META[state.activePage].title;
  if (state.activePage === 'patients') renderPatientsPage(state.jobs);
  if (state.activePage === 'reports') renderReportsPage(state.jobs);
  window.scrollTo({ top: 0, behavior: 'auto' });
}

function openJobFromView(id, tab = 'overview') {
  selectPage('operation');
  state.activeTab = tab;
  loadDetail(id).then(() => {
    $('detailCard')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}

async function checkSession() {
  const session = await api('/api/session');
  if (session.authenticated) {
    state.csrf = session.csrf_token;
    $('loginPanel').classList.add('hidden');
    await boot();
  } else $('loginPanel').classList.remove('hidden');
}

async function boot() {
  initNavigation();
  initSpecialtyTabs();
  selectPage(state.activePage);
  await health();
  await loadJobs();
  if (state.poll) clearInterval(state.poll);
  state.poll = setInterval(async () => {
    if (state.processing || document.hidden || isEditingField()) return;
    await loadJobs(false);
    const job = state.currentJob;
    const needsDetailRefresh = job && state.selectedId && ['queued', 'running'].includes(job.status) && job.current_stage < 6;
    if (needsDetailRefresh) await loadDetail(state.selectedId, false, { preserveScroll: true });
  }, 8000);
}

async function health() {
  try {
    const status = await api('/api/health');
    const element = $('health');
    element.classList.toggle('ok', status.status === 'operational');
    element.querySelector('span:last-child').textContent = status.status === 'operational' ? `Operacional · ${status.processing_mode}` : 'Configuração incompleta';
  } catch {
    $('health').querySelector('span:last-child').textContent = 'API indisponível';
  }
}

$('loginForm').addEventListener('submit', async event => {
  event.preventDefault();
  $('loginError').textContent = '';
  try {
    const data = await api('/api/login', { method: 'POST', body: JSON.stringify({ password: $('password').value }) });
    state.csrf = data.csrf_token;
    $('loginPanel').classList.add('hidden');
    $('password').value = '';
    await boot();
  } catch (error) {
    $('loginError').textContent = error.message;
  }
});

$('logout').onclick = async () => {
  try { await api('/api/logout', { method: 'POST', body: '{}' }); }
  finally { state.csrf = null; location.reload(); }
};

$('refresh').onclick = async () => {
  await loadJobs();
  if (state.selectedId) await loadDetail(state.selectedId, true, { preserveScroll: true });
};

$('newAttendanceHero').onclick = () => {
  selectPage('operation');
  $('nome').focus();
  $('nome').scrollIntoView({ behavior: 'smooth', block: 'center' });
};

function selectTab(name) {
  const valid = DETAIL_TABS.some(tab => tab.key === name);
  state.activeTab = valid ? name : 'overview';
  document.querySelectorAll('.tab').forEach(button => button.classList.toggle('active', button.dataset.tab === state.activeTab));
  document.querySelectorAll('.panel[data-panel]').forEach(panel => panel.classList.toggle('hidden', panel.dataset.panel !== state.activeTab));
}
