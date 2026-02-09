import logging
import sys


def configure_logging(level: str = None) -> None:
    if level is None:
        from config import constants
        level = constants.LOG_LEVEL
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    logging.basicConfig(
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
    )

    logging.info("Logging is configured.")
