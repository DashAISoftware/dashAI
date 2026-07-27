from typing import Optional

from pydantic import BaseModel, Field


class UploadNotebook(BaseModel):
    name: Optional[str] = Field(None, description="Nombre del notebook.")
    description: Optional[str] = Field(None, description="Descripción del notebook.")
    dataset_id: int = Field(..., description="ID del dataset asociado al notebook.")


class DeleteNotebook(BaseModel):
    notebook_id: int = Field(..., description="ID del notebook a eliminar")


class GetNotebookExplorerListByNotebookId(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook para obtener la lista de explorers"
    )


class GetDatasetRowsByNotebookIdParams(BaseModel):
    notebook_id: int = Field(
        ...,
        description="ID del notebook del cual se quiere obtener las filas del dataset.",
    )
    start_row: int = Field(
        0, ge=0, description="Fila inicial para obtener las filas del dataset."
    )
    end_row: int = Field(
        5, description="Fila final para obtener las filas del dataset."
    )
