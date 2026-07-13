const FIELD_LABELS = {
  nome: 'Nome', idade: 'Idade', peso_kg: 'Peso', altura_m: 'Altura', sexo: 'Sexo',
  profissao: 'Profissão', imc: 'IMC', objetivo: 'Objetivo', objetivo_descricao: 'Meta e contexto',
  doencas_cronicas: 'Doenças crônicas', cirurgias: 'Cirurgias', medicamentos: 'Medicamentos',
  alergias: 'Alergias', condicoes_especificas: 'Condições específicas', historico_familiar: 'Histórico familiar',
  sono_horas: 'Sono', sono_qualidade: 'Qualidade do sono', estresse_nivel: 'Estresse',
  cafeina_diaria: 'Cafeína', agua_litros: 'Água', alcool: 'Álcool', fumante: 'Fumante',
  frequencia_semanal: 'Frequência semanal', tipo_treino: 'Modalidade', tempo_pratica: 'Nível',
  local_treino: 'Local de treino', lesoes_atuais: 'Lesões', limitacoes: 'Limitações',
  tmb_kcal: 'TMB', get_kcal: 'GET', ajuste_kcal: 'Meta calórica', proteinas_g: 'Proteínas',
  carboidratos_g: 'Carboidratos', gorduras_g: 'Gorduras', fibras_g: 'Fibras', meta_hidrica_l: 'Meta hídrica',
  estrutura: 'Estrutura', aquecimento: 'Aquecimento',
};

function renderExamFiles(job, root, primary = false) {
  const files = job.exam_files || [];
  if (!files.length) {
    root.append(text('div', 'Nenhum PDF de exames foi anexado a este atendimento.', 'notice'));
    return;
  }
  files.forEach((item, index) => {
    const pdf = document.createElement('div');
    pdf.className = 'pdf-meta';
    pdf.append(text('div', String(index + 1).padStart(2, '0'), 'pdf-icon'));
    const info = document.createElement('div');
    info.className = 'pdf-info';
    info.append(text('strong', item.name || `Exame ${index + 1}.pdf`));
    info.append(text('span', `${formatBytes(item.size)} · ${item.page_count || 0} páginas · ${item.text_length || 0} caracteres extraídos`));
    pdf.append(info);
    const open = document.createElement('button');
    open.className = primary ? 'btn btn-primary' : 'btn btn-soft';
    open.type = 'button';
    open.textContent = 'Abrir';
    open.onclick = () => window.open(`/api/atendimentos/${encodeURIComponent(job.id)}/exames/${encodeURIComponent(item.id)}`, '_blank', 'noopener');
    pdf.append(open);
    root.append(pdf);
    if (item.warning) root.append(text('div', item.warning, 'notice'));
  });
}

function renderOverview(job) {
  const root = $('panelOverview');
  root.replaceChildren();
  if (job.error_message) root.append(text('div', job.error_message, 'notice error'));
  if (job.status === 'review_required') root.append(text('div', 'Os seis agentes concluíram o processamento. O laudo permanece como rascunho até revisão e assinatura profissional.', 'notice'));
  if (job.status === 'approved') root.append(text('div', `Aprovado por ${job.reviewer_name} — ${job.registration_type} ${job.registration_number}.`, 'notice success'));

  const summary = document.createElement('div');
  summary.className = 'panel-card';
  summary.append(text('h4', 'Resumo operacional'));
  summary.append(text('p', `${job.current_stage} de 6 agentes concluídos. ${job.exam_file_count || 0} PDF(s) de exames. Status atual: ${STATUS[job.status] || job.status}.`));
  root.append(summary);

  const shortcuts = document.createElement('div');
  shortcuts.className = 'agent-shortcuts';
  STAGES.forEach((stage, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `agent-shortcut${index + 1 <= job.current_stage ? ' complete' : ''}`;
    button.append(text('strong', stage.label));
    button.append(text('span', index + 1 <= job.current_stage ? 'Abrir resultado' : 'Aguardando processamento'));
    button.onclick = () => selectTab(stage.key);
    button.disabled = index + 1 > job.current_stage;
    shortcuts.append(button);
  });
  root.append(shortcuts);

  if (job.has_exam_pdf) renderExamFiles(job, root);
  if (job.status === 'review_required') root.append(approvalForm(job.id));
}

