# ruff: noqa
from pydantic import BaseModel, Field


class MainResponseQualityCriteria(BaseModel):
    request_fulfillment_text: int = Field(
        description="Colocar 1 si la respuesta textual del agente cumple con la solicitud del usuario.  Si hubo al menos un aspecto solicitado "
        "que no se cumplió en la respuesta del agente, debes colocar 0"
    )
    response_structure: int = Field(
        description="Colocar 1 si la respuesta del agente cumple con la siguiente estructura: Resumen, acciones ejecutadas, explicación técnica, "
        "próximos pasos.  Colocar 0 si al menos una parte de la estructura no se cumple"
    )
    clarity_response: float = Field(
        description="Colocar un valor entre 0 y 1 que indique el nivel de claridad de la respuesta del agente.  0 es muy confusa, 1 es muy clara"
    )
    enthusiasm_response: float = Field(
        description="Colocar un valor entre 0 y 1 que indique el nivel de entusiasmo de la respuesta del agente.  "
        "0 es muy poco entusiasta, 1 es muy entusiasta.  Entiendase por entusiasta como ser que siente pasión, interés y motivación profunda por una causa, actividad o idea"
    )
    logical_coherence: float = Field(
        description="Colocar un valor entre 0 y 1 que indique el nivel de coherencia lógica de la respuesta del agente.  0 es muy incoherente, "
        "1 es muy coherente"
    )
