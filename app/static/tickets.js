export const escape = (value) => String(value ?? '—').replace(/[&<>"']/g, token => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[token]));
export const time = (minute) => minute == null ? '—' : `${minute >= 1440 ? '+1 ' : ''}${String(Math.floor(minute % 1440 / 60)).padStart(2,'0')}:${String(minute % 60).padStart(2,'0')}`;
export const interval = ([start, end]) => `${time(start)}–${time(end)}`;
const reason = {PLACED:'已落位', NO_WINDOW:'没有共同开工窗口', RESOURCE_FULL:'窗口内资源已占满', DEPENDENCY_BLOCKED:'前置工序未落位', DEPENDENCY_CYCLE:'工序成环', MISSING_DEPENDENCY:'缺失前置工单', UNKNOWN_STAGE:'未知工位', UNKNOWN_ROLE:'未知工种', HOLD_UNCERTAIN:'资源预约待核实', INVALID_HOLD:'无效预约', ACCEPTED:'已采信', BAD_ORDER:'工单字段异常', DUPLICATE_CONFLICT:'同号工单冲突', DUPLICATE_REPLAY:'同号重传', BAD_JSON:'记录截断或无效', EMPTY_ROW:'空行'};
export const describe = code => reason[code] || code;
export const heading = (title, control = '') => `<div class="panel-head"><h2>${title}</h2>${control}</div>`;
export function table(labels, rows) {
  return rows.length ? `<div class="table-wrap"><table><thead><tr>${labels.map(v => `<th>${escape(v)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(value => `<td${typeof value === 'number' ? ' class="number"' : ''}>${escape(value)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : '<p>暂无记录</p>';
}
export function ticket(job, data) {
  if (!job) return '<p>选择工序查看证据</p>';
  const who = data.calendars.technicians[job.tech]?.name;
  return `<div class="ticket ${job.status === 'scheduled' ? '' : 'bad'}"><small>${escape(job.id)} · 工单第 ${job.line} 行</small><strong>${escape(job.title)}</strong><p>${escape(job.stage)} · ${escape(who || job.role)}</p><p>${escape(describe(job.code))} <time>${job.start == null ? '' : interval([job.start,job.end])}</time></p></div>
  <div class="ticket"><small>放行 / 截止</small><p><time>${time(job.ready ?? job.release)}</time> / <time>${time(job.deadline)}</time></p><small>前置工序</small><p>${escape(job.needs.join('、') || '无')}</p><small>阻塞证据</small><p>${escape(job.related.join('、') || '无')}</p>${job.end > job.deadline ? `<p class="bad-text">超时 ${job.end-job.deadline} 分钟</p>` : ''}</div>`;
}
