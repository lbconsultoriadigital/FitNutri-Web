const STAGES=[
  {key:'triagem',label:'Triagem',detail:'Anamnese estruturada'},
  {key:'exames',label:'Exames',detail:'Marcadores laboratoriais'},
  {key:'suplementacao',label:'Suplementos',detail:'Protocolo e interações'},
  {key:'nutricao',label:'Nutrição',detail:'Plano alimentar'},
  {key:'treino',label:'Treino',detail:'Estratégia física'},
  {key:'consolidacao',label:'Consolidação',detail:'Laudo integrado'}
];
const STATUS={queued:'Na fila',running:'Em processamento',review_required:'Aguardando revisão',approved:'Aprovado',failed:'Falhou',cancelled:'Cancelado'};
const state={csrf:null,selectedId:null,poll:null,processing:false,jobs:[],selectedFiles:[],currentJob:null};
const $=id=>document.getElementById(id);
const splitList=id=>$(id).value.split(',').map(v=>v.trim()).filter(Boolean);
const formatBytes=n=>!n?'—':n<1024?`${n} B`:n<1048576?`${(n/1024).toFixed(1)} KB`:`${(n/1048576).toFixed(1)} MB`;
const dateText=value=>value?new Date(value).toLocaleString('pt-BR'):'—';
function notify(message){const el=$('flash');el.textContent=message;el.classList.remove('hidden');clearTimeout(el._t);el._t=setTimeout(()=>el.classList.add('hidden'),5200)}
function setBadge(el,status){el.className=`badge ${status||''}`;el.textContent=STATUS[status]||String(status||'Aguardando')}
function text(tag,value,className=''){const el=document.createElement(tag);el.textContent=value;if(className)el.className=className;return el}
async function api(path,options={}){const headers=new Headers(options.headers||{});const method=(options.method||'GET').toUpperCase();if(options.body&&!(options.body instanceof FormData)&&!headers.has('Content-Type'))headers.set('Content-Type','application/json');if(state.csrf&&['POST','PUT','PATCH','DELETE'].includes(method))headers.set('X-CSRF-Token',state.csrf);let res;try{res=await fetch(path,{...options,headers,credentials:'same-origin'})}catch(err){throw new Error('Falha de conexão com o servidor. Verifique a internet e tente novamente.')}const type=res.headers.get('content-type')||'';let data;try{data=type.includes('json')?await res.json():await res.text()}catch{data={}}if(!res.ok)throw new Error(data.detail||data||`HTTP ${res.status}`);return data}

async function checkSession(){const session=await api('/api/session');if(session.authenticated){state.csrf=session.csrf_token;$('loginPanel').classList.add('hidden');await boot()}else $('loginPanel').classList.remove('hidden')}
async function boot(){await health();await loadJobs();if(state.poll)clearInterval(state.poll);state.poll=setInterval(async()=>{if(state.processing)return;await loadJobs(false);if(state.selectedId)await loadDetail(state.selectedId,false)},5000)}
async function health(){try{const h=await api('/api/health');const el=$('health');el.classList.toggle('ok',h.status==='operational');el.querySelector('span:last-child').textContent=h.status==='operational'?`Operacional · ${h.processing_mode}`:'Configuração incompleta'}catch{$('health').querySelector('span:last-child').textContent='API indisponível'}}

$('loginForm').addEventListener('submit',async e=>{e.preventDefault();$('loginError').textContent='';try{const d=await api('/api/login',{method:'POST',body:JSON.stringify({password:$('password').value})});state.csrf=d.csrf_token;$('loginPanel').classList.add('hidden');$('password').value='';await boot()}catch(err){$('loginError').textContent=err.message}})
$('logout').onclick=async()=>{try{await api('/api/logout',{method:'POST',body:'{}'})}finally{state.csrf=null;location.reload()}}
$('refresh').onclick=()=>loadJobs();
$('newAttendanceHero').onclick=()=>{$('nome').focus();$('nome').scrollIntoView({behavior:'smooth',block:'center'})};

document.querySelectorAll('.tab').forEach(btn=>btn.addEventListener('click',()=>selectTab(btn.dataset.tab)));
function selectTab(name){document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));['Overview','Outputs','Report','Pdf'].forEach(key=>$(`panel${key}`).classList.toggle('hidden',key.toLowerCase()!==name))}
