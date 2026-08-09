"""Input normalization for reservation requests."""

from errors import ReservationError


def normalize_request(raw: dict) -> dict:
    try:
        request_id = str(raw["id"])
        priority = int(raw["priority"])
        seats = tuple(str(seat) for seat in raw["seats"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ReservationError("invalid reservation request") from exc
    if not request_id or not seats:
        raise ReservationError("invalid reservation request")
    return {"id": request_id, "priority": priority, "seats": seats}
