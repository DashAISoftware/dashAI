import logging

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy.orm import Session, sessionmaker

from DashAI.back.api.api_v1.schemas import notebook_params as schemas
from DashAI.back.dependencies.database.models import Notebook

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=schemas.Notebook, status_code=status.HTTP_201_CREATED)
@inject
def create_notebook(
    params: schemas.NotebookCreate,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
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
            )


@router.get("/{notebook_id}", response_model=schemas.Notebook)
@inject
def get_notebook(
    notebook_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    db: Session
    with session_factory() as db:
        notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
        if not notebook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notebook not found",
            )
        return notebook
