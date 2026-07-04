import pytest

from cake_divider.model import DividerParameters


def test_accepts_supported_configurations() -> None:
    for slices in (6, 8, 10, 12):
        for split_count in (2, 4):
            DividerParameters(diameter_mm=260, slices=slices, split_count=split_count).validate()


def test_rejects_unsupported_diameter() -> None:
    with pytest.raises(ValueError):
        DividerParameters(diameter_mm=149).validate()


def test_rejects_unsupported_slice_count() -> None:
    with pytest.raises(ValueError):
        DividerParameters(slices=7).validate()
