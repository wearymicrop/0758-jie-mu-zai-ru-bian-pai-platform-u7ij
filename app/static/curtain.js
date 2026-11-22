import {escape, time, describe, heading, ticket, interval} from './tickets.js';

function timeline(jobs, venue, active) {
  const start = Math.floor(Math.min(...venue.map(row=>row[0]), ...jobs.map(row=>row.start)) / 60) * 60;
  const end = Math.ceil(Math.max(...venue.map(row=>row[1]), ...jobs.map(row=>row.stage_end)) / 60) * 60;
  const space = end - start;
  const hour = 60 / space * 100;
  const ticks = Array.from({length: Math.ceil(space/60)}, (_,i) => `<span class="tick" style="left:${i*60/space*100}%">${time(start+i*60)}</span>`).join('');
  const strip = (left,right) => `left:${(left-start)/space*100}%;width:${(right-left)/space*100}%`;
  const names = [...new Set(jobs.map(row=>row.stage))];
  return `<div class="chart-wrap" tabindex="0" aria-label="工序时间轴"><div class="cue-chart" style="--hour:${hour}%"><div class="lane ruler"><div class="ruler-label">剧场时刻</div><div class="track">${ticks}</div></div>${names.map(stage => {
    const rows = jobs.filter(job=>job.stage===stage);
    return `<div class="lane"><div class="lane-label">${escape(stage)}<small>${rows.length} 道工序</small></div><div class="track">${rows.map(job=>`<button class="cue ${job.end > job.deadline ? 'late' : ''}" data-job="${escape(job.id)}" aria-pressed="${job.id===active}" style="${strip(job.start, job.end)}" title="${escape(job.title)} · ${interval([job.start,job.end])}">${escape(job.id)}</button>${job.reset ? `<span class="cue reset" style="${strip(job.end,job.stage_end)}" title="清场"></span>`:''}`).join('')}</div></div>`;
  }).join('')}</div></div>`;
}

export function curtain(data, state) {
  const jobs = data.schedule.jobs;
  const stages = Object.keys(data.calendars.stages);
  const filtered = jobs.filter(row => !state.stage || row.stage === state.stage);
  const scheduled = filtered.filter(row => row.status === 'scheduled');
  const pending = filtered.filter(row => row.status !== 'scheduled');
  const selected = filtered.find(row => row.id === state.job) || scheduled[0] || pending[0];
  const options = `<select id="stage" aria-label="筛选工位"><option value="">全部工位</option>${stages.map(v=>`<option ${v===state.stage?'selected':''}>${escape(v)}</option>`).join('')}</select>`;
  return [heading('工位时间轴',options) + (scheduled.length ? timeline(scheduled,data.calendars.venue,selected?.id) : '<p>该工位暂无落位工序</p>') +
    `<h3>待排与隔离</h3><div class="ticket-list">${pending.map(row=>`<button data-job="${escape(row.id)}" aria-pressed="${row.id===selected?.id}">${escape(row.id)} · ${escape(row.title)} · ${escape(describe(row.code))}</button>`).join('') || '<p>全部工序已落位</p>'}</div>`,
    heading('工序票签') + ticket(selected,data)];
}
