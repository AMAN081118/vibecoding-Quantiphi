let projectId, boardData;
const $ = s => document.querySelector(s);
const labels = {todo: 'To-do', in_progress: 'In progress', done: 'Done'};
async function api(url, options = {}) { const res = await fetch(url, {...options, headers: {'Content-Type':'application/json', ...options.headers}}); if (!res.ok) throw new Error((await res.json().catch(()=>({detail:'Something went wrong'}))).detail); return res.status === 204 ? null : res.json(); }
function initials(name) { return name.split(' ').map(x=>x[0]).slice(0,2).join(''); }
function toast(message) { const t = $('#toast'); t.textContent = message; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'), 2600); }
function memberOptions(selected='') { return `<option value="">Unassigned</option>${boardData.members.map(m=>`<option value="${m.id}" ${m.id === selected ? 'selected':''}>${m.name}</option>`).join('')}`; }
function card(task) { return `<article class="card" draggable="true" data-id="${task.id}"><h4>${escapeHtml(task.title)}</h4>${task.description ? `<p class="description">${escapeHtml(task.description)}</p>`:''}<div class="meta"><span class="tag ${task.priority}">${task.priority}</span>${task.due_date ? `<span>Due ${task.due_date}</span>` : ''}${task.assignee ? `<span class="avatar" title="${escapeHtml(task.assignee.name)}">${initials(task.assignee.name)}</span>`:''}</div></article>`; }
function escapeHtml(value) { const node = document.createElement('span'); node.textContent = value; return node.innerHTML; }
function render() {
  $('#project-name').textContent = boardData.project.name;
  const filter = $('#priority-filter').value;
  $('#board').innerHTML = ['todo','in_progress','done'].map(status => { const tasks = boardData.tasks.filter(t=>t.status===status && (filter==='all'||t.priority===filter)); return `<section class="column"><div class="column-head"><h3>${labels[status]}</h3><span class="counter">${tasks.length}</span></div><div class="dropzone" data-status="${status}">${tasks.map(card).join('')}</div></section>`; }).join('');
  $('#members').innerHTML = boardData.members.map(m=>`<div class="member"><span class="avatar ${m.overloaded?'overloaded':''}">${initials(m.name)}</span><div class="member-info"><div class="member-name">${escapeHtml(m.name)}</div><div class="member-sub">${m.role}</div></div><span class="workload">${m.in_progress_count}<br>active</span></div>`).join('');
  wireBoard();
}
function wireBoard() {
  document.querySelectorAll('.card').forEach(c=> { c.addEventListener('dragstart',e=>e.dataTransfer.setData('taskId', c.dataset.id)); c.addEventListener('click',()=>openTask(Number(c.dataset.id))); });
  document.querySelectorAll('.dropzone').forEach(zone=> { zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('over')}); zone.addEventListener('dragleave',()=>zone.classList.remove('over')); zone.addEventListener('drop',async e=> { e.preventDefault(); zone.classList.remove('over'); const task=boardData.tasks.find(t=>t.id===Number(e.dataTransfer.getData('taskId'))); if(task && task.status!==zone.dataset.status) { try { await api(`/api/tasks/${task.id}`,{method:'PATCH',body:JSON.stringify({status:zone.dataset.status})}); await load(); } catch(err) {toast(err.message)} } }); });
}
async function load() { boardData = await api(`/api/projects/${projectId}/board`); render(); }
function openTask(id) { const task = boardData.tasks.find(t=>t.id===id); $('#task-form').reset(); $('#task-id').value = task?.id || ''; $('#task-form-title').textContent = task ? 'Edit task' : 'New task'; $('#title').value=task?.title||''; $('#description').value=task?.description||''; $('#priority').value=task?.priority||'medium'; $('#due-date').value=task?.due_date||''; $('#assignee').innerHTML=memberOptions(task?.assignee_id||''); $('#delete-task').style.display=task?'block':'none'; $('#task-dialog').showModal(); }
$('#add-task').addEventListener('click',()=>openTask()); $('#priority-filter').addEventListener('change',render);
$('#task-form').addEventListener('submit', async e=> { e.preventDefault(); const id=$('#task-id').value; const data={title:$('#title').value.trim(),description:$('#description').value.trim(),priority:$('#priority').value,due_date:$('#due-date').value||null,assignee_id:$('#assignee').value?Number($('#assignee').value):null}; try { await api(id?`/api/tasks/${id}`:`/api/projects/${projectId}/tasks`,{method:id?'PATCH':'POST',body:JSON.stringify(data)}); $('#task-dialog').close(); await load(); } catch(err){toast(err.message)} });
$('#delete-task').addEventListener('click',async()=>{const id=$('#task-id').value;if(!confirm('Delete this task?'))return;try{await api(`/api/tasks/${id}`,{method:'DELETE'});$('#task-dialog').close();await load()}catch(err){toast(err.message)}});
$('#add-member').addEventListener('click',()=>{$('#member-form').reset();$('#member-dialog').showModal()});
$('#member-form').addEventListener('submit',async e=>{e.preventDefault();try{await api(`/api/projects/${projectId}/members`,{method:'POST',body:JSON.stringify({name:$('#member-name').value.trim(),email:$('#member-email').value.trim(),role:$('#member-role').value})});$('#member-dialog').close();await load()}catch(err){toast(err.message)}});
document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
(async()=>{try{const projects=await api('/api/projects');projectId=projects[0].id;await load()}catch(err){toast(err.message)}})();
