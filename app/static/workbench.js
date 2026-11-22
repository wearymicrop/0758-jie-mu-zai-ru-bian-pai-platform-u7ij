import {curtain} from './curtain.js';
import {describe, escape, heading, interval, table} from './tickets.js';

const $ = selector => document.querySelector(selector);
const links = [...document.querySelectorAll('nav a')];
const state = {data:null, archive:null, sample:'dirty', job:'', stage:'', request:0};
const show = text => { $('#status').textContent = text; };

async function request(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || '请求失败');
  return data;
}

function archivePanel() {
  if (!state.archive) return '<p>确认归档后可下载执行清单</p>';
  return `<div class="archived"><small>批次编号</small><code>${escape(state.archive.id)}</code><button id="rerun">复跑核验</button><a class="file" href="/api/runs/${state.archive.id}/export">下载执行证据</a></div>`;
}

function sections(view, data) {
  const d = data[view];
  switch(view) {
    case 'orders': return [heading('工单采信')+table(['行号','工单','采信状态'],d.rows.map(r=>[r.line,r.id,describe(r.code)])),heading('来源隔离')+table(['行号','原因'],d.rows.filter(r=>r.code!=='ACCEPTED').map(r=>[r.line,describe(r.code)]))];
    case 'dependencies': return [heading('依赖边')+table(['工单','前置'],Object.entries(d.edges).map(([key,needs])=>[key,needs.join('、')||'无'])),heading('隔离依据')+table(['工单','状态','相关工序'],Object.entries(d.issues).map(([key,v])=>[key,describe(v.code),v.related.join('、')]))];
    case 'calendars': return [heading('技师可开工')+table(['技师','工种','有效窗口'],Object.entries(d.technicians).map(([key,t])=>[t.name,t.role,d.effective_tech[key].map(interval).join(' / ')])),heading('剧场窗口')+table(['工位','有效窗口'],Object.entries(d.effective_stages).map(([k,v])=>[k,v.map(interval).join(' / ')]))];
    case 'conflicts': return [heading('预约冲突')+table(['资源','冲突预约','重叠段'],d.overlaps.map(h=>[h.resource,`${h.left} / ${h.right}`,interval([h.start,h.end])] )),heading('无效预约')+table(['源序号','预约','原因'],d.issues.map(h=>[h.source_index,h.id,describe(h.code)]))];
    case 'reconcile': return [heading('截止偏差')+table(['工单','源行','超时分钟'],d.late.map(r=>[r.id,r.line,r.minutes])),heading('守恒核验')+table(['核验项','差异'],[['输入行数差',d.row_gap],['排程碰撞',d.collisions.length],['前置违序',d.premature.length],['预约重叠',d.hold_clashes]])];
    case 'dispatch': return [heading('执行顺序')+table(['工位','工单','技师','开工时段'],d.stages.flatMap(s=>s.steps.map(j=>[s.stage,`${j.id} · ${j.title}`,j.technician,interval([j.start,j.end])]))),heading('归档凭证')+archivePanel()];
    default: return curtain(data,state);
  }
}

function render() {
  if (!state.data) return;
  const link = links.find(a=>a.hash===location.hash) || links[0];
  links.forEach(a=>a===link ? a.setAttribute('aria-current','page') : a.removeAttribute('aria-current'));
  $('#heading').textContent = link.textContent;
  $('#day').textContent = `${state.data.calendars.date} / 剧场作业日`;
  const counts = state.data.reconcile;
  $('#metrics').innerHTML = [['已落位',counts.scheduled],['待排',counts.pending],['工单隔离',counts.isolated],['超时',counts.late_count]].map(([label,count])=>`<div class="kpi"><small>${label}</small><strong>${count}</strong></div>`).join('');
  const [board, evidence] = sections(link.dataset.view,state.data);
  $('#board').innerHTML=board; $('#evidence').innerHTML=evidence;
  $('#run-key').textContent = state.archive ? `${state.archive.manifest.rule_version} · ${state.archive.id.slice(0,12)}` : 'tandem-stage-1.0 · 试排快照';
}

async function load() {
  const token = ++state.request;
  show('读取样例中');
  try {
    const sample = $('#sample').value;
    const data = await request(`/api/samples/${sample}`);
    if (token !== state.request) return;
    Object.assign(state,{data,archive:null,sample,job:'',stage:''});
    render(); show(data.reconcile.status==='MATCHED' ? '工单与资源已对平' : '有待复核的勾稽差异');
  } catch (error) { if (token===state.request) show(error.message); }
}

async function archive(body) {
  const token=++state.request;
  const button=$('#run');
  button.disabled=true;
  try {
    const record=await request('/api/runs',body);
    if (token!==state.request) return;
    Object.assign(state,{archive:record,data:record.result,sample:body.sample || '',job:'',stage:''});
    render(); show(record.reused?'已打开同一批次':'已保存执行清单');
  } catch (error) { if (token===state.request) show(error.message); }
  finally { button.disabled=!state.sample; }
}

$('#sample').addEventListener('change',()=>{ $('#run').disabled=false; load(); });
$('#run').addEventListener('click',()=>archive({sample:$('#sample').value}));
$('#custom-form').addEventListener('submit',event=>{
  event.preventDefault();
  try { archive({orders:$('#orders').value,calendar:JSON.parse($('#calendar').value)}); }
  catch { show('剧场日历需为有效 JSON'); }
});
document.addEventListener('change',event=>{ if(event.target.id==='stage') { state.stage=event.target.value; render(); $('#stage').focus(); } });
document.addEventListener('click',async event=>{
  const btn=event.target.closest('button');
  if (btn?.dataset.job) { state.job=btn.dataset.job; render(); [...document.querySelectorAll('[data-job]')].find(node=>node.dataset.job===state.job)?.focus(); }
  if (btn?.id==='rerun' && state.archive) {
    try { await request(`/api/runs/${state.archive.id}/rerun`,{}); show('复跑一致'); }
    catch (error) { show(error.message); }
  }
});
window.addEventListener('hashchange',render);
load();
