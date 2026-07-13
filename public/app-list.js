function updateMetrics(jobs) {
  $('metricTotal').textContent = jobs.length;
  $('metricRunning').textContent = jobs.filter(job => ['queued', 'running'].includes(job.status) && job.current_stage < 6).length;
  $('metricReview').textContent = jobs.filter(job => job.status === 'review_required').length;
  $('metricApproved').textContent = jobs.filter(job => job.status === 'approved').length;
  $('jobCount').textContent = jobs.length;
}

async function loadJobs(showError = true) {
  try {
    const jobs = await api('/api/atendimentos');
    state.jobs = jobs;
    updateMetrics(jobs);
    renderRecentJobs(jobs);
    renderPatientsPage(jobs);
    renderReportsPage(jobs);
  } catch (error) {
    if (showError) notify(error.message);
  }
}

function renderRecentJobs(jobs) {
  const root = $('jobs');
  root.replaceChildren();
  if (!jobs.length) {
    root.append(text('div', 'Nenhum atendimento criado.', 'empty'));
    return;
  }
  jobs.forEach(job => {
    const card = document.createElement('article');
    card.className = `job${job.id === state.selectedId ? ' selected' : ''}`;
    card.tabIndex = 0;
    const top = document.createElement('div');
    top.className = 'job-top';
    top.append(text('div', job.patient_name, 'job-name'));
    const badge = document.createElement('span');
    setBadge(badge, job.status);
    top.append(badge);
    card.append(top);
    const meta = [`Etapa ${job.current_stage}/6`, dateText(job.created_at)];
    if (job.exam_file_count) meta.push(`${job.exam_file_count} PDF${job.exam_file_count === 1 ? '' : 's'}`);
    card.append(text('div', meta.join(' · '), 'job-meta'));
    const progress = document.createElement('div');
    progress.className = 'mini-progress';
    const bar = document.createElement('span');
    bar.style.width = `${Math.round(job.current_stage / 6 * 100)}%`;
    progress.append(bar);
    card.append(progress);
    card.onclick = () => loadDetail(job.id);
    card.onkeydown = event => { if (event.key === 'Enter') loadDetail(job.id); };
    root.append(card);
  });
}

function groupPatients(jobs) {
  const groups = new Map();
  jobs.forEach(job => {
    const key = String(job.patient_name || '').trim().toLocaleLowerCase('pt-BR');
    if (!groups.has(key)) groups.set(key, { name: job.patient_name, jobs: [] });
    groups.get(key).jobs.push(job);
  });
  return [...groups.values()].map(group => {
    group.jobs.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    return { ...group, latest: group.jobs[0] };
  });
}

function renderPatientsPage(jobs) {
  const root = $('patientsGrid');
  if (!root) return;
  root.replaceChildren();
  const query = ($('patientSearch')?.value || '').trim().toLocaleLowerCase('pt-BR');
  const patients = groupPatients(jobs).filter(patient => patient.name.toLocaleLowerCase('pt-BR').includes(query));
  if (!patients.length) {
    root.append(text('div', query ? 'Nenhum paciente corresponde à busca.' : 'Nenhum paciente cadastrado.', 'empty'));
    return;
  }

  patients.forEach(patient => {
    const card = document.createElement('article');
    card.className = 'patient-card';
    const header = document.createElement('div');
    header.className = 'patient-head';
    const avatar = text('div', patient.name.trim().charAt(0).toUpperCase() || 'P', 'patient-avatar');
    const copy = document.createElement('div');
    copy.append(text('h3', patient.name));
    copy.append(text('p', `${patient.jobs.length} atendimento${patient.jobs.length === 1 ? '' : 's'} · último em ${dateText(patient.latest.created_at)}`));
    header.append(avatar, copy);
    const badge = document.createElement('span');
    setBadge(badge, patient.latest.status);
    header.append(badge);
    card.append(header);

    const stats = document.createElement('div');
    stats.className = 'patient-stats';
    stats.append(metricMini('Etapa atual', `${patient.latest.current_stage}/6`));
    stats.append(metricMini('Exames', String(patient.jobs.reduce((sum, job) => sum + (job.exam_file_count || 0), 0))));
    stats.append(metricMini('Laudos', String(patient.jobs.filter(job => job.current_stage >= 6).length)));
    card.append(stats);

    const actions = document.createElement('div');
    actions.className = 'card-actions';
    actions.append(actionButton('Abrir atendimento', () => openJobFromView(patient.latest.id, 'overview'), 'btn btn-primary'));
    if (patient.latest.current_stage >= 6) actions.append(actionButton('Ver laudo', () => openJobFromView(patient.latest.id, 'report'), 'btn btn-soft'));
    card.append(actions);
    root.append(card);
  });
}

