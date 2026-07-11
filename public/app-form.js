const drop=$('dropzone'),fileInput=$('examPdf');
['dragenter','dragover'].forEach(evt=>drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.add('drag')}));
['dragleave','drop'].forEach(evt=>drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.remove('drag')}));
drop.addEventListener('drop',e=>{const f=e.dataTransfer.files[0];if(f)chooseFile(f)});fileInput.addEventListener('change',()=>{if(fileInput.files[0])chooseFile(fileInput.files[0])});
$('removeFile').onclick=()=>{state.selectedFile=null;fileInput.value='';$('fileChip').classList.add('hidden')};
function chooseFile(file){if(file.type!=='application/pdf'&&!file.name.toLowerCase().endsWith('.pdf'))return notify('Selecione um arquivo PDF');if(file.size>4000000)return notify('O PDF deve ter no máximo 4 MB');state.selectedFile=file;$('fileName').textContent=file.name;$('fileSize').textContent=formatBytes(file.size);$('fileChip').classList.remove('hidden')}

$('attendanceForm').addEventListener('reset',()=>setTimeout(()=>{$('removeFile').click()},0));
$('attendanceForm').addEventListener('submit',async e=>{
  e.preventDefault();const btn=$('submitAttendance');btn.disabled=true;
  const payload={
    nome:$('nome').value,idade:Number($('idade').value),peso_kg:Number($('peso').value),altura_m:Number($('altura').value),sexo:$('sexo').value,profissao:$('profissao').value,
    objetivo:$('objetivo').value,objetivo_descricao:$('descricao').value,condicoes:splitList('condicoes'),doencas_cronicas:splitList('condicoes'),medicamentos:splitList('medicamentos'),alergias:splitList('alergias'),cirurgias:splitList('cirurgias'),historico_familiar:splitList('historicoFamiliar'),
    sono_horas:Number($('sono').value||0),estresse_nivel:$('estresse').value,agua_litros:Number($('agua').value||0),frequencia_treino:Number($('frequenciaTreino').value||0),tipo_treino:$('tipoTreino').value,nivel_treino:$('nivelTreino').value,local_treino:$('localTreino').value,
    restricoes_alimentares:splitList('restricoes'),suplementos_atuais:splitList('suplementos'),exames_texto:$('exames').value,obs:$('obs').value
  };
  const form=new FormData();form.append('payload',JSON.stringify(payload));if(state.selectedFile)form.append('exame_pdf',state.selectedFile,state.selectedFile.name);
  try{const job=await api('/api/atendimentos',{method:'POST',body:form});notify('Atendimento criado. Iniciando os agentes.');e.target.reset();await loadJobs(false);await loadDetail(job.id,false);await runAllAgents(job.id)}catch(err){notify(err.message)}finally{btn.disabled=false}
});
