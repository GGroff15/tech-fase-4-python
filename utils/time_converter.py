from datetime import datetime, timezone


def epoch_to_iso_utc(epoch_seconds: float) -> str:
    return (
        datetime
        .fromtimestamp(epoch_seconds, tz=timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )
