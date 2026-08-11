from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AnalysisContext:
    """Consumer-agnostic input for an AI-generated insight.

    ``data`` carries the already-computed facts a consumer wants analyzed
    (e.g. a partial dependence curve's trend and values), never pre-written
    narrative text — the analyzer decides how to phrase it, not the caller.
    """

    consumer_type: str
    data: dict
    metadata: Optional[dict] = None
