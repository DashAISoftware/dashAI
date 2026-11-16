"""Unit that applies a converter pipeline to a parsed document."""

import logging

from kink import di

from DashAI.back.job.base_job import JobError
from DashAI.back.services.documents.document_pipeline_service import (
    DocumentPipelineService,
)
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext

log = logging.getLogger(__name__)


class ApplyDocumentPipelineUnit(BaseUnit):
    """Run the configured converter pipeline and republish the document.

    The pipeline is a runtime param: it comes from the ``DataDocument`` row
    the job already loaded, not from a form. The unit replaces the context's
    ``document`` with the converted one, whose metadata records what each
    step applied or skipped.
    """

    REQUIRES = ("document",)
    PROVIDES = ("document",)
    RUNTIME_PARAMS = ("pipeline",)

    def execute(self, ctx: ExecutionContext) -> None:
        """Apply every pipeline step to the document.

        Parameters
        ----------
        ctx : ExecutionContext
            Context holding the parsed document.

        Raises
        ------
        JobError
            If the pipeline is invalid or a step cannot be applied.
        """
        document = ctx.require("document")
        service = DocumentPipelineService(di["component_registry"])
        try:
            converted = service.apply(document, self.config["pipeline"])
        except Exception as e:
            log.exception(e)
            raise JobError(f"Error applying the document pipeline: {e}") from e
        ctx.put("document", converted)
