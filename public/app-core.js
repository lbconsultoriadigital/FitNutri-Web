const STAGES = [
  { key: 'triagem', label: 'Triagem', detail: 'Anamnese estruturada' },
  { key: 'exames', label: 'Exames', detail: 'Marcadores laboratoriais' },
  { key: 'suplementacao', label: 'Suplementos', detail: 'Protocolo e interações' },
  { key: 'nutricao', label: 'Nutrição', detail: 'Plano alimentar' },
  { key: 'treino', label: 'Treino', detail: 'Estratégia física' },
  { key: 'consolidacao', label: 'Consolidação', detail: 'Laudo integrado' },
];

const STATUS = {
  queued: 'Na fila',
  running: 'Em processamento',
  review_required: 'Aguardando revisão',
  approved: 'Aprovado',
  failed: 'Falhou',
  cancelled: 'Cancelado',
};

const state = {
  csrf: null,
  selectedId: null,
  poll: null,
  processing: false,
  jobs: [],
  selectedFiles: [],
  currentJob: null,
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

async function checkSession() {
  const session = await api('/api/session');
  if (session.authenticated) {
    state.csrf = session.csrf_token;
    $('loginPanel').classList.add('hidden');
    await boot();
  } else $('loginPanel').classList.remove('hidden');
}

async function boot() {
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
  $('nome').focus();
  $('nome').scrollIntoView({ behavior: 'smooth', block: 'center' });
};

document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => selectTab(button.dataset.tab)));

function selectTab(name) {
  state.activeTab = name;
  document.querySelectorAll('.tab').forEach(button => button.classList.toggle('active', button.dataset.tab === name));
  ['Overview', 'Outputs', 'Report', 'Pdf'].forEach(key => $(`panel${key}`).classList.toggle('hidden', key.toLowerCase() !== name));
}
