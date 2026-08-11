import logging
from typing import TYPE_CHECKING

from kink import inject

from DashAI.back.dependencies.database.models import InsightResult
from DashAI.back.insights.base import import_analyzer
from DashAI.back.insights.context import AnalysisContext
from DashAI.back.insights.providers import build_provider
from DashAI.back.job.base_job import BaseJob, JobError

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

log = logging.getLogger(__name__)


class InsightGenerationJob(BaseJob):
    """Generate one AI insight for an already-created ``InsightResult`` row.

    Unlike ``GenerativeJob``, this job never talks to ``BaseGenerativeTask``
    (no session, no history, no per-row ``ProcessData``): it resolves the
    analyzer and provider named on the row, builds the prompt, and asks the
    provider for a completion. It has no idea which consumer (explainer
    today, others later) created the row — that is exactly the point.
    """

    @inject
    def set_status_as_delivered(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        insight_result_id: int = self.kwargs["insight_result_id"]
        with session_factory() as db:
            result: InsightResult = db.get(InsightResult, insight_result_id)
            if not result:
                raise JobError(
                    f"InsightResult {insight_result_id} does not exist in DB."
                )
            result.set_status_as_delivered()
            db.commit()

    @inject
    def set_status_as_error(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        insight_result_id = self.kwargs.get("insight_result_id")
        if insight_result_id is None:
            return
        with session_factory() as db:
            result: InsightResult = db.get(InsightResult, insight_result_id)
            if result:
                result.set_status_as_error()
                db.commit()

    @inject
    def get_job_name(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> str:
        insight_result_id = self.kwargs.get("insight_result_id")
        if insight_result_id is None:
            return "AI Insight"
        try:
            with session_factory() as db:
                result: InsightResult = db.get(InsightResult, insight_result_id)
                if result:
                    return f"AI Insight: {result.consumer_type} #{result.consumer_id}"
        except Exception as e:
            log.exception(f"Error getting job name: {e}")
        return f"AI Insight ({insight_result_id})"

    @inject
    def run(self) -> None:
        import gc

        from kink import di

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]

        insight_result_id: int = self.kwargs["insight_result_id"]
        provider = None

        with session_factory() as db:
            result: InsightResult = db.get(InsightResult, insight_result_id)
            if not result:
                raise JobError(
                    f"InsightResult {insight_result_id} does not exist in DB."
                )

            try:
                result.set_status_as_started()
                db.commit()

                context = AnalysisContext(
                    consumer_type=result.consumer_type,
                    data=result.context_data,
                    metadata=result.context_metadata,
                )
                analyzer = import_analyzer(result.analyzer_path)()

                messages = analyzer.build_prompt(context)
                result.prompt = messages
                db.commit()

                self.report_progress(0.5, "Generating insight")
                provider = build_provider(
                    result.provider_kind, result.provider_params, component_registry
                )
                text = analyzer.analyze(context, provider)

                result.result_text = text
                result.set_status_as_finished()
                db.commit()
                self.report_progress(1.0, "Done")
            except Exception as e:
                log.exception(e)
                result.error_message = str(e)
                result.set_status_as_error()
                db.commit()
                raise JobError("AI insight generation failed") from e
            finally:
                if provider is not None:
                    provider.close()
                gc.collect()
