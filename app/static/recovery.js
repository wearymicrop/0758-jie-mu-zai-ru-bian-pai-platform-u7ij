import {escape, time, interval, heading, table, describe} from './tickets.js';

const minuteOf = (value) => {
  const [hour, minute] = value.split(':').map(Number);
  return hour * 60 + minute;
};

export function closurePayload(sample) {
  const backup = document.querySelector('#closure-backup').value.trim();
  return {
    sample,
    closure: {
      id: document.querySelector('#closure-id').value.trim(),
      stage: document.querySelector('#closure-stage').value.trim(),
      as_of: minuteOf(document.querySelector('#closure-asof').value),
      start: minuteOf(document.querySelector('#closure-start').value),
      end: minuteOf(document.querySelector('#closure-end').value),
      ...(backup ? {backup_stage: backup} : {}),
    },
  };
}

function recoveryTimeline(data, recovery) {
  const placed = recovery.jobs.filter(job => job.status === 'scheduled');
  const event = recovery.event;
  const venue = data.calendars.venue;
  if (!placed.length) {
    return `<p>封场后没有可落位的工序，全部进入待排，见右侧证据。</p>`;
  }
  const start = Math.floor(Math.min(...venue.map(row => row[0]), ...placed.map(row => row.start)) / 60) * 60;
  const end = Math.ceil(Math.max(...venue.map(row => row[1]), ...placed.map(row => row.stage_end), event.end) / 60) * 60;
  const space = end - start;
  const ticks = Array.from({length: Math.ceil(space / 60)}, (_, i) =>
    `<span class="tick" style="left:${i * 60 / space * 100}%">${time(start + i * 60)}</span>`).join('');
  const strip = (left, right) => `left:${(left - start) / space * 100}%;width:${(right - left) / space * 100}%`;
  const closureBand = (stage) => stage === event.stage
    ? `<span class="closure-band" style="${strip(event.start, event.end)}" title="封场 ${interval([event.start, event.end])}">封场</span>` : '';
  return `<div class="chart-wrap" tabindex="0" aria-label="恢复后时间轴"><div class="cue-chart"><div class="lane ruler"><div class="ruler-label">剧场时刻</div><div class="track">${ticks}</div></div>${Object.keys(data.calendars.stages).map(stage => {
    const rows = placed.filter(job => job.stage === stage);
    return `<div class="lane"><div class="lane-label">${escape(stage)}<small>${rows.length} 道工序</small></div><div class="track">${closureBand(stage)}${rows.map(job =>
      `<button class="cue ${job.late_minutes > 0 ? 'late' : ''} ${job.relocated ? 'moved' : ''}" data-job="${escape(job.id)}" style="${strip(job.start, job.end)}" title="${escape(job.title)} · ${interval([job.start, job.end])}${job.relocated ? ' · 改场自 ' + escape(job.original_stage) : ''}">${escape(job.id)}</button>`).join('')}</div></div>`;
  }).join('')}</div></div>`;
}

const entryText = {locked: '已完工锁定', active: '开工中续排', waiting: '待开工重排', scheduled: '原已落位', pending: '待排', isolated: '隔离'};

export function recoveryView(data, recovery) {
  const s = recovery.summary;
  const kpis = [['锁定工序', s.locked], ['开工中', s.active], ['等待工序', s.waiting], ['改场工序', s.relocated], ['恢复待排', s.pending], ['恢复超时', s.late]]
    .map(([label, count]) => `<div class="kpi"><small>${label}</small><strong>${count}</strong></div>`).join('');
  const eventRows = [
    ['事件号', recovery.event.id], ['封场工位', recovery.event.stage],
    ['封场时段', interval([recovery.event.start, recovery.event.end])],
    ['巡检时刻', time(recovery.event.as_of)],
    ['备用工位', recovery.event.backup_stage || '未启用'],
  ];
  const jobRows = recovery.jobs.filter(job => job.entry_status !== 'scheduled' || job.relocated)
    .map(job => [job.id, entryText[job.entry_status] || job.entry_status,
      job.relocated ? `${job.original_stage} → ${job.stage}` : job.stage,
      job.start == null ? '—' : interval([job.start, job.end]),
      job.late_minutes ? `超时 ${job.late_minutes} 分钟` : describe(job.code)]);
  const board = heading('恢复指标') + `<section class="kpis recovery-kpis" aria-label="恢复指标">${kpis}</section>`
    + heading('恢复后时间轴') + recoveryTimeline(data, recovery)
    + heading('恢复后的空档') + table(['工位', '空档时段', '分钟', '成因'],
      recovery.gaps.map(g => [g.stage, interval([g.start, g.end]), g.minutes, g.cause]))
    + heading('超时工序（截止不顺延）') + table(['工单', '工位', '超时分钟', '是否改场'],
      recovery.late.map(j => [j.id, j.stage, j.minutes, j.relocated ? '是' : '否']));
  const evidence = heading('停场事件') + table(['项目', '内容'], eventRows)
    + heading('改场与等待工序') + table(['工单', '开工事实', '工位变化', '恢复时段', '结果'], jobRows);
  return [board, evidence];
}
