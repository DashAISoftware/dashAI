import logging
from typing import Any, Dict, List, Union

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import exc
from sqlalchemy.orm.session import sessionmaker

from DashAI.back.core.enums.status import ConverterListStatus
from DashAI.back.dependencies.database.models import ConverterList, Notebook

logger = logging.getLogger(__name__)
router = APIRouter()


class ConverterParams(PydanticBaseModel):
    order: int = 0
    params: Dict[str, Union[str, int, float, bool, None]] = None
    scope: Dict[str, List[int]] = None
    target: str = None

    def serialize(self) -> Dict[str, Any]:
        return {
            "order": self.order,
            "params": self.params,
            "scope": self.scope,
            "target": self.target,
        }


class ConverterListParams(PydanticBaseModel):
    notebook_id: int
    converters: Dict[str, ConverterParams]


@router.post("/", status_code=status.HTTP_201_CREATED)
@inject
async def post_notebook_converter_list(
    params: ConverterListParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Save a list of converters to apply to the notebook.

    Parameters
    ----------
    notebook_id : int
        ID of the notebook.
    converters : Dict[str, ConverterParams]
        A dictionary with the converters to apply to the notebook.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the ID of the converter list.

    Raises
    ------
    HTTPException
        If the notebook is not found or if there is an internal database error.
    """
    with session_factory() as db:
        try:
            notebook = db.get(Notebook, params.notebook_id)
            if not notebook:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Notebook not found",
                )

            converter_name = list(params.converters.keys())[0]
            converter_parameters = {
                key: value.serialize() for key, value in params.converters.items()
            }

            converter_list = ConverterList(
                notebook_id=params.notebook_id,
                converter=converter_name,
                parameters=converter_parameters,
            )

            db.add(converter_list)
            db.commit()
            db.refresh(converter_list)

            return converter_list

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{converter_list_id}")
@inject
async def get_converter_list(
    converter_list_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get a converter list from the database.

    Parameters
    ----------
    converter_list_id : int
        ID of the converter list.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    ConverterList
        The converter list.

    Raises
    ------
    HTTPException
        If the converter list is not found or if there is an internal database error.
    """
    with session_factory() as db:
        try:
            converter_list = db.get(ConverterList, converter_list_id)
            if not converter_list:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Converter list not found",
                )

            return converter_list

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/notebook/{notebook_id}")
@inject
async def get_converters_by_notebook(
    notebook_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get a list of finished converters from the database by notebook ID.

    Parameters
    ----------
    notebook_id : int
        ID of the notebook.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    List[ConverterList]
        A list of converter lists.

    Raises
    ------
    HTTPException
        If there is an internal database error.
    """
    with session_factory() as db:
        try:
            converter_lists = (
                db.query(ConverterList)
                .filter(ConverterList.notebook_id == notebook_id)
                .filter(ConverterList.status == ConverterListStatus.FINISHED)
                .all()
            )
            return converter_lists

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
