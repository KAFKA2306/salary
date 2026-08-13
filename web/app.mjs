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

async function main() {
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

main().catch((error) => {
  summary.textContent = `読み込み失敗: ${error.message}`;
});