function approvalForm(id) {
  const form = document.createElement('form');
  form.className = 'approval';
  form.append(text('h3', 'Aprovação profissional'));
  const grid = document.createElement('div');
  grid.className = 'field-grid';

  const reviewerField = document.createElement('div');
  reviewerField.className = 'field';
  const reviewerLabel = document.createElement('label');
  reviewerLabel.textContent = 'Nome do revisor';
  const reviewer = document.createElement('input');
  reviewer.required = true;
  reviewer.value = state.approvalDraft.reviewer;
  reviewer.addEventListener('input', () => { state.approvalDraft.reviewer = reviewer.value; });
  reviewerField.append(reviewerLabel, reviewer);

  const numberField = document.createElement('div');
  numberField.className = 'field';
  const numberLabel = document.createElement('label');
  numberLabel.textContent = 'Número do registro';
  const regNumber = document.createElement('input');
  regNumber.required = true;
  regNumber.value = state.approvalDraft.regNumber;
  regNumber.addEventListener('input', () => { state.approvalDraft.regNumber = regNumber.value; });
  numberField.append(numberLabel, regNumber);

  const typeField = document.createElement('div');
  typeField.className = 'field full';
  const typeLabel = document.createElement('label');
  typeLabel.textContent = 'Conselho profissional';
  const regType = document.createElement('select');
  ['CRM', 'CRN', 'CREF', 'outro'].forEach(value => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    regType.append(option);
  });
  regType.value = state.approvalDraft.regType;
  regType.addEventListener('change', () => { state.approvalDraft.regType = regType.value; });
  typeField.append(typeLabel, regType);

  const notesField = document.createElement('div');
  notesField.className = 'field full';
  const notesLabel = document.createElement('label');
  notesLabel.textContent = 'Notas da revisão';
  const notes = document.createElement('textarea');
  notes.value = state.approvalDraft.notes;
  notes.addEventListener('input', () => { state.approvalDraft.notes = notes.value; });
  notesField.append(notesLabel, notes);

  grid.append(reviewerField, numberField, typeField, notesField);
  form.append(grid);

  const actions = document.createElement('div');
  actions.className = 'submit-row';
  const approve = document.createElement('button');
  approve.className = 'btn btn-primary';
  approve.type = 'submit';
  approve.textContent = 'Aprovar e assinar';
  const fillTest = document.createElement('button');
  fillTest.className = 'btn btn-soft';
  fillTest.type = 'button';
  fillTest.textContent = 'Preencher teste';
  fillTest.onclick = () => {
    reviewer.value = 'Usuário de Teste';
    regNumber.value = 'TESTE-001';
    regType.value = 'outro';
    notes.value = 'Aprovação fictícia para validação do protótipo.';
    state.approvalDraft = { reviewer: reviewer.value, regNumber: regNumber.value, regType: regType.value, notes: notes.value };
  };
  actions.append(approve, fillTest);
  form.append(actions);

  form.onsubmit = async event => {
    event.preventDefault();
    approve.disabled = true;
    fillTest.disabled = true;
    state.processing = true;
    try {
      const payload = { reviewer_name: reviewer.value, registration_type: regType.value, registration_number: regNumber.value, notes: notes.value };
      const updated = await api(`/api/atendimentos/${encodeURIComponent(id)}/approve`, { method: 'POST', body: JSON.stringify(payload) });
      state.approvalDraft = { reviewer: '', regNumber: '', regType: 'CRM', notes: '' };
      state.currentJob = updated;
      notify('Laudo aprovado e registrado.');
      renderDetail(updated);
      await loadJobs(false);
    } catch (error) {
      notify(error.message);
    } finally {
      state.processing = false;
      approve.disabled = false;
      fillTest.disabled = false;
    }
  };
  return form;
}

