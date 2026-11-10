from typing import List, Optional, Union

from pydantic import BaseModel, model_validator


class GenerativeSessionParams(BaseModel):
    """Parameters to create a generative session.

    ``workflow_name`` names the workflow that runs the session. Without it the
    session runs ``InferenceWorkflow`` and must name its task and model. A
    workflow built on one task, or taking its model from the parameters,
    derives them, so they may be left out.
    """

    workflow_name: Optional[str] = None
    model_name: Optional[str] = None
    task_name: Optional[str] = None
    parameters: dict
    name: str
    description: Union[str, None] = None

    @model_validator(mode="after")
    def check_task_and_model_without_workflow(self) -> "GenerativeSessionParams":
        """Require a task and a model when no workflow is named.

        Returns
        -------
        GenerativeSessionParams
            The validated parameters.

        Raises
        ------
        ValueError
            If ``workflow_name`` is absent and the task or the model is missing.
        """
        if self.workflow_name is None and (
            self.task_name is None or self.model_name is None
        ):
            raise ValueError(
                "Provide task_name and model_name, or the workflow_name that "
                "derives them."
            )
        return self


class GenerativeSessionBulkDeleteParams(BaseModel):
    ids: List[int]
