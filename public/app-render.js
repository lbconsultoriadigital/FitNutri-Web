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

function renderOutputs(job) {
  const root = $('panelOutputs');
  root.replaceChildren();
  const outputs = job.agent_outputs || {};
  const grid = document.createElement('div');
  grid.className = 'output-grid';
  STAGES.forEach(stage => {
    const wrap = document.createElement('article');
    wrap.className = 'output';
    const head = document.createElement('div');
    head.className = 'output-head';
    head.append(text('span', stage.label));
    head.append(text('span', outputs[stage.key] ? 'Concluído' : 'Aguardando'));
    const pre = document.createElement('pre');
    pre.textContent = outputs[stage.key] ? JSON.stringify(outputs[stage.key], null, 2) : 'Esta saída será preenchida quando o agente concluir a etapa.';
    wrap.append(head, pre);
    grid.append(wrap);
  });
  root.append(grid);
}

function renderReport(job) {
  const root = $('panelReport');
  root.replaceChildren();
  if (!job.laudo_html) {
    root.append(text('div', 'O laudo integrado será disponibilizado após a conclusão dos seis agentes.', 'notice'));
    return;
  }
  const frame = document.createElement('iframe');
  frame.className = 'viewer';
  frame.setAttribute('sandbox', '');
  frame.srcdoc = job.laudo_html;
  root.append(frame);
}

function renderPdf(job) {
  const root = $('panelPdf');
  root.replaceChildren();
  renderExamFiles(job, root, true);
}
