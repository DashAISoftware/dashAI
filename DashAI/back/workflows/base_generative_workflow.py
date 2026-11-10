from typing import Any, Dict, Final, Mapping, Optional, Type

from DashAI.back.core.schema_fields import BaseSchema


class BaseGenerativeWorkflow:
    """How a generative session runs.

    Every generative session is a task (what goes in and comes out), a model
    (the engine) and a workflow (how a turn runs). A workflow declares which
    task it builds on, where the session model comes from, which schema
    validates the session parameters and which registered job runs a turn.

    Attributes
    ----------
    TASK : Optional[str]
        Name of the generative task the workflow builds on. ``None`` means
        the workflow runs any generative task and the session picks it.
    MODEL_PARAMETER : Optional[str]
        Session parameter that names the model, as a ``{component, params}``
        reference. ``None`` means the model is the session's own
        ``model_name`` and the parameters are that model's.
    SCHEMA : Optional[Type[BaseSchema]]
        Schema of the session parameters. ``None`` means the parameters are
        validated with the model's own schema.
    JOB : str
        Name of the registered job that runs a turn.
    """

    TYPE: Final[str] = "GenerativeWorkflow"
    TASK: Optional[str] = None
    MODEL_PARAMETER: Optional[str] = None
    SCHEMA: Optional[Type[BaseSchema]] = None
    JOB: str = "GenerativeJob"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Return the metadata the frontend reads.

        Returns
        -------
        Dict[str, Any]
            ``{"task": TASK}``; ``None`` for a task agnostic workflow.
        """
        return {"task": cls.TASK}

    @classmethod
    def model_name_from(cls, parameters: Optional[Mapping[str, Any]]) -> Optional[str]:
        """Return the model named by the session parameters.

        Parameters
        ----------
        parameters : Optional[Mapping[str, Any]]
            Session parameters.

        Returns
        -------
        Optional[str]
            The component name in ``parameters[MODEL_PARAMETER]``, or
            ``None`` when the workflow takes no model from its parameters or
            the reference is missing or malformed.
        """
        if cls.MODEL_PARAMETER is None or not isinstance(parameters, Mapping):
            return None
        reference = parameters.get(cls.MODEL_PARAMETER)
        if not isinstance(reference, Mapping):
            return None
        component = reference.get("component")
        if isinstance(component, str) and component:
            return component
        return None
