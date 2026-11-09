"""Serialize the writes that touch a folder with SQLite's write lock.

The app does not enable SQLite's ``PRAGMA foreign_keys``, so the
``ondelete="SET NULL"`` of ``data_document.folder_id`` never runs and the
database does not stop a document from pointing at a folder that was deleted
while it was being created or moved.

Taking SQLite's write lock before the folder is read closes that window: a
concurrent folder delete blocks until the transaction that holds the lock
commits, then reads the folder's documents again and nulls their ``folder_id``
instead of deleting the folder underneath them.
"""

from typing import TYPE_CHECKING

from sqlalchemy import update

from DashAI.back.dependencies.database.models import Folder

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def lock_folder_row(db: "Session", folder_id: int) -> None:
    """Take SQLite's write lock for the rest of the session's transaction.

    The UPDATE writes the current value back, so it changes nothing but still
    makes SQLite acquire the database-wide write lock (``RESERVED``), which any
    other writer has to wait for. It is released when the session commits or
    rolls back, so it must run before the folder is read and before the rows
    that reference it are written.

    Parameters
    ----------
    db : Session
        An open session.
    folder_id : int
        Folder the caller is about to read or write against. A missing folder
        still takes the lock, and the caller's own lookup reports the 404.
    """
    db.execute(
        update(Folder)
        .where(Folder.id == folder_id)
        .values(last_modified=Folder.last_modified)
    )
