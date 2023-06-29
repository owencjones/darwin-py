from json import loads
from pathlib import Path
from tkinter import W
from uuid import UUID

import pytest

from darwin.future.data_objects.workflow import (
    WFStage,
)

test_data_path: Path = Path(__file__).parent / "data"
validate_json = test_data_path / "stage.json"


def test_file_exists() -> None:
    # This is a test sanity check to make sure the file exists
    # Helps avoids headaches when debugging tests
    assert validate_json.exists()


def test_WFStage_validates_from_valid_json() -> None:
    WFStage.parse_file(validate_json)
    assert True


def test_casts_strings_to_uuids_as_needed() -> None:
    parsed_stage = WFStage.parse_file(validate_json)
    assert isinstance(parsed_stage.id, UUID)
    assert str(parsed_stage.id) == "e69d3ebe-6ab9-4159-b44f-2bf84d29bb20"


def test_raises_with_invalid_uuid() -> None:
    dict_from_json = loads(validate_json.read_text())
    dict_from_json["id"] = "not-a-uuid"

    with pytest.raises(ValueError) as excinfo:
        WFStage.parse_obj(dict_from_json)

    assert "not a valid uuid" in str(excinfo.value)
    assert str(excinfo.value).startswith("1 validation error for WFStage\nid")