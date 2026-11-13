"""How a failed chat turn is stored, shared by the plain and the RAG chat jobs.

The chat keeps a failed turn on screen with its error (#969), so the turn
stores a short, readable detail as its output.
"""

from DashAI.back.dependencies.database.models import GenerativeProcess, ProcessData

#: The longest error detail a failed turn stores. The chat shows it in the
#: turn's error bubble; the full error and its traceback stay in the log.
ERROR_DETAIL_MAX_LENGTH = 500


def fail_process(
    db, process: "GenerativeProcess | None", message: str, cause=None
) -> None:
    """Mark a turn as failed and store why, as its output.

    The chat shows the stored detail in the failed turn's error bubble, so it
    is the error's message, cut to ``ERROR_DETAIL_MAX_LENGTH``, never a
    traceback (that stays in the log).

    Parameters
    ----------
    db : Session
        The open database session.
    process : GenerativeProcess or None
        The failed turn; nothing is stored when it could not be loaded.
    message : str
        What failed, for the user.
    cause : BaseException, optional
        The error behind it, whose message is added to the detail.
    """
    if process is None:
        return
    # A failed database call leaves the session unusable until rolled back,
    # and nothing pending at a failure point is worth keeping.
    db.rollback()
    detail = f"{message} {cause}" if cause is not None else message
    if len(detail) > ERROR_DETAIL_MAX_LENGTH:
        detail = detail[: ERROR_DETAIL_MAX_LENGTH - 3] + "..."
    process.set_status_as_error()
    process.set_progress(None)
    db.add(
        ProcessData(
            data=detail,
            data_type="str",
            process_id=process.id,
            is_input=False,
        )
    )
    db.commit()
