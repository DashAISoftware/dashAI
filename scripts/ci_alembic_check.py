#!/usr/bin/env python3
import os
import sys

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

try:
    from DashAI.back.dependencies.database.models import Base

    metadata = Base.metadata
except Exception as e:
    print("ERROR importing project metadata:", e, file=sys.stderr)
    sys.exit(2)

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    print("DATABASE_URL is not defined", file=sys.stderr)
    sys.exit(2)

engine = create_engine(database_url)
with engine.connect() as conn:
    ctx = MigrationContext.configure(conn)
    diffs = compare_metadata(ctx, metadata)

if diffs:
    print("¡Detected schema drift! Autogenerate produced changes:")
    for d in diffs:
        print(d)
    sys.exit(1)

print("No pending schema changes detected.")
sys.exit(0)
