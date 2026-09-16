import uuid
from datetime import date
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.routes.recommendations import create_recommendation_snapshot
from app.main import app
from app.schemas.donation_delivery_queue import DonationDeliveryQueueRead


def build_queue(
    offer_id: uuid.UUID,
    report_date: date,
) -> DonationDeliveryQueueRead:
    return DonationDeliveryQueueRead(
        donation_offer_id=offer_id,
        offer_status="open",
        as_of_date=report_date,
        tie_window_days=3,
        offered_category_count=1,
        total_offered_pounds=100.0,
        total=0,
        recipients=[],
    )


def test_recommendation_route_is_registered() -> None:
    paths = app.openapi()["paths"]
    path = "/api/v1/donation-offers/{offer_id}/recommendations"

    assert "post" in paths[path]
    assert paths[path]["post"]["responses"]["201"]


def test_create_recommendation_snapshot_commits() -> None:
    offer_id = uuid.uuid4()
    run_id = uuid.uuid4()
    report_date = date(2026, 9, 15)
    queue = build_queue(offer_id, report_date)
    offered_items = [
        {
            "food_category_code": "produce",
            "category_name": "Produce",
            "pounds": 100.0,
        }
    ]
    run = Mock(
        id=run_id,
        policy_version="v1",
    )
    db = Mock(spec=Session)

    with (
        patch(
            "app.api.routes.recommendations.get_donation_delivery_queue",
            return_value=queue,
        ) as get_queue,
        patch(
            "app.api.routes.recommendations.load_offered_items_snapshot",
            return_value=offered_items,
        ) as load_items,
        patch(
            "app.api.routes.recommendations.save_recommendation_snapshot",
            return_value=run,
        ) as save_snapshot,
    ):
        response = create_recommendation_snapshot(
            offer_id=offer_id,
            db=db,
            as_of=report_date,
        )

    get_queue.assert_called_once_with(
        offer_id=offer_id,
        db=db,
        as_of=report_date,
    )
    load_items.assert_called_once_with(
        db=db,
        offer_id=offer_id,
    )
    save_snapshot.assert_called_once_with(
        db,
        queue=queue,
        offered_items_snapshot=offered_items,
    )
    db.commit.assert_called_once_with()
    db.rollback.assert_not_called()
    assert response.recommendation_run_id == run_id
    assert response.policy_version == "v1"
    assert response.queue == queue


def test_create_recommendation_snapshot_rolls_back_database_error() -> None:
    offer_id = uuid.uuid4()
    report_date = date(2026, 9, 15)
    queue = build_queue(offer_id, report_date)
    offered_items = [
        {
            "food_category_code": "produce",
            "category_name": "Produce",
            "pounds": 100.0,
        }
    ]
    db = Mock(spec=Session)

    with (
        patch(
            "app.api.routes.recommendations.get_donation_delivery_queue",
            return_value=queue,
        ),
        patch(
            "app.api.routes.recommendations.load_offered_items_snapshot",
            return_value=offered_items,
        ),
        patch(
            "app.api.routes.recommendations.save_recommendation_snapshot",
            side_effect=SQLAlchemyError("database failure"),
        ),
        pytest.raises(HTTPException) as error_info,
    ):
        create_recommendation_snapshot(
            offer_id=offer_id,
            db=db,
            as_of=report_date,
        )

    assert error_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert error_info.value.detail == "recommendation snapshot could not be saved"
    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()