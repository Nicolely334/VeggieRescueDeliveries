from pathlib import Path
from typing import Any

import pytest
from openpyxl import Workbook

from app.importers.import_farms import (
    FarmImportRow,
    load_farm_rows,
    synchronize_farms,
)
from app.models.farm import Farm


class FakeScalarResult:
    def __init__(self, values: list[Farm]) -> None:
        self.values = values

    def all(self) -> list[Farm]:
        return self.values


class FakeSession:
    def __init__(self, existing_farms: list[Farm] | None = None) -> None:
        self.existing_farms = existing_farms or []
        self.added: list[Farm] = []
        self.flushed = False
        self.committed = False
        self.rolled_back = False

    def scalars(self, _statement: Any) -> FakeScalarResult:
        return FakeScalarResult(self.existing_farms)

    def add(self, farm: Farm) -> None:
        self.added.append(farm)

    def flush(self) -> None:
        self.flushed = True

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def write_donor_workbook(
    file_path: Path,
    rows: list[list[object]],
) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Food_Donors"
    worksheet.append(
        [
            "Updated",
            "Farmers giving often",
            "Initials",
            "Added",
            "DonorName",
            "StreetAddress",
            "City",
            "State",
            "Zip",
            "Mailing Address",
            "City",
        ]
    )

    for row in rows:
        worksheet.append(row)

    workbook.save(file_path)
    workbook.close()


def test_load_farm_rows_reads_donor_directory(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "donors.xlsx"
    write_donor_workbook(
        file_path,
        [
            [
                None,
                None,
                None,
                None,
                "Blue Dog Farm",
                "123 Farm Road",
                "Buellton",
                "CA",
                "93427",
                None,
                "Different Mailing City",
            ]
        ],
    )

    rows = load_farm_rows(file_path)

    assert rows == [
        FarmImportRow(
            name="Blue Dog Farm",
            address="123 Farm Road",
            city="Buellton",
            region="CA",
        )
    ]


def test_load_farm_rows_rejects_duplicate_names(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "donors.xlsx"
    write_donor_workbook(
        file_path,
        [
            [None, None, None, None, "Blue Dog Farm", None, None, "CA"],
            [None, None, None, None, " blue dog farm ", None, None, "CA"],
        ],
    )

    with pytest.raises(ValueError, match="duplicate donor name"):
        load_farm_rows(file_path)


def test_synchronize_farms_creates_and_updates_without_committing() -> None:
    existing_farm = Farm(
        name="Blue Dog Farm",
        address=None,
        city="Buellton",
        region="CA",
        is_active=True,
    )
    session = FakeSession([existing_farm])

    summary = synchronize_farms(
        db=session,  # type: ignore[arg-type]
        rows=[
            FarmImportRow(
                name="Blue Dog Farm",
                address="123 Farm Road",
                city="Buellton",
                region="CA",
            ),
            FarmImportRow(
                name="New Farm",
                address=None,
                city="Santa Maria",
                region="CA",
            ),
        ],
        commit=False,
    )

    assert summary == {
        "source_rows": 2,
        "farms_created": 1,
        "farms_updated": 1,
        "farms_unchanged": 0,
        "committed": False,
    }
    assert existing_farm.address == "123 Farm Road"
    assert len(session.added) == 1
    assert session.added[0].name == "New Farm"
    assert session.flushed is True
    assert session.committed is False
    assert session.rolled_back is True