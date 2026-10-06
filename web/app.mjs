const jobList = document.querySelector('#job-list');
const rejectedList = document.querySelector('#rejected-list');
const filters = [...document.querySelectorAll('.filter')];
let data;
let active = 'all';

const ownership = {
  internal_ai: '社内AI',
  internal_data_platform: '社内データ基盤',
  own_product: '自社プロダクト',
};

function man(value) {
  return `${Math.round(Number(value) / 10000).toLocaleString('ja-JP')}万円`;
}

function remoteLabel(value) {
  return ({ full_remote:'フルリモート', remote:'リモート', hybrid:'ハイブリッド', onsite:'出社' })[value] ?? value;
}

function elem(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

function scoreRow(label, value) {
  const row = elem('div','score-row');
  row.append(elem('span','',label));
  const meter = elem('div','meter');
  const bar = elem('i');
  bar.style.width = `${Number(value) * 20}%`;
  meter.append(bar);
  row.append(meter, elem('b','',`${value}/5`));
  return row;
}

function card(job) {
  const article = elem('article','job-card');

  const head = elem('div','job-head');
  const company = elem('div','company');
  company.append(elem('span','rank',`#${job.rank}`), elem('strong','',job.company_name));
  head.append(company, elem('strong','score',String(job.score)));

  const title = elem('h3','',job.title);

  const tags = elem('div','tags');
  [
    ownership[job.ownership_scope] ?? job.ownership_scope,
    remoteLabel(job.remote_mode),
    Number(job.ai_production) >= 4 ? 'AI本番利用' : null,
    Number(job.cross_company_scope) >= 4 ? '全社横断' : null,
    Number(job.fixed_overtime_hours) === 0 ? '固定残業なし' : `固定残業${job.fixed_overtime_hours}h`,
  ].filter(Boolean).forEach(t => tags.append(elem('span','tag',t)));

  const pay = elem('div','pay');
  pay.append(
    elem('span','', '基本給'),
    elem('strong','', `${man(job.base_salary_min_jpy)}〜${man(job.base_salary_max_jpy)}`),
    elem('small','', Number(job.fixed_overtime_hours) > 0 ? '固定残業代は800万円判定に不算入' : '固定残業代なし')
  );

  const location = elem('div','meta');
  location.append(elem('span','',remoteLabel(job.remote_mode)), elem('span','',job.location || '—'));

  const detail = elem('div','scores');
  detail.append(
    scoreRow('技術裁量',job.technical_ownership),
    scoreRow('実装',job.implementation_ratio),
    scoreRow('AI',job.ai_production),
    scoreRow('全社性',job.cross_company_scope),
    scoreRow('経歴接続',job.career_fit)
  );

  const link = elem('a','open-job','求人を見る');
  link.href = job.source_url; link.target = '_blank'; link.rel = 'noopener noreferrer';

  article.append(head,title,tags,pay,location,detail,link);
  return article;
}

function rejectCard(job) {
  const article = elem('article','reject-card');
  const top = elem('div','reject-top');
  const name = elem('div');
  name.append(elem('strong','',job.company_name),elem('span','',job.title));
  top.append(name,elem('span','reject-mark','対象外'));
  const reasons = elem('div','reasons');
  (job.failed_gates || []).forEach(r => reasons.append(elem('span','reason',r)));
  const salary = elem('p','reject-salary',`基本給下限 ${man(job.base_salary_min_jpy)} / 想定年収下限 ${man(job.total_salary_min_jpy)}`);
  article.append(top,reasons,salary);
  return article;
}

function matches(job) {
  if (active === 'remote') return ['full_remote','remote','hybrid'].includes(job.remote_mode);
  if (active === 'platform') return Number(job.data_platform_depth) >= 4;
  if (active === 'ai') return Number(job.ai_production) >= 4;
  return true;
}

function renderJobs() {
  jobList.replaceChildren();
  const rows = data.eligible.filter(matches);
  if (!rows.length) return jobList.append(elem('p','state','該当求人なし'));
  rows.forEach(job => jobList.append(card(job)));
}

function render() {
  document.querySelector('#eligible-count').textContent = data.summary.eligible_count;
  document.querySelector('#top-salary').textContent = man(data.summary.top_base_salary_min_jpy);
  document.querySelector('#remote-count').textContent = data.summary.remote_friendly_count;
  document.querySelector('#rejected-count').textContent = data.summary.rejected_count;
  renderJobs();
  rejectedList.replaceChildren();
  data.rejected.forEach(job => rejectedList.append(rejectCard(job)));
}

filters.forEach(button => button.addEventListener('click', () => {
  active = button.dataset.filter;
  filters.forEach(x => x.classList.toggle('active',x === button));
  renderJobs();
}));

fetch('./job-dashboard.json',{cache:'no-store'})
  .then(r => { if(!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
  .then(json => { data = json; render(); })
  .catch(error => {
    jobList.replaceChildren(elem('p','state error',`読み込み失敗: ${error.message}`));
  });
