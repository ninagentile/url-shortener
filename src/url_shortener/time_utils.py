from datetime import UTC, datetime


def utc_now() -> datetime:
    """
    Returns the current UTC time as a naive datetime, the same format
    MongoDB returns for stored dates

    Returns
    -------
    now
        Current UTC time, without tzinfo
    """
    return datetime.now(UTC).replace(tzinfo=None)
