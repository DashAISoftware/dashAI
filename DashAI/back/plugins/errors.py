"""Plugin errors, a ``code`` the front translates plus an English ``detail``."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class PluginError:
    code: str
    detail: str
    params: Dict[str, Any] = field(default_factory=dict)


class CodedError(Exception):
    """An exception the API reports as a ``PluginError``."""

    code = "internal_error"  # each subclass names its usual case

    def __init__(self, message: str = "", code: Optional[str] = None, **params):
        super().__init__(message)
        self.code = code or type(self).code
        self.params = params

    @property
    def error(self) -> PluginError:
        return PluginError(self.code, str(self), self.params)
