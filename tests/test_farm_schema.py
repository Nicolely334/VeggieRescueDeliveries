import pytest
from pydantic import ValidationError

from app.schemas.farm import FarmCreate


def test_farm_accepts_valid_data() -> None:
    farm = FarmCreate(
        name="  Sunrise Farm  ",
        address="  100 Farm Road  ",
        city="  Santa Maria  ",
        region="  North County  ",
        latitude=34.953,
        longitude=-120.435,
    )

    assert farm.name == "Sunrise Farm"
    assert farm.address == "100 Farm Road"
    assert farm.city == "Santa Maria"
    assert farm.region == "North County"
    assert farm.is_active is True


def test_farm_converts_blank_optional_text_to_none() -> None:
    farm = FarmCreate(
        name="Sunrise Farm",
        address="   ",
        city="",
    )

    assert farm.address is None
    assert farm.city is None


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("latitude", -91),
        ("latitude", 91),
        ("longitude", -181),
        ("longitude", 181),
    ],
)
def test_farm_rejects_invalid_coordinates(
    field_name: str,
    value: float,
) -> None:
    with pytest.raises(ValidationError):
        FarmCreate(
            name="Sunrise Farm",
            **{field_name: value},
        )


def test_farm_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        FarmCreate(
            name="   ",
        )
