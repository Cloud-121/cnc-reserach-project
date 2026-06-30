#!/usr/bin/env python3
"""Generate and verify Mozaik authorization codes (authorized security review only)."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from mozaik_license import (
    LongCodeFields,
    ShortCodeFields,
    SUCCESS_MAGIC,
    generate_long_code,
    generate_long_raw,
    generate_short_code,
    iter_edition_catalog,
    resolve_edition,
)

ROOT = Path(__file__).resolve().parent
MOZAIK_ROOT = Path(r"C:\Mozaik")
DEFAULT_DLL = MOZAIK_ROOT / "System" / "MozaikData.dll"


class MozaikDataBridge:
    """Load MozaikData.dll via pythonnet for machine IDs and validation."""

    def __init__(self, dll_path: Path = DEFAULT_DLL):
        if not dll_path.is_file():
            raise FileNotFoundError(f"MozaikData.dll not found: {dll_path}")
        try:
            import clr  # type: ignore
        except ImportError as exc:
            raise RuntimeError("pythonnet required: pip install pythonnet") from exc

        import System
        import System.Reflection as R

        self._System = System
        clr.AddReference(str(dll_path.resolve()))
        asm = System.Reflection.Assembly.LoadFrom(str(dll_path.resolve()))
        em_type = asm.GetType("em")
        if em_type is None:
            raise RuntimeError("Could not find type 'em' in MozaikData.dll")

        self._em_type = em_type
        self._flags = R.BindingFlags.Static | R.BindingFlags.Public | R.BindingFlags.NonPublic
        self._method_validate = self._find_method("a", 3, "Int16")
        self._method_cpu = self._find_method("e", 0, "String")
        self._method_fp = self._find_method("d", 0, "String")

    def _find_method(self, name: str, param_count: int, return_name: str):
        for method in self._em_type.GetMethods(self._flags):
            if method.Name != name:
                continue
            if method.GetParameters().Length != param_count:
                continue
            if method.ReturnType.Name != return_name:
                continue
            return method
        raise RuntimeError(f"Could not find em.{name}({param_count}) -> {return_name}")

    def _invoke0(self, method) -> object:
        return method.Invoke(None, self._System.Array[self._System.Object]([]))

    def get_cpu_id(self) -> str:
        return str(self._invoke0(self._method_cpu))

    def get_fingerprint(self) -> str:
        return str(self._invoke0(self._method_fp))

    def verify(self, code: str) -> dict:
        flag = self._System.Boolean(False)
        args = self._System.Array[self._System.Object]([code, False, flag])
        result = int(self._method_validate.Invoke(None, args))
        flag = bool(args[2])

        license_field = self._em_type.GetField("a")
        license_obj = license_field.GetValue(None)
        edition_enum = int(license_obj.a) if license_obj is not None else -1
        edition_name = str(license_obj.q()) if license_obj is not None else ""

        return {
            "result": result,
            "valid": result == SUCCESS_MAGIC and edition_enum not in (0, 5),
            "edition_enum": edition_enum,
            "edition_name": edition_name,
            "expired": flag,
        }


def parse_expiry(args: argparse.Namespace) -> tuple[int, int, int]:
    if args.expiry:
        expiry = date.fromisoformat(args.expiry)
        return expiry.month, expiry.day, expiry.year
    if args.month is None or args.day is None or args.year is None:
        raise ValueError("Provide --expiry YYYY-MM-DD or all of --month, --day, --year")
    return args.month, args.day, args.year


def resolve_cpu_id(args: argparse.Namespace, bridge: MozaikDataBridge | None) -> str:
    """Long-format codes bind to em.e() — 7-char CPU/machine key."""
    if args.cpu_id:
        cpu = args.cpu_id.strip()
        if len(cpu) > 7:
            print(f"Warning: truncating --cpu-id to 7 chars ({cpu[:7]})", file=sys.stderr)
        return cpu[:7]
    if args.user_id and len(args.user_id.strip()) == 7 and args.user_id.strip().isalnum():
        # Allow 7-char alphanumeric user/cpu ids directly
        return args.user_id.strip()[:7]
    if bridge is None:
        raise ValueError("Provide --cpu-id (7 chars) or --user-id when not using local machine defaults")
    return bridge.get_cpu_id()


def resolve_fingerprint(args: argparse.Namespace, bridge: MozaikDataBridge | None) -> str:
    """Short-format codes bind to em.d() fingerprint string."""
    if args.user_id:
        return args.user_id.strip()
    if args.fingerprint:
        return args.fingerprint.strip()
    if bridge is None:
        raise ValueError("Provide --user-id or --fingerprint for short-format codes")
    return bridge.get_fingerprint()


def build_long_fields(args: argparse.Namespace) -> tuple[LongCodeFields, str]:
    month, day, year = parse_expiry(args)
    code, ent_h, ent_i, display = resolve_edition(
        args.edition if args.edition_code is None else None,
        args.edition_code,
        enterprise=args.enterprise,
        enterprise_h=args.enterprise_h,
        enterprise_i=args.enterprise_i,
    )
    fields = LongCodeFields(
        month=month,
        day=day,
        year=year,
        edition_code=code,
        feature_flags=args.feature_flags,
        enterprise_h=ent_h,
        enterprise_i=ent_i,
        padding=args.padding,
    )
    return fields, display


def build_short_fields(args: argparse.Namespace) -> tuple[ShortCodeFields, str]:
    month, day, year = parse_expiry(args)
    year_offset = year - 2000
    if year_offset < 12 or year_offset > 25:
        raise ValueError("short-format year offset must be 12..25 (2012-2025)")
    edition = args.edition
    if args.edition_code is None and edition == "design_pro":
        edition = "design"
    code, _ent_h, _ent_i, display = resolve_edition(
        edition if args.edition_code is None else None,
        args.edition_code,
    )
    fields = ShortCodeFields(
        month=month,
        day=day,
        year_offset=year_offset,
        edition_code=code,
        feature_flag=args.feature_flag,
    )
    return fields, display


def add_field_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--user-id",
        "-u",
        help="User ID from About/State.dat (short-format binding). "
        "For long format, use --cpu-id unless this is a 7-char machine key.",
    )
    parser.add_argument(
        "--cpu-id",
        "-c",
        help="7-char machine CPU key (em.e) for long-format code binding",
    )
    parser.add_argument(
        "--fingerprint",
        help="Alternate fingerprint string (em.d) for short-format binding",
    )
    parser.add_argument(
        "--edition",
        "-e",
        default="design_pro",
        help="Edition preset name (run 'editions' subcommand for full list)",
    )
    parser.add_argument(
        "--edition-code",
        type=int,
        help="Raw edition payload code (overrides --edition). See 'editions' for code map.",
    )
    parser.add_argument(
        "--enterprise",
        action="store_true",
        help="Set enterprise_h=1 for Enterprise / CNC Operator (Ent.) display",
    )
    parser.add_argument("--expiry", help="Expiry date YYYY-MM-DD (default: 2099-12-31 for long)")
    parser.add_argument("--month", type=int, help="Expiry month 1-12")
    parser.add_argument("--day", type=int, help="Expiry day 1-31")
    parser.add_argument("--year", type=int, help="Expiry year e.g. 2099")
    parser.add_argument("--padding", default="0000", help="Long-format padding nibbles (4 hex chars)")
    parser.add_argument("--feature-flags", type=int, default=0, help="Long-format feature flag nibble")
    parser.add_argument("--enterprise-h", type=int, default=None, help="Long-format enterprise h field (1 = Enterprise)")
    parser.add_argument("--enterprise-i", type=int, default=None, help="Long-format enterprise i field")
    parser.add_argument("--feature-flag", type=int, default=1, help="Short-format feature flag digit")
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Do not verify against local MozaikData.dll (use when generating for another machine)",
    )


def cmd_ids(args: argparse.Namespace) -> int:
    bridge = MozaikDataBridge(Path(args.dll))
    print(f"CPU ID (em.e):        {bridge.get_cpu_id()}")
    print(f"User ID (em.d):       {bridge.get_fingerprint()}")
    print()
    print("Long-format codes bind to CPU ID (7 chars).")
    print("Short-format codes bind to User ID / fingerprint (em.d).")
    print("Run: python generate_auth_code.py editions")
    return 0


def cmd_editions(args: argparse.Namespace) -> int:
    print(f"{'Name':<28} {'Code':>4}  {'Ent':>3}  About-dialog label")
    print("-" * 72)
    for name, preset in iter_edition_catalog():
        ent = preset.enterprise_h if preset.enterprise_h else ""
        print(f"{name:<28} {preset.edition_code:>4}  {ent:>3}  {preset.display_name}")
        if preset.notes:
            print(f"{'':28} {'':>4}  {'':>3}  ({preset.notes})")
        for alias in preset.aliases:
            print(f"  alias: {alias}")
    print()
    print("Notes:")
    print("- Enterprise display requires enterprise_h=1 (--enterprise or *_enterprise presets).")
    print("- Standalone 'Mozaik Optimizer' is not produced by any edition code in v14.1.14.")
    print("  Use mfg_opt / cnc bundles; 'optimizer' is an alias for mfg_opt.")
    print("- Codes 27-38 are extended bundles with extra internal d/e/f flags.")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    bridge = None if args.skip_verify else MozaikDataBridge(Path(args.dll))
    if bridge and not args.expiry and args.month is None:
        args.expiry = args.expiry or "2099-12-31"

    fmt = args.format
    if fmt == "auto":
        fmt = "short" if args.user_id and len(args.user_id.strip()) > 7 else "long"

    if fmt == "long":
        return _generate_long(args, bridge)
    return _generate_short(args, bridge)


def _generate_long(args: argparse.Namespace, bridge: MozaikDataBridge | None) -> int:
    if not args.expiry and args.month is None:
        args.expiry = "2099-12-31"

    cpu_id = resolve_cpu_id(args, bridge)
    fields, expected_display = build_long_fields(args)
    raw = generate_long_raw(fields, cpu_id)
    dashed = generate_long_code(fields, cpu_id)

    print(f"Format:             long (24-char dashed)")
    print(f"CPU ID (binding):   {cpu_id}")
    if args.user_id:
        print(f"User ID (ref):      {args.user_id}")
    print(f"Edition preset:     {args.edition if args.edition_code is None else '(raw code)'}")
    print(f"Edition code:       {fields.edition_code}")
    print(f"Expected label:     {expected_display}")
    print(f"Expiry:             {fields.year:04d}-{fields.month:02d}-{fields.day:02d}")
    print(f"Padding:            {fields.padding}")
    print(f"Feature flags:      {fields.feature_flags}")
    print(f"Enterprise h/i:     {fields.enterprise_h}/{fields.enterprise_i}")
    print(f"Raw (20):           {raw}")
    print(f"Authorization code: {dashed}")

    if args.skip_verify:
        print("Skipped local DLL verification (--skip-verify)")
        return 0

    assert bridge is not None
    info = bridge.verify(dashed)
    print(f"DLL verify result:  {info['result']} (valid={info['valid']})")
    if info["valid"]:
        print(f"Licensed as:        {info['edition_name']}")
        return 0

    if cpu_id != bridge.get_cpu_id():
        print(
            "Verification failed: code is bound to a different CPU ID than this machine. "
            "Use --skip-verify if generating for another PC.",
            file=sys.stderr,
        )
        return 1

    print("Verification FAILED — trying padding search...", file=sys.stderr)
    for pad in range(0, 4096):
        fields.padding = format(pad, "04X")
        candidate = generate_long_code(fields, cpu_id)
        info = bridge.verify(candidate)
        if info["valid"]:
            print(f"Recovered with padding={fields.padding}")
            print(f"Authorization code: {candidate}")
            print(f"Licensed as:        {info['edition_name']}")
            return 0

    print("Could not produce valid code", file=sys.stderr)
    return 1


def _generate_short(args: argparse.Namespace, bridge: MozaikDataBridge | None) -> int:
    if not args.expiry and args.month is None:
        args.expiry = "2025-12-31"

    fingerprint = resolve_fingerprint(args, bridge)
    fields, expected_display = build_short_fields(args)
    code = generate_short_code(fields, fingerprint)

    print(f"Format:             short (14-char dashed)")
    print(f"User ID (binding):  {fingerprint}")
    print(f"Edition preset:     {args.edition if args.edition_code is None else '(raw code)'}")
    print(f"Edition code:       {fields.edition_code}")
    print(f"Expected label:     {expected_display}")
    print(f"Expiry:             20{fields.year_offset:02d}-{fields.month:02d}-{fields.day:02d}")
    print(f"Feature flag:       {fields.feature_flag}")
    print(f"Authorization code: {code}")

    if args.skip_verify:
        print("Skipped local DLL verification (--skip-verify)")
        return 0

    assert bridge is not None
    info = bridge.verify(code)
    print(f"DLL verify result:  {info['result']} (valid={info['valid']})")
    if not info["valid"] and fingerprint != bridge.get_fingerprint():
        print(
            "Verification failed: code is bound to a different User ID than this machine. "
            "Use --skip-verify if generating for another PC.",
            file=sys.stderr,
        )
    return 0 if info["valid"] else 1


def cmd_verify(args: argparse.Namespace) -> int:
    bridge = MozaikDataBridge(Path(args.dll))
    info = bridge.verify(args.code)
    print(f"Code:              {args.code}")
    print(f"CPU ID (em.e):     {bridge.get_cpu_id()}")
    print(f"User ID (em.d):    {bridge.get_fingerprint()}")
    print(f"Result:            {info['result']}")
    print(f"Valid:             {info['valid']}")
    print(f"Edition enum:      {info['edition_enum']}")
    print(f"Edition name:      {info['edition_name']}")
    print(f"Expired flag:      {info['expired']}")
    return 0 if info["valid"] else 1


def cmd_bruteforce_padding(args: argparse.Namespace) -> int:
    bridge = MozaikDataBridge(Path(args.dll))
    cpu_id = resolve_cpu_id(args, bridge)
    fields, _display = build_long_fields(args)

    for pad in range(0, 65536):
        fields.padding = format(pad, "04X")
        dashed = generate_long_code(fields, cpu_id)
        info = bridge.verify(dashed)
        if info["valid"]:
            print(f"FOUND padding={fields.padding} code={dashed}")
            print(f"Licensed as: {info['edition_name']}")
            return 0
    print("No valid padding found in 0000-FFFF", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mozaik auth code generator (authorized security review only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_auth_code.py ids
  python generate_auth_code.py editions
  python generate_auth_code.py generate --cpu-id A472DBC --edition cnc_enterprise --expiry 2099-12-31
  python generate_auth_code.py generate --cpu-id A472DBC --edition design_pro --enterprise --expiry 2099-12-31
  python generate_auth_code.py generate -u 660340596 --format short --edition design --expiry 2025-12-31
  python generate_auth_code.py generate -c A472DBC --edition-code 4 --month 12 --day 31 --year 2099
  python generate_auth_code.py generate -c OTHERID --skip-verify --expiry 2099-12-31
  python generate_auth_code.py verify 610C-0000-0004-030F-1525
""",
    )
    parser.add_argument("--dll", default=str(DEFAULT_DLL), help="Path to unpatched MozaikData.dll")
    sub = parser.add_subparsers(dest="command", required=True)

    ids = sub.add_parser("ids", help="Show this machine's CPU ID and User ID")
    ids.set_defaults(func=cmd_ids)

    ed = sub.add_parser("editions", help="List all edition presets and payload codes")
    ed.set_defaults(func=cmd_editions)

    gen = sub.add_parser("generate", help="Generate authorization code with custom fields")
    gen.add_argument(
        "--format",
        choices=("auto", "long", "short"),
        default="auto",
        help="Code format: long=24-char (5 boxes), short=14-char (3 boxes)",
    )
    add_field_args(gen)
    gen.set_defaults(func=cmd_generate)

    ver = sub.add_parser("verify", help="Verify a code via MozaikData.dll")
    ver.add_argument("code")
    ver.set_defaults(func=cmd_verify)

    bf = sub.add_parser("bruteforce-padding", help="Search padding space (debug)")
    add_field_args(bf)
    bf.set_defaults(func=cmd_bruteforce_padding)

    # Backward-compatible alias
    gen_s = sub.add_parser("generate-short", help="Alias for generate --format short")
    add_field_args(gen_s)
    gen_s.set_defaults(func=cmd_generate, format="short")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
