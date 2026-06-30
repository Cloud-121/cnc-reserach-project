/** Browser port of mozaik_license.py long-format helpers (research only). */

function md5Hex(value) {
  const bytes = new TextEncoder().encode(value);
  const words = md5Digest(bytes);
  let hex = '';
  for (let i = 0; i < words.length; i += 1) {
    const word = words[i] >>> 0;
    hex += (word & 0xff).toString(16).padStart(2, '0');
    hex += ((word >>> 8) & 0xff).toString(16).padStart(2, '0');
    hex += ((word >>> 16) & 0xff).toString(16).padStart(2, '0');
    hex += ((word >>> 24) & 0xff).toString(16).padStart(2, '0');
  }
  return hex.toUpperCase();
}

function md5Digest(input) {
  const msg = padMd5(input);
  const state = [0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476];
  const K = new Uint32Array(64);
  for (let i = 0; i < 64; i += 1) {
    K[i] = Math.floor(Math.abs(Math.sin(i + 1)) * 2 ** 32) >>> 0;
  }
  const S = [
    7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22,
    5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20,
    4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23,
    6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21,
  ];

  for (let offset = 0; offset < msg.length; offset += 64) {
    const M = new Uint32Array(16);
    for (let i = 0; i < 16; i += 1) {
      M[i] = msg[offset + i * 4]
        | (msg[offset + i * 4 + 1] << 8)
        | (msg[offset + i * 4 + 2] << 16)
        | (msg[offset + i * 4 + 3] << 24);
    }
    let [a, b, c, d] = state;
    for (let i = 0; i < 64; i += 1) {
      let f;
      let g;
      if (i < 16) {
        f = (b & c) | (~b & d);
        g = i;
      } else if (i < 32) {
        f = (d & b) | (~d & c);
        g = (5 * i + 1) % 16;
      } else if (i < 48) {
        f = b ^ c ^ d;
        g = (3 * i + 5) % 16;
      } else {
        f = c ^ (b | ~d);
        g = (7 * i) % 16;
      }
      const temp = d;
      d = c;
      c = b;
      const sum = (a + f + K[i] + M[g]) >>> 0;
      b = (b + leftRotate(sum, S[i])) >>> 0;
      a = temp;
    }
    state[0] = (state[0] + a) >>> 0;
    state[1] = (state[1] + b) >>> 0;
    state[2] = (state[2] + c) >>> 0;
    state[3] = (state[3] + d) >>> 0;
  }
  return state;
}

function leftRotate(value, shift) {
  return ((value << shift) | (value >>> (32 - shift))) >>> 0;
}

function padMd5(input) {
  const bitLen = input.length * 8;
  const padLen = ((56 - ((input.length + 1) % 64)) + 64) % 64;
  const out = new Uint8Array(input.length + 1 + padLen + 8);
  out.set(input);
  out[input.length] = 0x80;
  const view = new DataView(out.buffer);
  view.setUint32(out.length - 8, bitLen >>> 0, true);
  view.setUint32(out.length - 4, Math.floor(bitLen / 2 ** 32), true);
  return out;
}

function extractDigits(value, count) {
  const out = [];
  for (const ch of value) {
    if (ch >= '0' && ch <= '9') {
      out.push(ch);
      if (out.length === count) {
        return out.join('');
      }
    }
  }
  return '';
}

function swapChars(value, pos1, pos2) {
  if (value.length < pos2) {
    return value;
  }
  const chars = value.split('');
  const i = pos1 - 1;
  const j = pos2 - 1;
  [chars[i], chars[j]] = [chars[j], chars[i]];
  return chars.join('');
}

function inversePermuteI(value) {
  if (value.length < 16) {
    return '';
  }
  value = swapChars(value, 8, 10);
  value = swapChars(value, 7, 12);
  value = swapChars(value, 5, 14);
  value = swapChars(value, 3, 16);
  value = swapChars(value, 1, 4);
  return value;
}

function formatDashed(raw, groups) {
  const parts = [];
  let idx = 0;
  for (const size of groups) {
    parts.push(raw.slice(idx, idx + size));
    idx += size;
  }
  return parts.join('-');
}