function renderReportsPage(jobs) {
  const root = $('reportsGrid');
  const metricRoot = $('reportMetrics');
  if (!root || !metricRoot) return;
  root.replaceChildren();
  metricRoot.replaceChildren();

  const reports = jobs.filter(job => job.current_stage >= 6 || ['review_required', 'approved'].includes(job.status));
  const query = ($('reportSearch')?.value || '').trim().toLocaleLowerCase('pt-BR');
  const filtered = reports.filter(job => `${job.patient_name} ${STATUS[job.status] || job.status}`.toLocaleLowerCase('pt-BR').includes(query));

  metricRoot.append(reportMetric('Total de laudos', reports.length));
  metricRoot.append(reportMetric('Aguardando revisão', reports.filter(job => job.status === 'review_required').length));
  metricRoot.append(reportMetric('Aprovados', reports.filter(job => job.status === 'approved').length));

  if (!filtered.length) {
    root.append(text('div', query ? 'Nenhum laudo corresponde à busca.' : 'Nenhum laudo foi gerado ainda.', 'empty'));
    return;
  }

  filtered.forEach(job => {
    const card = document.createElement('article');
    card.className = 'report-card';
    const top = document.createElement('div');
    top.className = 'report-card-top';
    const copy = document.createElement('div');
    copy.append(text('div', job.patient_name, 'report-name'));
    copy.append(text('div', `Gerado em ${dateText(job.updated_at || job.created_at)}`, 'report-meta'));
    const badge = document.createElement('span');
    setBadge(badge, job.status);
    top.append(copy, badge);
    card.append(top);

    const details = document.createElement('div');
    details.className = 'report-details';
    details.append(metricMini('Etapas', `${job.current_stage}/6`));
    details.append(metricMini('PDFs', String(job.exam_file_count || 0)));
    details.append(metricMini('Responsável', job.reviewer_name || 'Pendente'));
    card.append(details);

    const actions = document.createElement('div');
    actions.className = 'card-actions';
    actions.append(actionButton('Abrir laudo', () => openJobFromView(job.id, 'report'), 'btn btn-primary'));
    actions.append(actionButton(job.status === 'review_required' ? 'Revisar' : 'Ver atendimento', () => openJobFromView(job.id, 'overview'), 'btn btn-soft'));
    card.append(actions);
    root.append(card);
  });
}

function metricMini(label, value) {
  const item = document.createElement('div');
  item.className = 'mini-stat';
  item.append(text('span', label));
  item.append(text('strong', value));
  return item;
}

function reportMetric(label, value) {
  const article = document.createElement('article');
  article.className = 'metric report-metric';
  article.append(text('div', label, 'metric-label'));
  article.append(text('div', String(value), 'metric-value'));
  article.append(text('div', '', 'metric-accent'));
  return article;
}

function actionButton(label, onClick, className) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = className;
  button.textContent = label;
  button.onclick = onClick;
  return button;
}

async function loadDetail(id, showError = true, options = {}) {
  const scrollY = window.scrollY;
  try {
    state.selectedId = id;
    const job = await api(`/api/atendimentos/${encodeURIComponent(id)}`);
    state.currentJob = job;
    renderDetail(job);
    renderRecentJobs(state.jobs);
    if (options.preserveScroll) requestAnimationFrame(() => window.scrollTo({ top: scrollY, behavior: 'auto' }));
    return job;
  } catch (error) {
    if (showError) notify(error.message);
    return null;
  }
}

function renderDetail(job) {
  $('detailEmpty').classList.add('hidden');
  $('detailContent').classList.remove('hidden');
  $('detailName').textContent = job.patient_name;
  $('detailMeta').textContent = `${job.slug} · criado em ${dateText(job.created_at)}`;
  setBadge($('detailStatus'), job.status);
  $('detailProgress').style.width = `${Math.round(job.current_stage / 6 * 100)}%`;
  $('progressText').textContent = `Etapa ${job.current_stage} de 6`;
  $('processingMode').textContent = job.processing_mode === 'manual' ? 'Execução controlada pelo painel' : 'Fila automática QStash';
  renderAgents(job);
  renderOverview(job);
  renderSpecialtyPanels(job);
  renderReport(job);
  renderPdf(job);
  selectTab(state.activeTab);
  const complete = job.current_stage >= 6 || ['review_required', 'approved'].includes(job.status);
  $('runNext').disabled = complete || state.processing;
  $('runAll').disabled = complete || state.processing;
  $('openPdfTop').classList.toggle('hidden', !job.has_exam_pdf);
  $('openPdfTop').textContent = job.exam_file_count > 1 ? `Ver ${job.exam_file_count} PDFs` : 'Abrir PDF';
  $('openPdfTop').onclick = () => selectTab('pdf');
}

function renderAgents(job) {
  const root = $('agentGrid');
  root.replaceChildren();
  STAGES.forEach((stage, index) => {
    const number = index + 1;
    const card = document.createElement('button');
    card.type = 'button';
    card.className = `agent${number <= job.current_stage ? ' done' : number === job.current_stage + 1 && ['queued', 'running'].includes(job.status) ? ' active' : ''}`;
    card.append(text('div', number <= job.current_stage ? '✓' : String(number), 'agent-index'));
    card.append(text('div', stage.label, 'agent-label'));
    card.title = `${stage.detail}. Abrir resultado do agente.`;
    card.onclick = () => selectTab(stage.key);
    root.append(card);
  });
}
