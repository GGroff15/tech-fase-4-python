import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    logging.basicConfig(
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
    )

    logging.info("Logging is configured.")