function renderSpecialtyPanels(job) {
  const outputs = job.agent_outputs || {};
  STAGES.forEach((stage, index) => {
    const root = $(`panel${stage.key.charAt(0).toUpperCase()}${stage.key.slice(1)}`);
    if (!root) return;
    root.replaceChildren();

    const header = document.createElement('section');
    header.className = 'specialty-header';
    const number = text('div', String(index + 1).padStart(2, '0'), 'specialty-number');
    const copy = document.createElement('div');
    copy.append(text('div', `Agente ${index + 1}`, 'eyebrow'));
    copy.append(text('h3', stage.label));
    copy.append(text('p', stage.detail));
    const badge = document.createElement('span');
    badge.className = `badge ${outputs[stage.key] ? 'approved' : ''}`;
    badge.textContent = outputs[stage.key] ? 'Concluído' : 'Aguardando';
    header.append(number, copy, badge);
    root.append(header);

    const output = outputs[stage.key];
    if (!output) {
      root.append(text('div', 'O resultado deste agente será exibido aqui quando a etapa for concluída.', 'notice'));
      return;
    }

    if (stage.key === 'triagem') renderTriagem(output, root);
    else if (stage.key === 'exames') renderExames(output, root);
    else if (stage.key === 'suplementacao') renderSuplementacao(output, root);
    else if (stage.key === 'nutricao') renderNutricao(output, root);
    else if (stage.key === 'treino') renderTreino(output, root);
    else if (stage.key === 'consolidacao') renderConsolidacao(output, root);
    else renderGeneric(output, root);

    const technical = document.createElement('details');
    technical.className = 'technical-json';
    const summary = document.createElement('summary');
    summary.textContent = 'Ver JSON técnico';
    const pre = document.createElement('pre');
    pre.textContent = JSON.stringify(output, null, 2);
    technical.append(summary, pre);
    root.append(technical);
  });
}

function renderTriagem(data, root) {
  appendObjectSection(root, 'Dados pessoais', data.dados_pessoais || {});
  appendObjectSection(root, 'Histórico de saúde', data.historico_saude || {});
  appendObjectSection(root, 'Hábitos', data.habitos || {});
  appendObjectSection(root, 'Treino atual', data.treino || {});
  appendListSection(root, 'Preferências alimentares', data.preferencias_alimentares);
  appendListSection(root, 'Restrições alimentares', data.restricoes_alimentares);
  appendListSection(root, 'Suplementos atuais', data.suplementos_atuais);
}

function renderExames(data, root) {
  const markers = data.marcadores || [];
  if (markers.length) appendTable(root, 'Marcadores laboratoriais', ['nome', 'valor', 'referencia', 'status', 'conduta'], markers);
  else root.append(text('div', 'Nenhum marcador laboratorial estruturado foi identificado.', 'notice'));
  appendListSection(root, 'Alertas críticos', data.alertas_criticos, 'error');
  appendTextSection(root, 'Parecer clínico', data.parecer_medico);
}

function renderSuplementacao(data, root) {
  const supplements = data.suplementos || [];
  const section = createSection('Protocolo de suplementação');
  if (!supplements.length) section.append(text('p', 'Nenhum suplemento recomendado.', 'muted-copy'));
  supplements.forEach(item => {
    const card = document.createElement('article');
    card.className = 'protocol-card';
    card.append(text('h4', item.nome || 'Suplemento'));
    const grid = document.createElement('div');
    grid.className = 'data-grid';
    appendDataItem(grid, 'Dosagem', item.dosagem);
    appendDataItem(grid, 'Posologia', item.posologia);
    appendDataItem(grid, 'Duração', item.duracao);
    card.append(grid);
    if (item.justificativa) card.append(text('p', item.justificativa));
    if (item.evidencias) card.append(text('small', `Evidências: ${item.evidencias}`));
    section.append(card);
  });
  root.append(section);
  appendListSection(root, 'Interações', data.interacoes, 'warning');
  appendListSection(root, 'Contraindicações', data.contraindicacoes, 'error');
  appendTextSection(root, 'Observações gerais', data.observacoes_gerais);
}

