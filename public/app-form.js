const drop = $('dropzone');
const fileInput = $('examPdf');
const fileList = $('fileChip');
const MAX_PDF_BYTES = 4000000;
const MAX_EXAM_FILES = 10;

fileInput.multiple = true;
fileList.className = 'file-list hidden';
fileList.replaceChildren();
const dropNote = drop.querySelector('.small-note');
if (dropNote) dropNote.textContent = 'Arraste ou selecione até 10 PDFs, com no máximo 4 MB cada. Os arquivos ficarão privados no Supabase.';

['dragenter', 'dragover'].forEach(eventName => {
  drop.addEventListener(eventName, event => {
    event.preventDefault();
    drop.classList.add('drag');
  });
});
['dragleave', 'drop'].forEach(eventName => {
  drop.addEventListener(eventName, event => {
    event.preventDefault();
    drop.classList.remove('drag');
  });
});

drop.addEventListener('drop', event => addFiles([...event.dataTransfer.files]));
fileInput.addEventListener('change', () => {
  addFiles([...fileInput.files]);
  fileInput.value = '';
});

function addFiles(files) {
  for (const file of files) {
    if (state.selectedFiles.length >= MAX_EXAM_FILES) {
      notify(`Limite de ${MAX_EXAM_FILES} PDFs por atendimento.`);
      break;
    }
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      notify(`${file.name}: selecione apenas PDF.`);
      continue;
    }
    if (file.size > MAX_PDF_BYTES) {
      notify(`${file.name}: cada PDF deve ter no máximo 4 MB.`);
      continue;
    }
    const duplicate = state.selectedFiles.some(item => item.name === file.name && item.size === file.size && item.lastModified === file.lastModified);
    if (!duplicate) state.selectedFiles.push(file);
  }
  renderSelectedFiles();
}

function renderSelectedFiles() {
  fileList.replaceChildren();
  fileList.classList.toggle('hidden', !state.selectedFiles.length);
  state.selectedFiles.forEach((file, index) => {
    const row = document.createElement('div');
    row.className = 'file-chip';
    const info = document.createElement('div');
    info.style.minWidth = '0';
    info.append(text('strong', file.name));
    info.append(text('span', formatBytes(file.size)));
    const remove = document.createElement('button');
    remove.className = 'icon-btn';
    remove.type = 'button';
    remove.textContent = 'Remover';
    remove.onclick = () => {
      state.selectedFiles.splice(index, 1);
      renderSelectedFiles();
    };
    row.append(info, remove);
    fileList.append(row);
  });
}

$('attendanceForm').addEventListener('reset', () => setTimeout(() => {
  state.selectedFiles = [];
  fileInput.value = '';
  renderSelectedFiles();
}, 0));

async function uploadExam(jobId, file, index, total) {
  $('processingOverlay').classList.remove('hidden');
  $('processingTitle').textContent = `Enviando exame ${index + 1} de ${total}`;
  $('processingText').textContent = file.name;
  $('processingProgress').style.width = `${Math.round(index / total * 100)}%`;
  const updated = await api(`/api/atendimentos/${encodeURIComponent(jobId)}/exames/upload?filename=${encodeURIComponent(file.name)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/pdf' },
    body: file,
  });
  $('processingProgress').style.width = `${Math.round((index + 1) / total * 100)}%`;
  return updated;
}

$('attendanceForm').addEventListener('submit', async event => {
  event.preventDefault();
  const button = $('submitAttendance');
  button.disabled = true;
  let job = null;
  const payload = {
    nome: $('nome').value,
    idade: Number($('idade').value),
    peso_kg: Number($('peso').value),
    altura_m: Number($('altura').value),
    sexo: $('sexo').value,
    profissao: $('profissao').value,
    objetivo: $('objetivo').value,
    objetivo_descricao: $('descricao').value,
    condicoes: splitList('condicoes'),
    doencas_cronicas: splitList('condicoes'),
    medicamentos: splitList('medicamentos'),
    alergias: splitList('alergias'),
    cirurgias: splitList('cirurgias'),
    historico_familiar: splitList('historicoFamiliar'),
    sono_horas: Number($('sono').value || 0),
    estresse_nivel: $('estresse').value,
    agua_litros: Number($('agua').value || 0),
    frequencia_treino: Number($('frequenciaTreino').value || 0),
    tipo_treino: $('tipoTreino').value,
    nivel_treino: $('nivelTreino').value,
    local_treino: $('localTreino').value,
    restricoes_alimentares: splitList('restricoes'),
    suplementos_atuais: splitList('suplementos'),
    exames_texto: $('exames').value,
    obs: $('obs').value,
  };
  const files = [...state.selectedFiles];
  try {
    job = await api('/api/atendimentos', { method: 'POST', body: JSON.stringify(payload) });
    if (files.length) {
      state.processing = true;
      for (let index = 0; index < files.length; index += 1) job = await uploadExam(job.id, files[index], index, files.length);
      state.processing = false;
      hideProcessing();
    }
    notify(`${files.length || 'Nenhum'} PDF${files.length === 1 ? '' : 's'} registrado${files.length === 1 ? '' : 's'}. Iniciando os agentes.`);
    event.target.reset();
    await loadJobs(false);
    await loadDetail(job.id, false);
    await runAllAgents(job.id);
  } catch (error) {
    state.processing = false;
    hideProcessing();
    if (job) {
      await loadJobs(false);
      await loadDetail(job.id, false);
      notify(`Atendimento criado, mas houve um problema: ${error.message}`);
    } else notify(error.message);
  } finally {
    button.disabled = false;
  }
});