function formatLongCode(raw20) {
  const raw = raw20.toUpperCase();
  if (raw.length !== 20) {
    throw new Error('long code must be 20 hex chars');
  }
  return formatDashed(raw, [4, 4, 4, 4, 4]);
}

function applyEditionCode(state, editionCode) {
  state.tier = 0;
  state.mfgB = false;
  state.mfgC = false;
  state.dFlag = false;
  state.eFlag = false;
  state.fFlag = false;

  const code = editionCode;
  if (code === 1) state.tier = 1;
  if (code === 2) state.tier = 2;
  if (code === 4) state.tier = 3;
  if ((code >= 8 && code <= 14) || code === 22 || (code >= 30 && code <= 32) || (code >= 36 && code <= 38)) {
    state.tier = 4;
  }
  if ((code >= 16 && code <= 20) || code === 24 || (code >= 27 && code <= 29) || (code >= 33 && code <= 35)) {
    state.tier = 5;
  }
  if (code >= 27 && code <= 32) state.dFlag = true;
  if (code >= 33 && code <= 38) {
    state.dFlag = true;
    state.eFlag = true;
  }
  if ([12, 14, 18, 20, 22, 24].includes(code) || (code >= 27 && code <= 38)) {
    state.mfgB = true;
  }
  if ([20, 14, 22, 24, 28, 29, 31, 32, 34, 35, 37, 38].includes(code)) {
    state.mfgC = true;
  }
  if ([22, 24, 32, 29, 35, 38].includes(code)) {
    state.fFlag = true;
  }
}

function editionDisplayName(editionCode, enterpriseH = 0) {
  const state = { tier: 0, mfgB: false, mfgC: false, enterpriseH };
  applyEditionCode(state, editionCode);

  const names = [];
  if (state.tier === 1) names.push('Kitchen Sketch');
  if (state.tier === 2) names.push('Mozaik Design');
  if (state.tier === 3) names.push('Mozaik Design Pro');
  if (state.tier === 4 && !state.mfgC && !state.mfgB) names.push('Mozaik Manufacturing');
  if (state.tier === 4 && state.mfgC && !state.mfgB) names.push('Mozaik Optimizer');
  if (state.tier === 4 && !state.mfgC && state.mfgB) names.push('Mozaik MFG+OPT');
  if (state.tier === 4 && state.mfgC && state.mfgB) names.push('Mozaik CNC');
  if (state.tier === 5) names.push('Mozaik CNC Operator');
  if (enterpriseH === 1 && state.tier !== 5) names.push('Mozaik Enterprise');
  if (enterpriseH === 1 && state.tier === 5) names.push('Mozaik CNC Operator (Ent.)');
  return names.length ? names[names.length - 1] : `(unknown code ${editionCode})`;
}

const PRESET_ITEMS = [
  ['kitchen_sketch', 1, 0, 0],
  ['kitchen_sketch_enterprise', 1, 1, 0],
  ['design', 2, 0, 0],
  ['design_enterprise', 2, 1, 0],
  ['design_pro', 4, 0, 0],
  ['design_pro_enterprise', 4, 1, 0],
  ['manufacturing', 8, 0, 0],
  ['manufacturing_enterprise', 8, 1, 0],
  ['manufacturing_10', 10, 0, 0],
  ['mfg_opt', 12, 0, 0],
  ['mfg_opt_enterprise', 12, 1, 0],
  ['cnc', 14, 0, 0],
  ['cnc_enterprise', 14, 1, 0],
  ['cnc_operator', 16, 0, 0],
  ['cnc_operator_enterprise', 16, 1, 0],
  ['cnc_bundle_22', 22, 0, 0],
  ['cnc_operator_24', 24, 0, 0],
  ['cnc_operator_27', 27, 0, 0],
  ['cnc_operator_28', 28, 0, 0],
  ['cnc_operator_29', 29, 0, 0],
  ['mfg_opt_plus', 30, 0, 0],
  ['cnc_plus', 31, 0, 0],
  ['cnc_full', 32, 0, 0],
  ['cnc_operator_33', 33, 0, 0],
  ['cnc_operator_34', 34, 0, 0],
  ['cnc_operator_35', 35, 0, 0],
  ['mfg_opt_enterprise_plus', 36, 1, 0],
  ['cnc_enterprise_plus', 37, 1, 0],
  ['cnc_full_enterprise', 38, 1, 0],
];

