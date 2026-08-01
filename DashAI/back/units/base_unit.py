"""Base class for the atomic units a job is composed of."""

import logging
from abc import ABCMeta, abstractmethod
from typing import Final, Tuple, final

from DashAI.back.config_object import ConfigObject
from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.units.context import ExecutionContext

logger = logging.getLogger(__name__)


class BaseUnit(ConfigObject, metaclass=ABCMeta):
    """Abstract class for all atomic units.

    A unit is the smallest reusable piece of a job: it declares the context
    keys it needs, the keys it produces, and does one thing. Jobs compose units
    into a sequence; the orchestration around them (database transactions,
    status transitions, progress reporting) stays in the job.

    Units never read nor mutate the ``Run`` row. ``run_id`` travels through the
    context as an opaque correlation id because ``ModelFactory`` needs it for
    ``BaseModel.calculate_metrics`` to work, but the ownership of the row
    belongs to the job.

    ``BaseUnit`` deliberately does not inherit from ``BaseJob``: the registry
    derives a component's type by walking the MRO for ancestors whose name
    contains "Base" and that declare a ``TYPE``, and it rejects components with
    more than one candidate. Inheriting from both would make registration fail.
    """

    TYPE: Final[str] = "Unit"

    #: Context keys that must be present before the unit runs.
    REQUIRES: Tuple[str, ...] = ()
    #: Context keys the unit guarantees after it runs.
    PROVIDES: Tuple[str, ...] = ()

    SCHEMA: BaseSchema = BaseSchema

    def __init__(self, **config) -> None:
        """Store the unit configuration.

        Parameters
        ----------
        config : dict
            Configuration of the unit, as declared by its schema.
        """
        self.config = config

    def validate(self, ctx: ExecutionContext) -> None:
        """Check preconditions without executing the unit.

        Runs before the job commits to any observable state change, so a unit
        can reject an impossible configuration early. No-op by default.

        Parameters
        ----------
        ctx : ExecutionContext
            The shared execution context.
        """

    @abstractmethod
    def execute(self, ctx: ExecutionContext) -> None:
        """Do the unit's work, reading from and writing to the context.

        Parameters
        ----------
        ctx : ExecutionContext
            The shared execution context.
        """
        raise NotImplementedError

    @final
    def __call__(self, ctx: ExecutionContext) -> None:
        """Run the unit, enforcing its declared contract.

        Calls ``validate`` before ``execute`` so a caller that just does
        ``unit(ctx)`` — the sanctioned way to run a unit — always gets its
        precondition checks (e.g. a download gate) for free. An orchestrator
        that needs ``validate`` to run earlier, ahead of some other state
        change, is still free to call ``unit.validate(ctx)`` directly first;
        ``validate`` runs again here, which is redundant but harmless.

        Parameters
        ----------
        ctx : ExecutionContext
            The shared execution context.

        Raises
        ------
        UnitContractError
            If a required key is missing before execution or a promised key is
            missing after it.
        """
        for key in self.REQUIRES:
            ctx.require(key)

        self.validate(ctx)

        logger.debug("Running unit %s", type(self).__name__)
        self.execute(ctx)

        for key in self.PROVIDES:
            ctx.require(key)
