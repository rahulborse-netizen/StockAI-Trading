"""
Configure logging to write errors and warnings to logs/errors.log.
Stored at project root for easy access when fixing issues.
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_log_file():
    """Configure logging to write WARNING and ERROR to logs/errors.log."""
    project_root = Path(__file__).resolve().parent.parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "errors.log"

    # Format: timestamp | level | module | message
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler: WARNING and above (warnings + errors)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(formatter)

    # Add to root logger so all modules inherit it
    root = logging.getLogger()
    if not any(h for h in root.handlers if getattr(h, "baseFilename", "").endswith("errors.log")):
        root.addHandler(file_handler)

    return str(log_file)
