#!/usr/bin/env python3
"""Guard the Alembic history against edits that break existing databases.

Alembic stores only the current revision of a database. On upgrade it walks
the ``down_revision`` links from that revision and treats every ancestor as
already applied. Two edits to the history therefore corrupt databases that
users already have, without raising any error:

* giving a published migration a new parent, which makes the revisions
  inserted below it look applied, so they never run. This is how the
  ``credential`` table went missing on databases created on v0.9.7 (see
  revision 72db19a8ec8d);
* renaming or deleting a published revision, which leaves those databases
  pointing at a revision Alembic can no longer locate.

Subcommands:

check-parents REF [REF ...]
    Fail if any migration present in the git ref REF is missing from the
    working tree or has a different ``down_revision`` there.

upgrade-from REF [REF ...]
    Build a database with the migrations of each git ref REF, upgrade it with
    the working-tree migrations and compare its schema with a database created
    from scratch. Fail on any missing or different table, column, unique
    constraint, index or foreign key.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_SUBDIR = Path("DashAI") / "alembic"
CURRENT_SCRIPT_DIR = REPO_ROOT / ALEMBIC_SUBDIR


def safe_name(ref: str) -> str:
    return re.sub(r"[^\w.-]", "_", ref)


def export_alembic_dir(ref: str, workdir: Path) -> Path | None:
    """Extract DashAI/alembic as it is in ``ref``; None if the ref lacks it."""
    dest = workdir / safe_name(ref)
    tar_path = workdir / f"{safe_name(ref)}.tar"
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        [
            "git",
            "archive",
            "--format=tar",
            "-o",
            str(tar_path),
            ref,
            str(ALEMBIC_SUBDIR),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if archive.returncode != 0:
        return None
    subprocess.run(["tar", "-xf", str(tar_path), "-C", str(dest)], check=True)
    return dest / ALEMBIC_SUBDIR


def alembic_config(script_dir: Path, db_path: Path) -> Config:
    url = f"sqlite:///{db_path}"
    # ``-x url`` is the first thing env.py looks at, above DATABASE_URL, so
    # the database CI prepares for the other steps is never touched.
    cfg = Config(cmd_opts=argparse.Namespace(x=[f"url={url}"]))
    cfg.set_main_option("script_location", str(script_dir))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.set_main_option("prepend_sys_path", str(REPO_ROOT))
    return cfg


def script_directory(script_dir: Path) -> ScriptDirectory:
    cfg = Config()
    cfg.set_main_option("script_location", str(script_dir))
    return ScriptDirectory.from_config(cfg)


def parents(revision) -> tuple[str, ...]:
    down = revision.down_revision
    if down is None:
        return ()
    if isinstance(down, str):
        return (down,)
    return tuple(sorted(down))


def read_schema(db_path: Path) -> dict:
    con = sqlite3.connect(db_path)
    schema = {}
    tables = con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
        " AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'"
    ).fetchall()
    for (table,) in tables:
        columns = {
            col[1]: (col[2], col[3], col[4], col[5])
            for col in con.execute(f"PRAGMA table_info('{table}')")
        }
        unique = set()
        indexes = set()
        for index in con.execute(f"PRAGMA index_list('{table}')"):
            _, name, is_unique, origin, _ = index
            if is_unique:
                unique.add(
                    tuple(row[2] for row in con.execute(f"PRAGMA index_info('{name}')"))
                )
            if origin == "c":
                indexes.add(name)
        foreign_keys = {
            (fk[2], fk[3], fk[4])
            for fk in con.execute(f"PRAGMA foreign_key_list('{table}')")
        }
        schema[table] = {
            "columns": columns,
            "unique": unique,
            "indexes": indexes,
            "foreign keys": foreign_keys,
        }
    con.close()
    return schema


def diff_schema(fresh: dict, upgraded: dict) -> list[str]:
    problems = []
    for table, expected in fresh.items():
        if table not in upgraded:
            problems.append(f"missing table {table}")
            continue
        actual = upgraded[table]
        for column, spec in expected["columns"].items():
            if column not in actual["columns"]:
                problems.append(f"missing column {table}.{column}")
            elif actual["columns"][column] != spec:
                problems.append(
                    f"column {table}.{column} is {actual['columns'][column]},"
                    f" expected {spec}"
                )
        for kind in ("unique", "indexes", "foreign keys"):
            for item in sorted(expected[kind] - actual[kind]):
                problems.append(f"missing {kind} on {table}: {item}")
            for item in sorted(actual[kind] - expected[kind]):
                problems.append(f"unexpected {kind} on {table}: {item}")
    for table in upgraded:
        if table not in fresh:
            problems.append(f"unexpected table {table}")
    return problems


def check_parents(refs: list[str], workdir: Path) -> list[str]:
    current = {
        rev.revision: rev
        for rev in script_directory(CURRENT_SCRIPT_DIR).walk_revisions()
    }
    problems = []
    for ref in refs:
        script_dir = export_alembic_dir(ref, workdir)
        if script_dir is None:
            print(f"{ref}: has no {ALEMBIC_SUBDIR}, skipped")
            continue
        published = list(script_directory(script_dir).walk_revisions())
        for rev in published:
            now = current.get(rev.revision)
            if now is None:
                problems.append(
                    f"{ref}: revision {rev.revision} ({rev.doc}) no longer exists"
                )
            elif parents(now) != parents(rev):
                problems.append(
                    f"{ref}: revision {rev.revision} ({rev.doc}) revised"
                    f" {parents(rev)} and now revises {parents(now)}"
                )
        print(f"{ref}: {len(published)} published revisions compared")
    return problems


def upgrade_from(refs: list[str], workdir: Path) -> list[str]:
    current = script_directory(CURRENT_SCRIPT_DIR)
    fresh_db = workdir / "fresh.sqlite3"
    command.upgrade(alembic_config(CURRENT_SCRIPT_DIR, fresh_db), "head")
    fresh = read_schema(fresh_db)

    problems = []
    for ref in refs:
        script_dir = export_alembic_dir(ref, workdir)
        if script_dir is None:
            print(f"{ref}: has no {ALEMBIC_SUBDIR}, skipped")
            continue

        old_db = workdir / f"{safe_name(ref)}.sqlite3"
        try:
            command.upgrade(alembic_config(script_dir, old_db), "head")
        except Exception as exc:
            problems.append(
                f"{ref}: its own migrations fail on an empty database: {exc}"
            )
            continue

        old = script_directory(script_dir)
        old_ids = {rev.revision for rev in old.walk_revisions()}
        skipped: set[str] = set()
        try:
            for head in old.get_heads():
                ancestors = current.iterate_revisions(head, "base")
                skipped |= {rev.revision for rev in ancestors} - old_ids
        except Exception:  # reported by the upgrade below
            pass

        upgraded_db = workdir / f"{safe_name(ref)}-upgraded.sqlite3"
        shutil.copy(old_db, upgraded_db)
        try:
            command.upgrade(alembic_config(CURRENT_SCRIPT_DIR, upgraded_db), "head")
        except Exception as exc:
            problems.append(f"{ref}: upgrade to head fails: {exc}")
            continue

        diffs = diff_schema(fresh, read_schema(upgraded_db))
        print(f"{ref}: {'schema differs' if diffs else 'OK'}")
        for rev_id in sorted(skipped):
            doc = current.get_revision(rev_id).doc
            print(f"    note: {rev_id} ({doc}) counts as applied and does not run")
        for diff in diffs:
            print(f"    {diff}")
            problems.append(f"{ref}: {diff}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    subparsers = parser.add_subparsers(dest="check", required=True)
    for name in ("check-parents", "upgrade-from"):
        sub = subparsers.add_parser(name)
        sub.add_argument("refs", nargs="+", metavar="REF")
    args = parser.parse_args()

    # The working-tree migrations are driven through ``-x url``; make sure no
    # inherited DATABASE_URL can redirect an older env.py either.
    os.environ.pop("DATABASE_URL", None)

    with tempfile.TemporaryDirectory(prefix="dashai-alembic-") as tmp:
        workdir = Path(tmp)
        if args.check == "check-parents":
            problems = check_parents(args.refs, workdir)
        else:
            problems = upgrade_from(args.refs, workdir)

    sys.stdout.flush()
    if problems:
        print(f"\n{len(problems)} problem(s):", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print("\nAll good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