function renderNutricao(data, root) {
  const metrics = createSection('Cálculos e metas nutricionais');
  const grid = document.createElement('div');
  grid.className = 'nutrition-metrics';
  [
    ['TMB', formatUnit(data.tmb_kcal, 'kcal')],
    ['GET', formatUnit(data.get_kcal, 'kcal')],
    ['Meta calórica', formatUnit(data.ajuste_kcal, 'kcal')],
    ['Proteínas', formatUnit(data.proteinas_g, 'g')],
    ['Carboidratos', formatUnit(data.carboidratos_g, 'g')],
    ['Gorduras', formatUnit(data.gorduras_g, 'g')],
    ['Fibras', formatUnit(data.fibras_g, 'g')],
    ['Meta hídrica', formatUnit(data.meta_hidrica_l, 'L')],
  ].forEach(([label, value]) => grid.append(metricTile(label, value)));
  metrics.append(grid);
  root.append(metrics);

  const meals = data.refeicoes || [];
  const mealSection = createSection('Estrutura do cardápio');
  if (!meals.length) mealSection.append(text('p', 'Nenhuma refeição estruturada.', 'muted-copy'));
  meals.forEach(meal => {
    const card = document.createElement('article');
    card.className = 'meal-card';
    const head = document.createElement('div');
    head.className = 'meal-head';
    head.append(text('h4', meal.nome || 'Refeição'));
    head.append(text('span', meal.horario || 'Horário flexível'));
    card.append(head);
    appendList(card, meal.alimentos || []);
    if (meal.observacoes) card.append(text('p', meal.observacoes, 'meal-note'));
    mealSection.append(card);
  });
  root.append(mealSection);
  appendTextSection(root, 'Observações gerais', data.observacoes_gerais);
}

function renderTreino(data, root) {
  appendObjectSection(root, 'Estratégia de treino', {
    frequencia_semanal: data.frequencia_semanal,
    estrutura: data.estrutura,
    aquecimento: data.aquecimento,
  });
  const section = createSection('Periodização semanal');
  const days = data.dias_treino || [];
  if (!days.length) section.append(text('p', 'Nenhum dia de treino estruturado.', 'muted-copy'));
  days.forEach(day => {
    const card = document.createElement('article');
    card.className = 'training-day';
    card.append(text('div', day.dia || 'Dia de treino', 'training-day-name'));
    card.append(text('h4', day.foco || 'Foco'));
    appendList(card, day.exercicios || []);
    section.append(card);
  });
  root.append(section);
  appendListSection(root, 'Observações', data.observacoes);
}

function renderConsolidacao(data, root) {
  appendTextSection(root, 'Sumário executivo', data.sumario_executivo);
  appendListSection(root, 'Recomendações gerais', data.recomendacoes_gerais);
  appendListSection(root, 'Próximos passos', data.proximos_passos, 'success');
  root.append(text('div', 'Os detalhes técnicos de anamnese, exames, suplementação, nutrição e treino permanecem disponíveis nas respectivas abas.', 'notice success'));
}

function renderGeneric(data, root) {
  appendObjectSection(root, 'Resultado estruturado', data);
}

function appendObjectSection(root, title, object) {
  if (!object || typeof object !== 'object') return;
  const section = createSection(title);
  const grid = document.createElement('div');
  grid.className = 'data-grid';
  Object.entries(object).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      const item = document.createElement('div');
      item.className = 'data-item wide';
      item.append(text('span', labelFor(key)));
      if (value.length) appendList(item, value.map(entry => typeof entry === 'object' ? JSON.stringify(entry) : entry));
      else item.append(text('strong', 'Não informado'));
      grid.append(item);
    } else if (value && typeof value === 'object') {
      const item = document.createElement('div');
      item.className = 'data-item wide nested-data';
      item.append(text('span', labelFor(key)));
      const inner = document.createElement('div');
      inner.className = 'data-grid';
      Object.entries(value).forEach(([innerKey, innerValue]) => appendDataItem(inner, labelFor(innerKey), displayValue(innerKey, innerValue)));
      item.append(inner);
      grid.append(item);
    } else appendDataItem(grid, labelFor(key), displayValue(key, value));
  });
  section.append(grid);
  root.append(section);
}

