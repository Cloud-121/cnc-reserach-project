"""Pure-Python port of MozaikData.em license helpers (review / research only)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable

SUCCESS_MAGIC = 7675


@dataclass
class LicenseState:
    """Subset of em.b fields after em.a(b, edition_code) runs."""

    tier: int = 0  # em.a enum: 0=unset, 1=kitchen..5=cnc_operator
    mfg_b: bool = False
    mfg_c: bool = False
    d_flag: bool = False
    e_flag: bool = False
    f_flag: bool = False
    enterprise_h: int = 0


def apply_edition_code(state: LicenseState, edition_code: int) -> None:
    """Port of em.a(b, long) in MozaikData.dll."""
    state.tier = 0
    state.mfg_b = False
    state.mfg_c = False
    state.d_flag = False
    state.e_flag = False
    state.f_flag = False

    code = edition_code
    if code == 1:
        state.tier = 1
    if code == 2:
        state.tier = 2
    if code == 4:
        state.tier = 3
    if (8 <= code <= 14) or code == 22 or (30 <= code <= 32) or (36 <= code <= 38):
        state.tier = 4
    if (16 <= code <= 20) or code == 24 or (27 <= code <= 29) or (33 <= code <= 35):
        state.tier = 5
    if 27 <= code <= 32:
        state.d_flag = True
    if 33 <= code <= 38:
        state.d_flag = True
        state.e_flag = True
    if code in (12, 14, 18, 20, 22, 24) or (27 <= code <= 38):
        state.mfg_b = True
    if code in (20, 14, 22, 24, 28, 29, 31, 32, 34, 35, 37, 38):
        state.mfg_c = True
    if code in (22, 24, 32, 29, 35, 38):
        state.f_flag = True


def edition_display_name(edition_code: int, enterprise_h: int = 0) -> str:
    """Port of em.b.q() display logic for a decoded edition payload code."""
    state = LicenseState(enterprise_h=enterprise_h)
    apply_edition_code(state, edition_code)

    names: list[str] = []
    if state.tier == 1:
        names.append("Kitchen Sketch")
    if state.tier == 2:
        names.append("Mozaik Design")
    if state.tier == 3:
        names.append("Mozaik Design Pro")
    if state.tier == 4 and not state.mfg_c and not state.mfg_b:
        names.append("Mozaik Manufacturing")
    if state.tier == 4 and state.mfg_c and not state.mfg_b:
        names.append("Mozaik Optimizer")
    if state.tier == 4 and not state.mfg_c and state.mfg_b:
        names.append("Mozaik MFG+OPT")
    if state.tier == 4 and state.mfg_c and state.mfg_b:
        names.append("Mozaik CNC")
    if state.tier == 5:
        names.append("Mozaik CNC Operator")
    if state.enterprise_h == 1 and state.tier != 5:
        names.append("Mozaik Enterprise")
    if state.enterprise_h == 1 and state.tier == 5:
        names.append("Mozaik CNC Operator (Ent.)")
    return names[-1] if names else f"(unknown code {edition_code})"


@dataclass(frozen=True)
class EditionPreset:
    edition_code: int
    display_name: str
    enterprise_h: int = 0
    enterprise_i: int = 0
    notes: str = ""
    aliases: tuple[str, ...] = field(default_factory=tuple)


def _preset(
    name: str,
    code: int,
    *,
    enterprise_h: int = 0,
    enterprise_i: int = 0,
    notes: str = "",
    aliases: tuple[str, ...] = (),
) -> tuple[str, EditionPreset]:
    display = edition_display_name(code, enterprise_h)
    return name, EditionPreset(
        edition_code=code,
        display_name=display,
        enterprise_h=enterprise_h,
        enterprise_i=enterprise_i,
        notes=notes,
        aliases=aliases,
    )


_PRESET_ITEMS: list[tuple[str, EditionPreset]] = [
    _preset("kitchen_sketch", 1),
    _preset("kitchen_sketch_enterprise", 1, enterprise_h=1),
    _preset("design", 2),
    _preset("design_enterprise", 2, enterprise_h=1),
    _preset("design_pro", 4),
    _preset("design_pro_enterprise", 4, enterprise_h=1),
    _preset("manufacturing", 8),
    _preset("manufacturing_enterprise", 8, enterprise_h=1),
    _preset(
        "manufacturing_10",
        10,
        notes="Code 10 is manufacturing-tier in v14.1.14 (not Optimizer-only).",
    ),
    _preset("mfg_opt", 12),
    _preset("mfg_opt_enterprise", 12, enterprise_h=1),
    _preset("cnc", 14),
    _preset("cnc_enterprise", 14, enterprise_h=1),
    _preset("cnc_operator", 16),
    _preset("cnc_operator_enterprise", 16, enterprise_h=1),
    _preset("cnc_bundle_22", 22, notes="Manufacturing-tier CNC bundle with extra f-flag."),
    _preset("cnc_operator_24", 24, notes="CNC Operator bundle with mfg_b/c/f flags."),
    _preset("cnc_operator_27", 27, notes="Extended CNC Operator bundle (d-flag)."),
    _preset("cnc_operator_28", 28),
    _preset("cnc_operator_29", 29),
    _preset("mfg_opt_plus", 30, notes="Extended MFG+OPT bundle (d-flag)."),
    _preset("cnc_plus", 31, notes="Extended CNC bundle (d-flag)."),
    _preset("cnc_full", 32, notes="Extended CNC bundle (d/e/f flags)."),
    _preset("cnc_operator_33", 33, notes="Extended CNC Operator bundle (d/e flags)."),
    _preset("cnc_operator_34", 34),
    _preset("cnc_operator_35", 35),
    _preset("mfg_opt_enterprise_plus", 36, notes="Extended MFG+OPT bundle (d/e flags)."),
    _preset("cnc_enterprise_plus", 37, notes="Extended CNC bundle (d/e flags)."),
    _preset("cnc_full_enterprise", 38, notes="Extended CNC bundle (d/e/f flags)."),
    _preset(
        "optimizer",
        12,
        aliases=("optimizer_bundle",),
        notes="Alias for mfg_opt. Standalone 'Mozaik Optimizer' UI is not reachable from edition codes alone in v14.1.14.",
    ),
]

EDITION_PRESETS: dict[str, EditionPreset] = {}
for preset_name, preset in _PRESET_ITEMS:
    EDITION_PRESETS[preset_name] = preset
    for alias in preset.aliases:
        EDITION_PRESETS[alias] = preset

# Primary CLI names -> edition payload code (backward compatible)
EDITION_CODES: dict[str, int] = {name: preset.edition_code for name, preset in _PRESET_ITEMS}


def resolve_edition(
    edition: str | None = None,
    edition_code: int | None = None,
    *,
    enterprise: bool = False,
    enterprise_h: int | None = None,
    enterprise_i: int | None = None,
) -> tuple[int, int, int, str]:
    """Resolve edition name/code into payload fields and expected About-dialog label."""
    preset: EditionPreset | None = None

    if edition_code is not None:
        code = edition_code
    else:
        if edition is None:
            edition = "design_pro"
        key = edition.lower().replace(" ", "_").replace("+", "_")
        if key not in EDITION_PRESETS:
            valid = ", ".join(sorted(EDITION_PRESETS))
            raise ValueError(f"Unknown edition {edition!r}; expected one of: {valid}")
        preset = EDITION_PRESETS[key]
        code = preset.edition_code

    if enterprise_h is not None:
        ent_h = enterprise_h
    elif enterprise:
        ent_h = 1
    elif preset is not None:
        ent_h = preset.enterprise_h
    else:
        ent_h = 0

    if enterprise_i is not None:
        ent_i = enterprise_i
    elif preset is not None:
        ent_i = preset.enterprise_i
    else:
        ent_i = 0

    display = edition_display_name(code, ent_h)
    return code, ent_h, ent_i, display


def iter_edition_catalog() -> list[tuple[str, EditionPreset]]:
    """Unique preset entries for listing (aliases deduplicated)."""
    seen: set[int] = set()
    rows: list[tuple[str, EditionPreset]] = []
    for name, preset in _PRESET_ITEMS:
        token = id(preset)
        if token in seen:
            continue
        seen.add(token)
        rows.append((name, preset))
    return rows


def strip_dashes(value: str) -> str:
    while "-" in value:
        value = value.replace("-", "")
    return value


def md5_hex(value: str) -> str:
    digest = hashlib.md5(value.encode("utf-8")).digest()
    return digest.hex().upper()


def extract_digits(value: str, count: int) -> str:
    out: list[str] = []
    for ch in value:
        if ch.isdigit():
            out.append(ch)
            if len(out) == count:
                return "".join(out)
    return ""


def parse_hex(value: str) -> int:
    return int(value, 16)


def swap_chars(value: str, pos1: int, pos2: int) -> str:
    """1-based positions, matches em.a(string, short, short)."""
    if len(value) < pos2:
        return value
    chars = list(value)
    i, j = pos1 - 1, pos2 - 1
    chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


def permute_i(value: str) -> str:
    """em.i(string) — long-format permutation."""
    if len(value) < 16:
        return ""
    value = swap_chars(value, 1, 4)
    value = swap_chars(value, 3, 16)
    value = swap_chars(value, 5, 14)
    value = swap_chars(value, 7, 12)
    value = swap_chars(value, 8, 10)
    return value


def permute_h(value: str) -> str:
    """em.h(string) — short-format permutation."""
    if len(value) < 12:
        return ""
    value = swap_chars(value, 1, 12)
    value = swap_chars(value, 3, 10)
    value = swap_chars(value, 5, 8)
    return value


def inverse_permute_i(value: str) -> str:
    """Inverse of permute_i (swaps are self-inverse, reverse order)."""
    if len(value) < 16:
        return ""
    value = swap_chars(value, 8, 10)
    value = swap_chars(value, 7, 12)
    value = swap_chars(value, 5, 14)
    value = swap_chars(value, 3, 16)
    value = swap_chars(value, 1, 4)
    return value


def inverse_permute_h(value: str) -> str:
    if len(value) < 12:
        return ""
    value = swap_chars(value, 5, 8)
    value = swap_chars(value, 3, 10)
    value = swap_chars(value, 1, 12)
    return value


def format_dashed(raw: str, groups: Iterable[int]) -> str:
    parts: list[str] = []
    idx = 0
    for size in groups:
        parts.append(raw[idx : idx + size])
        idx += size
    return "-".join(parts)


def format_long_code(raw20: str) -> str:
    raw20 = raw20.upper()
    if len(raw20) != 20:
        raise ValueError("long code must be 20 hex chars")
    return format_dashed(raw20, (4, 4, 4, 4, 4))


def format_short_code(raw12: str) -> str:
    raw12 = raw12.upper()
    if len(raw12) != 12:
        raise ValueError("short code must be 12 hex chars")
    return format_dashed(raw12, (4, 4, 4))


@dataclass
class LongCodeFields:
    month: int
    day: int
    year: int
    edition_code: int
    feature_flags: int = 0
    enterprise_h: int = 0
    enterprise_i: int = 0
    padding: str = "0000"

    @classmethod
    def from_edition_name(cls, edition: str, expiry: date, *, enterprise: bool = False) -> LongCodeFields:
        code, ent_h, ent_i, _display = resolve_edition(edition, enterprise=enterprise)
        return cls(
            month=expiry.month,
            day=expiry.day,
            year=expiry.year,
            edition_code=code,
            enterprise_h=ent_h,
            enterprise_i=ent_i,
        )

    @classmethod
    def from_values(
        cls,
        *,
        month: int,
        day: int,
        year: int,
        edition: str | None = None,
        edition_code: int | None = None,
        feature_flags: int = 0,
        enterprise: bool = False,
        enterprise_h: int | None = None,
        enterprise_i: int | None = None,
        padding: str = "0000",
    ) -> LongCodeFields:
        code, ent_h, ent_i, _display = resolve_edition(
            edition,
            edition_code,
            enterprise=enterprise,
            enterprise_h=enterprise_h,
            enterprise_i=enterprise_i,
        )
        return cls(
            month=month,
            day=day,
            year=year,
            edition_code=code,
            feature_flags=feature_flags,
            enterprise_h=ent_h,
            enterprise_i=ent_i,
            padding=padding,
        )


def encode_post_permute(fields: LongCodeFields) -> str:
    """Build the 16-char logical payload at post-i() layout (positions 0-15)."""
    year_offset = fields.year - 2000
    if year_offset < 0 or year_offset > 255:
        raise ValueError("year must be between 2000 and 2255")

    month_hex = format(fields.month, "X")
    day_hex = format(fields.day, "02X")
    year_hex = format(year_offset, "02X")
    edition_hex = format(fields.edition_code, "02X")
    flags_hex = format(fields.feature_flags, "X")
    h_hex = format(fields.enterprise_h, "02X")
    i_hex = format(fields.enterprise_i, "02X")
    padding = (fields.padding or "0000").upper().zfill(4)[:4]

    post = f"{month_hex}{day_hex}{year_hex}{edition_hex}{flags_hex}{h_hex}{i_hex}{padding}"
    if len(post) != 16:
        raise ValueError(f"encoded payload length {len(post)} != 16")
    return post


def generate_long_raw(fields: LongCodeFields, cpu_id: str) -> str:
    """Generate 20-char uppercase hex code bound to cpu_id."""
    cpu_id = cpu_id[:7]
    post = encode_post_permute(fields)
    pre16 = inverse_permute_i(post)
    checksum = extract_digits(md5_hex(pre16 + cpu_id), 4)
    if len(checksum) != 4:
        raise RuntimeError("could not derive 4-digit checksum from MD5")
    return (pre16 + checksum).upper()


def generate_long_code(fields: LongCodeFields, cpu_id: str) -> str:
    return format_long_code(generate_long_raw(fields, cpu_id))


@dataclass
class ShortCodeFields:
    month: int
    day: int
    year_offset: int  # years since 2000, stored in 2-digit field with constraints 12-25 in validator
    edition_code: int
    feature_flag: int = 1

    @classmethod
    def from_edition_name(cls, edition: str, expiry: date) -> ShortCodeFields:
        code, _ent_h, _ent_i, _display = resolve_edition(edition)
        year_offset = expiry.year - 2000
        if year_offset < 12 or year_offset > 25:
            raise ValueError("short-format year offset must be 12..25 (2012-2025)")
        return cls(
            month=expiry.month,
            day=expiry.day,
            year_offset=year_offset,
            edition_code=code,
        )

    @classmethod
    def from_values(
        cls,
        *,
        month: int,
        day: int,
        year: int,
        edition: str | None = None,
        edition_code: int | None = None,
        feature_flag: int = 1,
    ) -> ShortCodeFields:
        code, _ent_h, _ent_i, _display = resolve_edition(edition, edition_code)
        year_offset = year - 2000
        if year_offset < 12 or year_offset > 25:
            raise ValueError("short-format year offset must be 12..25 (2012-2025)")
        return cls(
            month=month,
            day=day,
            year_offset=year_offset,
            edition_code=code,
            feature_flag=feature_flag,
        )


def encode_short_post_permute(fields: ShortCodeFields) -> str:
    """9 chars before checksum in post-h() layout."""
    text = (
        f"{fields.day:02d}"
        f"{fields.month:02d}"
        f"{fields.year_offset:02d}"
        f"{fields.edition_code:02d}"
        f"{fields.feature_flag:d}"
    )
    if len(text) != 9:
        raise ValueError("short payload must be 9 chars")
    return text


def generate_short_raw(fields: ShortCodeFields, fingerprint: str) -> str:
    post9 = encode_short_post_permute(fields)
    pre12 = inverse_permute_h(post9 + "000")  # 12 chars: 9 payload + 3 placeholder for checksum slots
    # Checksum uses fingerprint + date6 + edition2 + flag1 = post9
    checksum = extract_digits(md5_hex(fingerprint + post9), 3)
    if len(checksum) != 3:
        raise RuntimeError("could not derive 3-digit checksum from MD5")
    raw = pre12[:9] + checksum
    return raw.upper()


def generate_short_code(fields: ShortCodeFields, fingerprint: str) -> str:
    return format_short_code(generate_short_raw(fields, fingerprint))
