const summary = document.querySelector('#summary');
const catalog = document.querySelector('#catalog');
const resultBox = document.querySelector('#inspection-result');
const worker = new Worker('./worker.mjs', { type: 'module' });
let requestId = 0;
const pending = new Map();

worker.addEventListener('message', (event) => {
  const { id, result, error } = event.data ?? {};
  const resolve = pending.get(id);
  if (!resolve) return;
  pending.delete(id);
  resolve({ result, error });
});

function inspect(path) {
  const id = ++requestId;
  return new Promise((resolve) => {
    pending.set(id, resolve);
    worker.postMessage({ id, selectedPath: path });
  });
}

function td(text) {
  const cell = document.createElement('td');
  cell.textContent = text;
  return cell;
}

function benchmarkBand(value, metrics) {
  if (value < metrics.q1) return '第1四分位未満';
  if (value < metrics.median) return '第1四分位〜中央値';
  if (value < metrics.q3) return '中央値〜第3四分位';
  return '第3四分位以上';
}

function deltaFromMedian(value, metrics, digits = 1) {
  const delta = ((value / metrics.median) - 1) * 100;
  return `${delta >= 0 ? '+' : ''}${delta.toFixed(digits)}%`;
}

function formatYen(value) {
  return `${Math.round(value).toLocaleString('ja-JP')}円`;
}

async function loadBenchmark() {
  const status = document.querySelector('#benchmark-status');
  const select = document.querySelector('#company-select');
  const result = document.querySelector('#company-result');
  const response = await fetch('./transport-equipment-fy2026-salary-top20.json', { cache: 'no-store' });
  if (!response.ok) throw new Error(`current benchmark fetch failed: HTTP ${response.status}`);
  const data = await response.json();
  const observations = Array.isArray(data.observations) ? data.observations : [];
  if (observations.length !== 20) throw new Error(`current benchmark expected 20 observations, got ${observations.length}`);
  const metrics = data.benchmark?.metrics;
  const salaryMetrics = metrics?.average_annual_salary_jpy;
  const ageMetrics = metrics?.average_age_years;
  const tenureMetrics = metrics?.average_tenure_years;
  if (!salaryMetrics || !ageMetrics || !tenureMetrics) throw new Error('current benchmark three-axis metrics missing');

  document.querySelector('#salary-q1').textContent = formatYen(salaryMetrics.q1);
  document.querySelector('#salary-median').textContent = formatYen(salaryMetrics.median);
  document.querySelector('#salary-q3').textContent = formatYen(salaryMetrics.q3);
  document.querySelector('#age-median').textContent = `${ageMetrics.median}歳`;
  document.querySelector('#tenure-median').textContent = `${tenureMetrics.median}年`;

  select.replaceChildren(new Option('会社を選択', ''));
  observations.forEach((observation, index) => {
    select.append(new Option(`${observation.company_name} (${observation.securities_code})`, String(index)));
  });
  status.textContent = `${data.verified_at}確認 / ${observations.length}社`;

  select.addEventListener('change', () => {
    if (select.value === '') {
      result.hidden = true;
      return;
    }
    const observation = observations[Number(select.value)];
    document.querySelector('#company-name').textContent = observation.company_name;
    document.querySelector('#salary-value').textContent = formatYen(observation.average_annual_salary_jpy);
    document.querySelector('#salary-vs-median').textContent = deltaFromMedian(observation.average_annual_salary_jpy, salaryMetrics);
    document.querySelector('#salary-band').textContent = benchmarkBand(observation.average_annual_salary_jpy, salaryMetrics);
    document.querySelector('#age-value').textContent = `${observation.average_age_years}歳`;
    document.querySelector('#age-vs-median').textContent = deltaFromMedian(observation.average_age_years, ageMetrics);
    document.querySelector('#age-band').textContent = benchmarkBand(observation.average_age_years, ageMetrics);
    document.querySelector('#tenure-value').textContent = `${observation.average_tenure_years}年`;
    document.querySelector('#tenure-vs-median').textContent = deltaFromMedian(observation.average_tenure_years, tenureMetrics);
    document.querySelector('#tenure-band').textContent = benchmarkBand(observation.average_tenure_years, tenureMetrics);
    document.querySelector('#fiscal-year').textContent = observation.fiscal_year_end;
    const source = document.querySelector('#source-link');
    source.href = observation.source_document.url;
    source.textContent = `EDINET ${observation.source_document.doc_id} / ${observation.source_document.section}`;
    result.hidden = false;
  });
}

async function loadArchive() {
  const response = await fetch('./archive-manifest.json', { cache: 'no-store' });
  if (!response.ok) throw new Error(`manifest fetch failed: HTTP ${response.status}`);
  const manifest = await response.json();
  const artifacts = Array.isArray(manifest.artifacts) ? manifest.artifacts : [];
  summary.textContent = `${manifest.archive_as_of ?? 'UNKNOWN'} snapshot / ${artifacts.length} manifest artifacts`;

  for (const artifact of artifacts) {
    const row = document.createElement('tr');
    row.append(td(artifact.path));
    row.append(td(artifact.role ?? 'UNKNOWN'));
    const status = td(artifact.current_use_status ?? 'UNKNOWN');
    if (artifact.current_use_status === 'UNKNOWN_PROVENANCE') status.className = 'warning';
    row.append(status);
    row.append(td(artifact.git_blob_sha ?? 'UNKNOWN'));
    row.append(td(Number.isFinite(artifact.size_bytes) ? `${artifact.size_bytes.toLocaleString()} B` : 'UNKNOWN'));
    const action = document.createElement('td');
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = 'inspect';
    button.addEventListener('click', async () => {
      resultBox.textContent = 'Pyodideで検査中…';
      const { result, error } = await inspect(artifact.path);
      if (error) {
        resultBox.textContent = `検査失敗: ${error}`;
        return;
      }
      const duplicateNote = result.same_blob_paths.length > 1
        ? `同一blob: ${result.same_blob_paths.join(', ')}（別datasetとして二重計上しません）`
        : '同一blob aliasなし';
      const eligibility = result.aggregate_eligible
        ? '集計適格: manifest status上は除外対象ではありません。'
        : '集計対象外: UNKNOWN_PROVENANCE / ARCHIVE_ONLY は現在値・正準値として扱いません。';
      resultBox.textContent = `${artifact.path}\n${eligibility}\n${duplicateNote}\n${JSON.stringify(result.detail, null, 2)}`;
    });
    action.append(button);
    row.append(action);
    catalog.append(row);
  }
}

loadBenchmark().catch((error) => {
  document.querySelector('#benchmark-status').textContent = `読み込み失敗: ${error.message}`;
  document.querySelector('#company-select').disabled = true;
});
loadArchive().catch((error) => {
  summary.textContent = `読み込み失敗: ${error.message}`;
});