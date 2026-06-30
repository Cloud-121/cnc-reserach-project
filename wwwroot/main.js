import { dotnet } from './_framework/dotnet.js';

const loadingEl = document.getElementById('loading');
const appEl = document.getElementById('app');
const errorEl = document.getElementById('error');
const errorTextEl = document.getElementById('error-text');
const exeInput = document.getElementById('exe-input');
const dllInput = document.getElementById('dll-input');
const patchBtn = document.getElementById('patch-btn');
const logEl = document.getElementById('log');
const resultsEl = document.getElementById('results');
const downloadExe = document.getElementById('download-exe');
const downloadDll = document.getElementById('download-dll');

let patchAssemblies = null;
let exeBytes = null;
let dllBytes = null;
let downloadUrls = [];

function setLog(lines) {
  logEl.textContent = Array.isArray(lines) ? lines.join('\n') : String(lines);
}

function appendLog(line) {
  logEl.textContent = logEl.textContent ? `${logEl.textContent}\n${line}` : line;
}

function revokeDownloadUrls() {
  for (const url of downloadUrls) {
    URL.revokeObjectURL(url);
  }
  downloadUrls = [];
}

function updatePatchButton() {
  patchBtn.disabled = !(exeBytes && dllBytes && patchAssemblies);
}

function readFileAsBytes(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(new Uint8Array(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error(`Failed to read ${file.name}`));
    reader.readAsArrayBuffer(file);
  });
}

function base64ToBytes(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function offerDownload(linkEl, filename, bytes) {
  const blob = new Blob([bytes], { type: 'application/octet-stream' });
  const url = URL.createObjectURL(blob);
  downloadUrls.push(url);
  linkEl.href = url;
  linkEl.download = filename;
}

exeInput.addEventListener('change', async () => {
  const file = exeInput.files?.[0];
  exeBytes = file ? await readFileAsBytes(file) : null;
  updatePatchButton();
});

dllInput.addEventListener('change', async () => {
  const file = dllInput.files?.[0];
  dllBytes = file ? await readFileAsBytes(file) : null;
  updatePatchButton();
});

patchBtn.addEventListener('click', async () => {
  if (!patchAssemblies || !exeBytes || !dllBytes) {
    return;
  }

  resultsEl.classList.add('hidden');
  revokeDownloadUrls();
  patchBtn.disabled = true;
  setLog('Patching…');

  try {
    const json = patchAssemblies(exeBytes, dllBytes);
    const result = JSON.parse(json);

    if (result.messages?.length) {
      setLog(result.messages);
    }

    if (!result.success) {
      appendLog(`Error: ${result.error ?? 'Patch failed'}`);
      return;
    }

    const patchedExe = base64ToBytes(result.patchedExe);
    const patchedDll = base64ToBytes(result.patchedDll);

    offerDownload(downloadExe, 'Mozaik.exe', patchedExe);
    offerDownload(downloadDll, 'MozaikData.dll', patchedDll);
    resultsEl.classList.remove('hidden');
  } catch (err) {
    appendLog(`Error: ${err.message ?? err}`);
  } finally {
    updatePatchButton();
  }
});

try {
  const { getAssemblyExports, getConfig } = await dotnet
    .withDiagnosticTracing(false)
    .create();

  const config = getConfig();
  const exports = await getAssemblyExports(config.mainAssemblyName);
  patchAssemblies = exports.MozaikPatcher.PatcherInterop.PatchAssemblies;

  await dotnet.run();

  loadingEl.classList.add('hidden');
  appEl.classList.remove('hidden');
  updatePatchButton();
} catch (err) {
  loadingEl.classList.add('hidden');
  errorEl.classList.remove('hidden');
  errorTextEl.textContent = err.message ?? String(err);
}
