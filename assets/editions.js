const byId = id => document.getElementById(id);
const dateLabel = value => new Intl.DateTimeFormat('pt-BR', {dateStyle:'long',timeZone:'UTC'}).format(new Date(value+'T12:00:00Z'));
export const todaySP = () => new Intl.DateTimeFormat('en-CA',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
export function pastEditions(editions, today=todaySP()) { return editions.filter(e=>e.date<=today).sort((a,b)=>b.date.localeCompare(a.date)||a.id.localeCompare(b.id)); }
function el(tag, cls, text) { const n=document.createElement(tag); if(cls)n.className=cls; if(text)n.textContent=text; return n; }
function link(text,url,cls='edition-link') {const a=el('a',cls,text);a.href=url;return a;}
function photo(media, name, lazy=true) {const img=el('img');img.src=media.src;img.alt=media.alt||`Registro de ${name}`;img.loading=lazy?'lazy':'eager';img.decoding='async';return img;}
function empty(container, text='Em breve, registros das nossas edições') {const box=el('div','edition-empty');box.append(el('p','',text));const a=link('Acompanhe a Aldeia MIX no Instagram','https://www.instagram.com/aldeiamixx/');a.target='_blank';a.rel='noopener noreferrer';box.append(a);container.append(box);}
function enlarge(media, name) {const dialog=el('dialog','lightbox');dialog.setAttribute('aria-label',`Foto de ${name}`);const close=el('button','','Fechar foto ×');close.type='button';close.onclick=()=>dialog.close();dialog.append(close,photo(media,name,false));document.body.append(dialog);dialog.addEventListener('close',()=>dialog.remove());dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});dialog.showModal();close.focus();}
export function carousel(container, photos, name) {
 if(!photos.length)return;
 const root=el('section','carousel');root.setAttribute('aria-label',`Fotos de ${name}`);root.setAttribute('aria-roledescription','carrossel');
 const stage=el('div','carousel-stage'),open=el('button');open.type='button';const image=photo(photos[0],name,false);open.append(image);stage.append(open);root.append(stage);
 let index=0,paused=false,hover=false,focused=false,visible=false,startX=null,timer=null,suppressClick=false;
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 const controls=el('div','carousel-controls'),counter=el('span','carousel-counter');
 const prev=el('button','','← Anterior'),next=el('button','','Próxima →'),pause=el('button','','Pausar');[prev,next,pause].forEach(b=>b.type='button');
 function show(i){index=(i+photos.length)%photos.length;image.src=photos[index].src;image.alt=photos[index].alt||`Registro de ${name}, foto ${index+1}`;counter.textContent=`${index+1} / ${photos.length}`;open.setAttribute('aria-label',`Ampliar foto ${index+1} de ${photos.length}`);}
 function schedule(){clearInterval(timer);timer=null;pause.textContent=paused?'Retomar':'Pausar';pause.setAttribute('aria-pressed',String(paused));pause.hidden=reduced.matches||photos.length<2;if(photos.length>1&&!paused&&!hover&&!focused&&visible&&!document.hidden&&!reduced.matches)timer=setInterval(()=>show(index+1),5000);}
 function move(delta){show(index+delta);paused=true;schedule();}
 prev.onclick=()=>move(-1);next.onclick=()=>move(1);pause.onclick=()=>{paused=!paused;schedule();};open.onclick=()=>{if(suppressClick){suppressClick=false;return;}paused=true;schedule();enlarge(photos[index],name);};
 root.onpointerenter=e=>{if(e.pointerType==='mouse'){hover=true;schedule();}};root.onpointerleave=()=>{hover=false;schedule();};
 root.onfocusin=()=>{focused=true;schedule();};root.onfocusout=()=>queueMicrotask(()=>{focused=root.contains(document.activeElement);schedule();});
 stage.onpointerdown=e=>{startX=e.clientX;suppressClick=false;};stage.onpointerup=e=>{if(startX!==null&&Math.abs(e.clientX-startX)>45){suppressClick=true;move(e.clientX<startX?1:-1);}startX=null;};stage.onpointercancel=()=>{startX=null;};
 root.onkeydown=e=>{if(e.key==='ArrowLeft'){e.preventDefault();move(-1);}if(e.key==='ArrowRight'){e.preventDefault();move(1);}};
 controls.append(counter);if(photos.length>1)controls.append(prev,next,pause);root.append(controls);container.append(root);show(0);
 const observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;schedule();},{threshold:.25});observer.observe(root);
 document.addEventListener('visibilitychange',schedule);reduced.addEventListener('change',schedule);
}
function detail(root, edition) {
 root.append(link('← Todas as edições','edicoes.html','gallery-back'),el('h1','editions-title',edition.name),el('time','edition-date',dateLabel(edition.date)));
 if(edition.description)root.append(el('p','edition-description',edition.description));
 const photos=edition.media.filter(m=>m.type==='image'),videos=edition.media.filter(m=>m.type==='video');
 if(!edition.media.length){empty(root,'As fotos desta edição chegam em breve.');return;}
 carousel(root,photos,edition.name);
 if(photos.length>1){const grid=el('div','photo-grid');photos.forEach((m,i)=>{const b=el('button');b.type='button';b.setAttribute('aria-label',`Ampliar foto ${i+1} de ${edition.name}`);b.append(photo(m,edition.name));b.onclick=()=>enlarge(m,edition.name);grid.append(b);});root.append(grid);}
 if(videos.length){root.append(el('h2','editions-title','Vídeos'));const grid=el('div','video-grid');videos.forEach(m=>{const item=el('div','video-item'),b=el('button','',`Assistir: ${m.name}`);b.type='button';b.onclick=()=>{const frame=el('iframe');frame.src=m.preview;frame.title=`Vídeo de ${edition.name}: ${m.name}`;frame.allow='fullscreen';frame.setAttribute('allowfullscreen','');item.insertBefore(frame,b);b.remove();};const a=link('Abrir vídeo no Google Drive',m.url);a.target='_blank';a.rel='noopener noreferrer';item.append(b,a);grid.append(item);});root.append(grid);}
}
async function init(){const root=byId('editions-root')||byId('latest-edition');if(!root)return;try{
 const response=await fetch('data/editions.json');if(!response.ok)throw Error('catalog');const data=await response.json();const editions=pastEditions(data.editions);
 root.replaceChildren();
 if(root.id==='latest-edition') {if(!editions.length){empty(root);return;}const e=editions[0];root.append(el('h3','editions-title',e.name),el('time','edition-date',dateLabel(e.date)));if(e.description)root.append(el('p','edition-description',e.description));carousel(root,e.media.filter(m=>m.type==='image').slice(0,6),e.name);root.append(link('Ver esta edição',`edicoes.html?id=${encodeURIComponent(e.id)}`));return;}
 const id=new URLSearchParams(location.search).get('id');if(id){const e=editions.find(e=>e.id===id);if(e){document.title=`${e.name} — Aldeia MIX`;detail(root,e);}else{root.append(el('h1','editions-title','Edição não encontrada'),link('Ver todas as edições','edicoes.html'));}return;}
 root.append(el('h1','editions-title','Edições da Aldeia'),el('p','edition-intro','Sabores, encontros e histórias para revisitar. Veja os registros de cada edição.'));
 if(!editions.length){empty(root);return;}const grid=el('div','edition-grid');editions.forEach(e=>{const card=link('',`edicoes.html?id=${encodeURIComponent(e.id)}`,'edition-card');card.append(e.cover?photo(e.cover,e.name):el('div','edition-placeholder','Registros em breve'),el('h2','',e.name),el('time','edition-date',dateLabel(e.date)));grid.append(card);});root.append(grid);
 }catch{root.replaceChildren();empty(root,'Não foi possível carregar as edições agora. Tente novamente em instantes.');}}
if(typeof document!=='undefined')init();