const EDITION_PRESETS = {};
for (const [name, code, entH, entI] of PRESET_ITEMS) {
  EDITION_PRESETS[name] = {
    editionCode: code,
    enterpriseH: entH,
    enterpriseI: entI,
    displayName: editionDisplayName(code, entH),
  };
}

const OFFICIAL_EDITION_IDS = ['manufacturing', 'cnc', 'manufacturing_enterprise'];

export function listOfficialEditionOptions() {
  return OFFICIAL_EDITION_IDS.map((id) => {
    const preset = EDITION_PRESETS[id];
    return { id, label: preset.displayName };
  });
}

export function listNonRetailEditionOptions() {
  const official = new Set(OFFICIAL_EDITION_IDS);
  return listEditionOptions()
    .filter((option) => !official.has(option.id))
    .map((option) => {
      const preset = EDITION_PRESETS[option.id];
      const codeTag = `[code ${preset.editionCode}]`;
      const entTag = preset.enterpriseH ? ' (Enterprise)' : '';
      return {
        id: option.id,
        label: `${preset.displayName} ${codeTag}${entTag}`,
      };
    });
}

export function listEditionOptions() {
  const seen = new Set();
  const rows = [];
  for (const [name, code, entH, entI] of PRESET_ITEMS) {
    const token = `${code}:${entH}:${entI}`;
    if (seen.has(token)) {
      continue;
    }
    seen.add(token);
    rows.push({
      id: name,
      label: EDITION_PRESETS[name].displayName + (entH ? ' (Enterprise)' : ''),
    });
  }
  return rows;
}

export function resolveEdition(edition) {
  const key = edition.toLowerCase().replace(/ /g, '_').replace(/\+/g, '_');
  const preset = EDITION_PRESETS[key];
  if (!preset) {
    throw new Error(`Unknown edition: ${edition}`);
  }
  return {
    editionCode: preset.editionCode,
    enterpriseH: preset.enterpriseH,
    enterpriseI: preset.enterpriseI,
    displayName: preset.displayName,
  };
}

export function longCodeFieldsFromValues({
  month,
  day,
  year,
  edition = 'design_pro',
  featureFlags = 0,
  padding = '0000',
}) {
  const resolved = resolveEdition(edition);
  return {
    month,
    day,
    year,
    editionCode: resolved.editionCode,
    featureFlags,
    enterpriseH: resolved.enterpriseH,
    enterpriseI: resolved.enterpriseI,
    padding,
    editionDisplayName: resolved.displayName,
  };
}

function encodePostPermute(fields) {
  const yearOffset = fields.year - 2000;
  if (yearOffset < 0 || yearOffset > 255) {
    throw new Error('year must be between 2000 and 2255');
  }

  const monthHex = fields.month.toString(16).toUpperCase();
  const dayHex = fields.day.toString(16).toUpperCase().padStart(2, '0');
  const yearHex = yearOffset.toString(16).toUpperCase().padStart(2, '0');
  const editionHex = fields.editionCode.toString(16).toUpperCase().padStart(2, '0');
  const flagsHex = fields.featureFlags.toString(16).toUpperCase();
  const hHex = fields.enterpriseH.toString(16).toUpperCase().padStart(2, '0');
  const iHex = fields.enterpriseI.toString(16).toUpperCase().padStart(2, '0');
  const pad = (fields.padding || '0000').toUpperCase().padStart(4, '0').slice(0, 4);

  const post = `${monthHex}${dayHex}${yearHex}${editionHex}${flagsHex}${hHex}${iHex}${pad}`;
  if (post.length !== 16) {
    throw new Error(`encoded payload length ${post.length} != 16`);
  }
  return post;
}

export function generateLongRaw(fields, cpuId) {
  const id = cpuId.slice(0, 7);
  const post = encodePostPermute(fields);
  const pre16 = inversePermuteI(post);
  const checksum = extractDigits(md5Hex(pre16 + id), 4);
  if (checksum.length !== 4) {
    throw new Error('could not derive 4-digit checksum from MD5');
  }
  return (pre16 + checksum).toUpperCase();
}

export function generateLongCode(fields, cpuId) {
  return formatLongCode(generateLongRaw(fields, cpuId));
}
