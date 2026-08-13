import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.2/full/pyodide.mjs";

const pyodideReady = (async () => {
  const pyodide = await loadPyodide();
  const sourceResponse = await fetch("./archive_inspection.py", { cache: "no-store" });
  if (!sourceResponse.ok) {
    throw new Error(`inspection source fetch failed: HTTP ${sourceResponse.status}`);
  }
  const source = await sourceResponse.text();
  pyodide.FS.writeFile("/archive_inspection.py", source);
  await pyodide.runPythonAsync("import sys; sys.path.insert(0, '/'); import archive_inspection");
  return pyodide;
})();

self.onmessage = async (event) => {
  const { id, selectedPath } = event.data ?? {};
  try {
    if (typeof selectedPath !== "string" || !selectedPath) {
      throw new Error("selectedPath is required");
    }
    const pyodide = await pyodideReady;
    pyodide.globals.set("selected_path", selectedPath);
    const result = await pyodide.runPythonAsync(`
import archive_inspection
await archive_inspection.inspect_same_origin(
    "./archive-manifest.json",
    "./artifacts/" + selected_path,
    selected_path,
)
`);
    self.postMessage({ id, result: JSON.parse(result) });
  } catch (error) {
    self.postMessage({ id, error: error instanceof Error ? error.message : String(error) });
  }
};
