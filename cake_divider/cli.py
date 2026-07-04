"""Command line interface for building CakeDivider exports."""

from __future__ import annotations

import argparse
from pathlib import Path

from .model import DividerParameters, VALID_FORMATS, VALID_SLICES, VALID_SPLITS, build_models, export_models


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a parametric CadQuery cake divider.")
    parser.add_argument("--diameter", type=float, default=260.0, help="Outer diameter in mm, 150-400.")
    parser.add_argument(
        "--slices",
        type=int,
        choices=sorted(VALID_SLICES),
        default=8,
        help="Number of cake slices.",
    )
    parser.add_argument(
        "--split",
        type=int,
        choices=sorted(VALID_SPLITS),
        default=4,
        help="Number of interlocking printable parts.",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=sorted(VALID_FORMATS),
        default=["stl", "step"],
        help="Export formats.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist"),
        help="Directory for generated STEP/STL files.",
    )
    parser.add_argument(
        "--no-full",
        action="store_true",
        help="Only export split parts, not the full reference model.",
    )
    parser.add_argument("--blade-height", type=float, default=18.0, help="Blade height in mm.")
    parser.add_argument("--blade-thickness", type=float, default=2.8, help="Top blade thickness in mm.")
    parser.add_argument("--cutting-edge", type=float, default=0.65, help="Lower cutting edge thickness in mm.")
    parser.add_argument("--clearance", type=float, default=0.35, help="Interlock clearance in mm.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    params = DividerParameters(
        diameter_mm=args.diameter,
        slices=args.slices,
        split_count=args.split,
        blade_height_mm=args.blade_height,
        blade_thickness_mm=args.blade_thickness,
        cutting_edge_mm=args.cutting_edge,
        interlock_clearance_mm=args.clearance,
    )
    models = build_models(params)
    written = export_models(
        models,
        params,
        args.output_dir,
        formats=args.formats,
        export_full=not args.no_full,
    )
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
