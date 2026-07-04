"""CadQuery model for a parametric, printable cake divider.

The model is generated as a full divider plus split printable parts. Split parts
are clipped from the full model and then receive matching tab/socket keys.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cadquery as cq


VALID_SLICES = {6, 8, 10, 12}
VALID_SPLITS = {2, 4}
VALID_FORMATS = {"step", "stl"}


@dataclass(frozen=True)
class DividerParameters:
    """User-facing parameters for the cake divider."""

    diameter_mm: float = 260.0
    slices: int = 8
    split_count: int = 4
    blade_height_mm: float = 18.0
    blade_thickness_mm: float = 2.8
    cutting_edge_mm: float = 0.65
    outer_ring_width_mm: float = 9.0
    hub_radius_mm: float = 17.0
    rib_width_mm: float = 4.2
    rib_height_mm: float = 3.0
    grip_height_mm: float = 4.0
    interlock_clearance_mm: float = 0.35

    def validate(self) -> None:
        if not 150 <= self.diameter_mm <= 400:
            raise ValueError("diameter_mm must be between 150 and 400 mm")
        if self.slices not in VALID_SLICES:
            raise ValueError(f"slices must be one of {sorted(VALID_SLICES)}")
        if self.split_count not in VALID_SPLITS:
            raise ValueError(f"split_count must be one of {sorted(VALID_SPLITS)}")
        if self.cutting_edge_mm <= 0 or self.cutting_edge_mm >= self.blade_thickness_mm:
            raise ValueError("cutting_edge_mm must be smaller than blade_thickness_mm")
        if self.outer_radius_mm - self.outer_ring_width_mm - self.hub_radius_mm < 45:
            raise ValueError("diameter_mm is too small for the selected hub and outer ring")
        if self.interlock_clearance_mm < 0:
            raise ValueError("interlock_clearance_mm must be non-negative")

    @property
    def outer_radius_mm(self) -> float:
        return self.diameter_mm / 2.0

    @property
    def usable_radius_mm(self) -> float:
        return self.outer_radius_mm - self.outer_ring_width_mm

    @property
    def rib_start_mm(self) -> float:
        return self.hub_radius_mm + 7.0

    @property
    def rib_end_mm(self) -> float:
        return self.usable_radius_mm - 7.0

    @property
    def grip_length_mm(self) -> float:
        return min(58.0, max(38.0, self.diameter_mm * 0.16))

    @property
    def grip_width_mm(self) -> float:
        return min(22.0, max(16.0, self.diameter_mm * 0.055))

    @property
    def max_height_mm(self) -> float:
        return self.blade_height_mm + self.grip_height_mm


@dataclass(frozen=True)
class DividerModels:
    full: cq.Workplane
    parts: tuple[cq.Workplane, ...]


def build_models(params: DividerParameters) -> DividerModels:
    """Build the full model and the requested split parts."""

    params.validate()
    full = _build_full_divider(params)
    parts = tuple(_build_split_part(full, params, index) for index in range(params.split_count))
    return DividerModels(full=full, parts=parts)


def export_models(
    models: DividerModels,
    params: DividerParameters,
    output_dir: Path | str,
    formats: Iterable[str] = ("stl", "step"),
    export_full: bool = True,
) -> list[Path]:
    """Export the full divider and all split parts."""

    params.validate()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    selected_formats = {fmt.lower() for fmt in formats}
    invalid_formats = selected_formats - VALID_FORMATS
    if invalid_formats:
        raise ValueError(f"Unsupported export formats: {sorted(invalid_formats)}")

    stem = _model_stem(params)
    written: list[Path] = []

    if export_full:
        for fmt in sorted(selected_formats):
            target = output_path / f"{stem}_full.{fmt}"
            cq.exporters.export(models.full, str(target))
            written.append(target)

    for part_number, part in enumerate(models.parts, start=1):
        for fmt in sorted(selected_formats):
            target = output_path / f"{stem}_split{params.split_count}_part{part_number:02d}.{fmt}"
            cq.exporters.export(part, str(target))
            written.append(target)

    return written


def _build_full_divider(params: DividerParameters) -> cq.Workplane:
    outer_ring = _outer_ring(params)
    hub = cq.Workplane("XY").circle(params.hub_radius_mm).extrude(params.blade_height_mm)
    model = outer_ring.union(hub)

    for index in range(params.slices):
        angle = 360.0 * index / params.slices
        model = model.union(_tapered_blade(angle, params))
        model = model.union(
            _oriented_box(
                angle_deg=angle,
                inner_radius=params.rib_start_mm,
                outer_radius=params.rib_end_mm,
                width=params.rib_width_mm,
                z=params.blade_height_mm,
                height=params.rib_height_mm,
            )
        )

    for index in range(params.split_count):
        angle = 360.0 * (index + 0.5) / params.split_count
        model = model.union(_grip_pad(angle, params))
        for offset in (-0.32, 0.0, 0.32):
            model = model.cut(_grip_groove(angle, offset, params))

    return model.clean()


def _build_split_part(full: cq.Workplane, params: DividerParameters, index: int) -> cq.Workplane:
    span = 360.0 / params.split_count
    gap_angle = math.degrees(params.interlock_clearance_mm / params.outer_radius_mm)
    start = index * span + gap_angle / 2.0
    end = (index + 1) * span - gap_angle / 2.0

    part = full.intersect(_sector_mask(start, end, params))

    # Each part has male keys on its end seam and matching sockets on its start seam.
    for inner_radius, outer_radius in _interlock_ranges(params):
        tab_depth = 6.0 + params.interlock_clearance_mm
        socket_depth = tab_depth + params.interlock_clearance_mm
        z = 1.0
        height = params.blade_height_mm - 1.0
        part = part.union(
            _interlock_prism(
                end,
                inner_radius,
                outer_radius,
                tab_depth,
                z,
                height,
            )
        )
        part = part.cut(
            _interlock_prism(
                start,
                inner_radius - params.interlock_clearance_mm,
                outer_radius + params.interlock_clearance_mm,
                socket_depth,
                z - 0.25,
                height + 0.5,
            )
        )

    return part.clean()


def _outer_ring(params: DividerParameters) -> cq.Workplane:
    ring = (
        cq.Workplane("XY")
        .circle(params.outer_radius_mm)
        .circle(params.usable_radius_mm)
        .extrude(params.blade_height_mm)
    )
    bevel = min(1.2, params.outer_ring_width_mm * 0.2)
    try:
        return ring.edges("<Z").chamfer(bevel)
    except Exception:
        return ring


def _tapered_blade(angle_deg: float, params: DividerParameters) -> cq.Workplane:
    inner = params.hub_radius_mm * 0.55
    outer = params.usable_radius_mm + 0.4
    bottom = _blade_wire(angle_deg, inner, outer, params.cutting_edge_mm, 0.0)
    top = _blade_wire(angle_deg, inner, outer, params.blade_thickness_mm, params.blade_height_mm)
    solid = cq.Solid.makeLoft([bottom, top], ruled=True)
    return cq.Workplane("XY").add(solid)


def _blade_wire(
    angle_deg: float,
    inner_radius: float,
    outer_radius: float,
    width: float,
    z: float,
) -> cq.Wire:
    angle = math.radians(angle_deg)
    radial = (math.cos(angle), math.sin(angle))
    normal = (-math.sin(angle), math.cos(angle))
    half_width = width / 2.0

    def point(radius: float, side: float) -> cq.Vector:
        return cq.Vector(
            radius * radial[0] + side * half_width * normal[0],
            radius * radial[1] + side * half_width * normal[1],
            z,
        )

    points = [
        point(inner_radius, 1.0),
        point(outer_radius, 1.0),
        point(outer_radius, -1.0),
        point(inner_radius, -1.0),
        point(inner_radius, 1.0),
    ]
    return cq.Wire.makePolygon(points)


def _oriented_box(
    angle_deg: float,
    inner_radius: float,
    outer_radius: float,
    width: float,
    z: float,
    height: float,
) -> cq.Workplane:
    length = outer_radius - inner_radius
    return (
        cq.Workplane("XY")
        .box(length, width, height, centered=(False, True, False))
        .translate((inner_radius, 0.0, z))
        .rotate((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), angle_deg)
    )


def _grip_pad(angle_deg: float, params: DividerParameters) -> cq.Workplane:
    center_radius = params.outer_radius_mm - params.outer_ring_width_mm / 2.0
    pad = _capsule_prism(
        angle_deg=angle_deg,
        center_radius=center_radius,
        length=params.grip_length_mm,
        width=params.grip_width_mm,
        z=params.blade_height_mm,
        height=params.grip_height_mm,
        segments=20,
    )
    try:
        return pad.edges(">Z").fillet(1.2)
    except Exception:
        return pad


def _grip_groove(angle_deg: float, radial_offset_factor: float, params: DividerParameters) -> cq.Workplane:
    center_radius = (
        params.outer_radius_mm
        - params.outer_ring_width_mm / 2.0
        + radial_offset_factor * params.grip_width_mm
    )
    return _capsule_prism(
        angle_deg=angle_deg,
        center_radius=center_radius,
        length=params.grip_length_mm * 0.55,
        width=2.2,
        z=params.blade_height_mm + params.grip_height_mm - 1.0,
        height=1.25,
        segments=10,
    )


def _capsule_prism(
    angle_deg: float,
    center_radius: float,
    length: float,
    width: float,
    z: float,
    height: float,
    segments: int,
) -> cq.Workplane:
    radius = width / 2.0
    straight = max(0.0, length / 2.0 - radius)
    local_points: list[tuple[float, float]] = []

    for index in range(segments + 1):
        theta = -math.pi / 2.0 + math.pi * index / segments
        local_points.append((straight + radius * math.cos(theta), radius * math.sin(theta)))
    for index in range(segments + 1):
        theta = math.pi / 2.0 + math.pi * index / segments
        local_points.append((-straight + radius * math.cos(theta), radius * math.sin(theta)))

    points = [_polar_local_to_xy(angle_deg, center_radius, tangent, radial) for tangent, radial in local_points]
    return cq.Workplane("XY", origin=(0.0, 0.0, z)).polyline(points).close().extrude(height)


def _sector_mask(start_deg: float, end_deg: float, params: DividerParameters) -> cq.Workplane:
    radius = params.outer_radius_mm + params.grip_width_mm + 12.0
    height = params.max_height_mm + 5.0
    span = end_deg - start_deg
    steps = max(12, int(abs(span) / 4.0))
    points = [(0.0, 0.0)]
    for index in range(steps + 1):
        angle = math.radians(start_deg + span * index / steps)
        points.append((radius * math.cos(angle), radius * math.sin(angle)))
    return cq.Workplane("XY", origin=(0.0, 0.0, -2.0)).polyline(points).close().extrude(height)


def _interlock_ranges(params: DividerParameters) -> tuple[tuple[float, float], tuple[float, float]]:
    center_outer = params.hub_radius_mm + 13.0
    outer_inner = params.outer_radius_mm - params.outer_ring_width_mm - 5.0
    return (
        (params.hub_radius_mm * 0.25, center_outer),
        (outer_inner, params.outer_radius_mm + 2.0),
    )


def _interlock_prism(
    seam_angle_deg: float,
    inner_radius: float,
    outer_radius: float,
    depth: float,
    z: float,
    height: float,
) -> cq.Workplane:
    points = [
        _polar_local_to_xy(seam_angle_deg, inner_radius, 0.0, 0.0),
        _polar_local_to_xy(seam_angle_deg, outer_radius, 0.0, 0.0),
        _polar_local_to_xy(seam_angle_deg, outer_radius, depth, 0.0),
        _polar_local_to_xy(seam_angle_deg, inner_radius, depth, 0.0),
    ]
    return cq.Workplane("XY", origin=(0.0, 0.0, z)).polyline(points).close().extrude(height)


def _polar_local_to_xy(
    angle_deg: float,
    center_radius: float,
    tangent_offset: float,
    radial_offset: float,
) -> tuple[float, float]:
    angle = math.radians(angle_deg)
    radial = (math.cos(angle), math.sin(angle))
    tangent = (-math.sin(angle), math.cos(angle))
    radius = center_radius + radial_offset
    return (
        radius * radial[0] + tangent_offset * tangent[0],
        radius * radial[1] + tangent_offset * tangent[1],
    )


def _model_stem(params: DividerParameters) -> str:
    diameter = _compact_number(params.diameter_mm)
    return f"cake_divider_{diameter}mm_{params.slices}_slices"


def _compact_number(value: float) -> str:
    return str(int(value)) if value == int(value) else f"{value:g}"
