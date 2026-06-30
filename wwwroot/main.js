import {
  generateLongCode,
  listNonRetailEditionOptions,
  listOfficialEditionOptions,
  longCodeFieldsFromValues,
} from './mozaik-license.js';

const machineIdInput = document.getElementById('machine-id');
const editionSelect = document.getElementById('edition');
const editionNonRetailSelect = document.getElementById('edition-non-retail');
const nonRetailMenu = document.getElementById('non-retail-menu');
const expiryInput = document.getElementById('expiry');
const generateBtn = document.getElementById('generate-btn');
const formErrorEl = document.getElementById('form-error');
const resultsEl = document.getElementById('results');
const resultCodeEl = document.getElementById('result-code');
const copyBtn = document.getElementById('copy-btn');
const metaMachineId = document.getElementById('meta-machine-id');
const metaEdition = document.getElementById('meta-edition');
const metaExpiry = document.getElementById('meta-expiry');

function appendOptions(select, options, selectedId) {
  for (const option of options) {
    const el = document.createElement('option');
    el.value = option.id;
    el.textContent = option.label;
    if (option.id === selectedId) {
      el.selected = true;
    }
    select.appendChild(el);
  }
}

appendOptions(editionSelect, listOfficialEditionOptions(), 'manufacturing');
appendOptions(editionNonRetailSelect, listNonRetailEditionOptions());

function selectedEditionId() {
  if (nonRetailMenu.open && editionNonRetailSelect.value) {
    return editionNonRetailSelect.value;
  }
  return editionSelect.value;
}

function showError(message) {
  formErrorEl.textContent = message;
  formErrorEl.classList.remove('hidden');
}

function clearError() {
  formErrorEl.textContent = '';
  formErrorEl.classList.add('hidden');
}

function normalizeMachineId(raw) {
  const trimmed = raw.trim();
  if (!trimmed) {
    throw new Error('Enter a machine ID.');
  }
  if (trimmed.length > 7) {
    throw new Error('Machine ID must be 7 characters or fewer.');
  }
  if (!/^[A-Za-z0-9]+$/.test(trimmed)) {
    throw new Error('Machine ID must be alphanumeric.');
  }
  return trimmed.slice(0, 7);
}

function parseExpiry(value) {
  if (!value) {
    throw new Error('Select an expiry date.');
  }
  const [yearStr, monthStr, dayStr] = value.split('-');
  const year = Number(yearStr);
  const month = Number(monthStr);
  const day = Number(dayStr);
  if (!year || !month || !day) {
    throw new Error('Invalid expiry date.');
  }
  return { year, month, day };
}

async function copyText(text) {
  if (navigator.clipboard?.writeText && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Fall back below (e.g. permission denied).
    }
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.select();
  textarea.setSelectionRange(0, text.length);

  let ok = false;
  try {
    ok = document.execCommand('copy');
  } finally {
    document.body.removeChild(textarea);
  }
  return ok;
}

function flashCopyButton(label, revertLabel = 'Copy') {
  copyBtn.textContent = label;
  setTimeout(() => {
    copyBtn.textContent = revertLabel;
  }, 1500);
}

nonRetailMenu.addEventListener('toggle', () => {
  if (!nonRetailMenu.open) {
    editionNonRetailSelect.value = '';
  }
});

generateBtn.addEventListener('click', () => {
  clearError();
  resultsEl.classList.add('hidden');

  try {
    const machineId = normalizeMachineId(machineIdInput.value);
    const { year, month, day } = parseExpiry(expiryInput.value);
    const fields = longCodeFieldsFromValues({
      month,
      day,
      year,
      edition: selectedEditionId(),
    });
    const code = generateLongCode(fields, machineId);

    resultCodeEl.textContent = code;
    metaMachineId.textContent = machineId;
    metaEdition.textContent = fields.editionDisplayName;
    metaExpiry.textContent = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    resultsEl.classList.remove('hidden');
  } catch (err) {
    showError(err.message ?? String(err));
  }
});

copyBtn.addEventListener('click', async () => {
  const code = resultCodeEl.textContent?.trim();
  if (!code) {
    return;
  }
  const ok = await copyText(code);
  flashCopyButton(ok ? 'Copied' : 'Copy failed');
});

machineIdInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    generateBtn.click();
  }
});
