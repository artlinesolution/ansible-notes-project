#!/usr/bin/env python3

import argparse
import os
import sqlite3
import tempfile
import time

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


def main():
    parser = argparse.ArgumentParser(
        description="Create and retain SQLite backups"
    )

    parser.add_argument("--db", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--retention-days",
        type=int,
        default=7
    )

    args = parser.parse_args()

    if args.retention_days < 1:
        parser.error("--retention-days must be at least 1")

    db_path = Path(args.db).expanduser().resolve()
    backup_dir = Path(args.output_dir).expanduser().resolve()

    if not db_path.is_file():
        raise SystemExit(f"Database not found: {db_path}")

    backup_dir.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700
    )

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    backup_path = backup_dir / f"notes-{timestamp}.sqlite3"

    fd, temporary_path = tempfile.mkstemp(
        prefix=".notes-",
        suffix=".tmp",
        dir=str(backup_dir)
    )
    os.close(fd)

    try:
        source_uri = (
            f"file:{quote(str(db_path), safe='/')}?mode=ro"
        )

        with closing(
            sqlite3.connect(source_uri, uri=True, timeout=30)
        ) as source:
            with closing(
                sqlite3.connect(temporary_path)
            ) as destination:

                source.backup(destination)

                result = destination.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0]

                if result != "ok":
                    raise RuntimeError(
                        f"Backup integrity check failed: {result}"
                    )

        os.replace(temporary_path, backup_path)

    except Exception:
        Path(temporary_path).unlink(missing_ok=True)
        raise

    cutoff = time.time() - (args.retention_days * 86400)

    for old_backup in backup_dir.glob("notes-*.sqlite3"):
        if old_backup != backup_path:
            if old_backup.stat().st_mtime < cutoff:
                old_backup.unlink()

    print(f"Backup created successfully: {backup_path}")
    print("Integrity check: ok")


if __name__ == "__main__":
    main()
