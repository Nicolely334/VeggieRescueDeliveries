from pydantic import BaseModel


class DeliveryRead(BaseModel):
    id: str
    delivery_date: str
    recipient: str
    location: str
    produce_pounds: float | None
    packaged_pounds: float | None
    driver: str
    vehicle: str
    status: str


class DeliveryListRead(BaseModel):
    total: int
    deliveries: list[DeliveryRead]