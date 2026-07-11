const drop=$('dropzone'),fileInput=$('examPdf'),fileList=$('fileChip');
const MAX_PDF_BYTES=6000000,MAX_EXAM_FILES=10;
fileInput.multiple=true;fileList.className='file-list hidden';fileList.replaceChildren();
const dropNote=drop.querySelector('.small-note');if(dropNote)dropNote.textContent='Arraste ou selecione até 10 PDFs, com no máximo 6 MB cada. Os arquivos ficarão privados no Supabase.';
['dragenter','dragover'].forEach(evt=>drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.add('drag')}));
['dragleave','drop'].forEach(evt=>drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.remove('drag')}));
drop.addEventListener('drop',e=>addFiles([...e.dataTransfer.files]));
fileInput.addEventListener('change',()=>{addFiles([...fileInput.files]);fileInput.value=''});

function addFiles(files){
  for(const file of files){
    if(state.selectedFiles.length>=MAX_EXAM_FILES){notify(`Limite de ${MAX_EXAM_FILES} PDFs por atendimento.`);break}
    if(file.type!=='application/pdf'&&!file.name.toLowerCase().endsWith('.pdf')){notify(`${file.name}: selecione apenas PDF.`);continue}
    if(file.size>MAX_PDF_BYTES){notify(`${file.name}: cada PDF deve ter no máximo 6 MB.`);continue}
    const duplicate=state.selectedFiles.some(item=>item.name===file.name&&item.size===file.size&&item.lastModified===file.lastModified);
    if(!duplicate)state.selectedFiles.push(file)
  }
  renderSelectedFiles()
}
function renderSelectedFiles(){
  fileList.replaceChildren();
  fileList.classList.toggle('hidden',!state.selectedFiles.length);
  state.selectedFiles.forEach((file,index)=>{
    const row=document.createElement('div');row.className='file-chip';
    const info=document.createElement('div');info.style.minWidth='0';info.append(text('strong',file.name));info.append(text('span',formatBytes(file.size)));
    const remove=document.createElement('button');remove.className='icon-btn';remove.type='button';remove.textContent='Remover';remove.onclick=()=>{state.selectedFiles.splice(index,1);renderSelectedFiles()};
    row.append(info,remove);fileList.append(row)
  })
}
$('attendanceForm').addEventListener('reset',()=>setTimeout(()=>{state.selectedFiles=[];fileInput.value='';renderSelectedFiles()},0));

async function uploadExam(jobId,file,index,total){
  $('processingOverlay').classList.remove('hidden');
  $('processingTitle').textContent=`Enviando exame ${index+1} de ${total}`;
  $('processingText').textContent=file.name;
  $('processingProgress').style.width=`${Math.round(index/total*100)}%`;
  const ticket=await api(`/api/atendimentos/${encodeURIComponent(jobId)}/exames/presign`,{
    method:'POST',body:JSON.stringify({filename:file.name,size:file.size,content_type:'application/pdf'})
  });
  const body=new FormData();body.append('cacheControl','3600');body.append('',file,file.name);
  let upload;
  try{upload=await fetch(ticket.signed_url,{method:'PUT',headers:{'x-upsert':'false'},body})}
  catch{throw new Error(`Falha ao enviar ${file.name}. Verifique a conexão e tente novamente.`)}
  if(!upload.ok){let detail='';try{detail=await upload.text()}catch{}throw new Error(`Falha ao enviar ${file.name}${detail?`: ${detail.slice(0,120)}`:''}`)}
  const updated=await api(`/api/atendimentos/${encodeURIComponent(jobId)}/exames/finalize`,{
    method:'POST',body:JSON.stringify({file_id:ticket.file_id,filename:file.name,size:file.size})
  });
  $('processingProgress').style.width=`${Math.round((index+1)/total*100)}%`;
  return updated
}

$('attendanceForm').addEventListener('submit',async e=>{
  e.preventDefault();const btn=$('submitAttendance');btn.disabled=true;let job=null;
  const payload={
    nome:$('nome').value,idade:Number($('idade').value),peso_kg:Number($('peso').value),altura_m:Number($('altura').value),sexo:$('sexo').value,profissao:$('profissao').value,
    objetivo:$('objetivo').value,objetivo_descricao:$('descricao').value,condicoes:splitList('condicoes'),doencas_cronicas:splitList('condicoes'),medicamentos:splitList('medicamentos'),alergias:splitList('alergias'),cirurgias:splitList('cirurgias'),historico_familiar:splitList('historicoFamiliar'),
    sono_horas:Number($('sono').value||0),estresse_nivel:$('estresse').value,agua_litros:Number($('agua').value||0),frequencia_treino:Number($('frequenciaTreino').value||0),tipo_treino:$('tipoTreino').value,nivel_treino:$('nivelTreino').value,local_treino:$('localTreino').value,
    restricoes_alimentares:splitList('restricoes'),suplementos_atuais:splitList('suplementos'),exames_texto:$('exames').value,obs:$('obs').value
  };
  const files=[...state.selectedFiles];
  try{
    job=await api('/api/atendimentos',{method:'POST',body:JSON.stringify(payload)});
    if(files.length){state.processing=true;for(let i=0;i<files.length;i++)job=await uploadExam(job.id,files[i],i,files.length);state.processing=false;hideProcessing()}
    notify(`${files.length||'Nenhum'} PDF${files.length===1?'':'s'} registrado${files.length===1?'':'s'}. Iniciando os agentes.`);
    e.target.reset();await loadJobs(false);await loadDetail(job.id,false);await runAllAgents(job.id)
  }catch(err){
    state.processing=false;hideProcessing();
    if(job){await loadJobs(false);await loadDetail(job.id,false);notify(`Atendimento criado, mas houve um problema: ${err.message}`)}else notify(err.message)
  }finally{btn.disabled=false}
});