function appendTable(root, title, keys, rows) {
  const section = createSection(title);
  const wrap = document.createElement('div');
  wrap.className = 'table-wrap';
  const table = document.createElement('table');
  table.className = 'clinical-table';
  const thead = document.createElement('thead');
  const header = document.createElement('tr');
  keys.forEach(key => header.append(text('th', labelFor(key))));
  thead.append(header);
  const tbody = document.createElement('tbody');
  rows.forEach(row => {
    const tr = document.createElement('tr');
    keys.forEach(key => {
      const td = text('td', displayValue(key, row[key]));
      if (key === 'status') td.className = `status-cell ${String(row[key] || '').toLowerCase()}`;
      tr.append(td);
    });
    tbody.append(tr);
  });
  table.append(thead, tbody);
  wrap.append(table);
  section.append(wrap);
  root.append(section);
}

function appendListSection(root, title, values, tone = '') {
  if (!Array.isArray(values) || !values.length) return;
  const section = createSection(title);
  if (tone) section.classList.add(`section-${tone}`);
  appendList(section, values);
  root.append(section);
}

function appendTextSection(root, title, value) {
  if (!value) return;
  const section = createSection(title);
  section.append(text('p', String(value), 'reading-copy'));
  root.append(section);
}

function appendList(root, values) {
  const list = document.createElement('ul');
  list.className = 'readable-list';
  values.forEach(value => list.append(text('li', String(value))));
  root.append(list);
}

function createSection(title) {
  const section = document.createElement('section');
  section.className = 'specialty-section';
  section.append(text('h3', title));
  return section;
}

function appendDataItem(root, label, value) {
  const item = document.createElement('div');
  item.className = 'data-item';
  item.append(text('span', label));
  item.append(text('strong', value === '' || value === null || value === undefined ? 'Não informado' : String(value)));
  root.append(item);
}

function metricTile(label, value) {
  const tile = document.createElement('div');
  tile.className = 'nutrition-tile';
  tile.append(text('span', label));
  tile.append(text('strong', value));
  return tile;
}

function displayValue(key, value) {
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não';
  if (value === null || value === undefined || value === '') return 'Não informado';
  if (key === 'peso_kg') return `${value} kg`;
  if (key === 'altura_m') return `${value} m`;
  if (key === 'sono_horas') return `${value} h`;
  if (key === 'agua_litros') return `${value} L`;
  return String(value).replaceAll('_', ' ');
}

function formatUnit(value, unit) {
  return value === null || value === undefined || value === '' ? '—' : `${value} ${unit}`;
}

function labelFor(key) {
  if (FIELD_LABELS[key]) return FIELD_LABELS[key];
  return String(key).replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase());
}

function renderReport(job) {
  const root = $('panelReport');
  root.replaceChildren();
  if (!job.laudo_html) {
    root.append(text('div', 'O laudo integrado será disponibilizado após a conclusão dos seis agentes.', 'notice'));
    return;
  }

  const toolbar = document.createElement('div');
  toolbar.className = 'report-toolbar';
  const copy = document.createElement('div');
  copy.append(text('strong', 'Laudo clínico integrado'));
  copy.append(text('span', job.status === 'approved' ? 'Documento aprovado' : 'Rascunho para revisão profissional'));
  const full = document.createElement('button');
  full.type = 'button';
  full.className = 'btn btn-soft';
  full.textContent = 'Abrir em tela cheia';
  full.onclick = () => {
    const url = URL.createObjectURL(new Blob([job.laudo_html], { type: 'text/html;charset=utf-8' }));
    window.open(url, '_blank', 'noopener');
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  };
  toolbar.append(copy, full);
  root.append(toolbar);

  const frame = document.createElement('iframe');
  frame.className = 'viewer';
  frame.setAttribute('sandbox', '');
  frame.title = `Laudo de ${job.patient_name}`;
  frame.srcdoc = job.laudo_html;
  root.append(frame);
}

function renderPdf(job) {
  const root = $('panelPdf');
  root.replaceChildren();
  renderExamFiles(job, root, true);
}
