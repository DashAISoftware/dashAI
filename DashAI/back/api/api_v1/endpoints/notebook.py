import logging

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy.orm import Session, sessionmaker

from DashAI.back.api.api_v1.schemas import notebook_params as schemas
from DashAI.back.dependencies.database.models import ConverterList, Explorer, Notebook

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=schemas.Notebook, status_code=status.HTTP_201_CREATED)
@inject
def create_notebook(
    params: schemas.NotebookCreate,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Create a new notebook entry in the database.

    Parameters
    ----------
    params : schemas.NotebookCreate
        The parameters for creating a notebook.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    schemas.Notebook
        The newly created notebook object.

    Raises
    ------
    HTTPException
        If there is an error creating the notebook, returns a 500 Internal Server Error.
    """
    db: Session
    with session_factory() as db:
        try:
            notebook_model = Notebook(**params.model_dump())
            db.add(notebook_model)
            db.commit()
            db.refresh(notebook_model)

            return notebook_model
        except Exception as e:
            log.error(f"Error creating notebook: {e}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create notebook",
            ) from e


@router.get("/{notebook_id}", response_model=schemas.Notebook)
@inject
def get_notebook(
    notebook_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get a notebook by its ID.

    Parameters
    ----------
    notebook_id : int
        ID of the notebook to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    schemas.Notebook
        The notebook object with the specified ID.

    Raises
    ------
    HTTPException
        If the notebook is not found, returns a 404 Not Found error.
    """
    db: Session
    with session_factory() as db:
        notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
        if not notebook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notebook not found",
            ) from None
        return notebook


@router.get("/{notebook_id}/explorer")
@inject
def get_notebook_explorer(
    notebook_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all explorers associated with a notebook.

    Parameters
    ----------
    notebook_id : int
        ID of the notebook.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    explorers : List[explorer_schemas.Explorer]
        List of explorers associated with the notebook.

    Raises
    ------
    HTTPException
        If there is an error retrieving explorers, returns a 500 Internal Server Error.
    """
    db: Session
    with session_factory() as db:
        try:
            explorers = (
                db.query(Explorer).filter(Explorer.notebook_id == notebook_id).all()
            )
            return explorers
        except Exception as e:
            log.error(f"Error retrieving explorers for notebook {notebook_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve explorers",
            ) from e


@router.get("/{notebook_id}/converter")
@inject
async def get_notebook_converter_list(
    notebook_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all converters associated with a notebook.

    Parameters
    ----------
    notebook_id : int
        ID of the notebook.
    session_factory : Callable[..., ContextManager[Session]]
        Dependency-injected SQLAlchemy session factory.

    Returns
    -------
    ConverterList
        The converter list associated with the notebook.

    Raises
    ------
        HTTPException: If there is an error retrieving the converter list,
        returns a 500 Internal Server Error.
    """
    with session_factory() as db:
        try:
            converter_list = (
                db.query(ConverterList)
                .filter(ConverterList.notebook_id == notebook_id)
                .all()
            )

            return converter_list
        except Exception as e:
            log.error(
                f"Error retrieving converter list for notebook {notebook_id}: {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve converter from notebook {notebook_id}",
            ) from e
