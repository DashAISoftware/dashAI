from typing import Final, List


class BaseGenerativeWorkflow:
    """How a generative session runs.

    Every generative session is a task (what goes in and comes out), a model
    (the engine) and a workflow (how a turn runs). Like a task, a workflow is
    defined by what it works with rather than by a configuration: its
    ``COMPATIBLE_COMPONENTS`` name the generative tasks it runs and the
    components it is built from, and the registry relates them both ways.
    A workflow has no schema; the parameters a user configures belong to the
    components it relates to.

    Attributes
    ----------
    COMPATIBLE_COMPONENTS : List[str]
        Names of the tasks the workflow runs and of the components it uses.
    """

    TYPE: Final[str] = "GenerativeWorkflow"
    COMPATIBLE_COMPONENTS: List[str] = []
