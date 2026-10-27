"""Function-calling runner for LLM-backed retrieval collaborators.

The retrieval evaluator and the filter evaluator share exactly the same model
protocol: require a function-calling-capable model, validate the function spec,
invoke ``generate_function_call``, and retry unusable parses up to a configured
bound. Keeping that protocol here leaves each evaluator in charge of only its
prompt and its typed parser.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Generic, List, TypeVar

from DashAI.back.models.RAG.exceptions.retriever import (
    RAGRetrieverEvaluationError,
)
from DashAI.back.models.text_to_text_generation_model import FunctionCallResult

T = TypeVar("T")

#: Maximum characters of an error reason echoed in a retry warning.
_MAX_RETRY_LOG_CHARS = 300


def _summarize_error(error: BaseException) -> str:
    """Return a short single-line summary of an evaluation error.

    Parameters
    ----------
    error : BaseException
        The error about to be retried.

    Returns
    -------
    str
        The first line of the error message, truncated for logs.
    """
    text = str(error).strip()
    if not text:
        return type(error).__name__
    first_line = text.splitlines()[0]
    if len(first_line) <= _MAX_RETRY_LOG_CHARS:
        return first_line
    return first_line[:_MAX_RETRY_LOG_CHARS] + "..."


class LLMRouteRunner(Generic[T]):
    """Owns the function-call contract and bounded retries.

    Parameters
    ----------
    llm_model : Any
        The text-to-text model used for the evaluation. It must support function
        calling.
    expected_function : str
        The function name a function-calling model must call.
    function_description : str
        Human-readable description of that function.
    function_parameters : Dict[str, Any]
        JSON schema of the function's arguments.
    function_call_max_trials : int
        Maximum number of attempts, the first one included.
    logger : logging.Logger
        Logger used for retry warnings. Callers inject their own module logger
        so records keep their original namespace.
    """

    def __init__(
        self,
        llm_model: Any,
        expected_function: str,
        function_description: str,
        function_parameters: Dict[str, Any],
        function_call_max_trials: int,
        logger: logging.Logger,
    ) -> None:
        self._llm_model = llm_model
        self._expected_function = expected_function
        self._function_description = function_description
        self._function_parameters = function_parameters
        self._function_call_max_trials = function_call_max_trials
        self._logger = logger

    def run(
        self,
        prompt_text: str,
        *,
        parse_call: Callable[[Any], T],
        function_route_label: str,
    ) -> T:
        """Evaluate through the function-calling interface.

        Parameters
        ----------
        prompt_text : str
            The rendered prompt sent as the user message.
        parse_call : Callable[[Any], T]
            Parses the function-call arguments into the typed result.
        function_route_label : str
            Human-readable route name used in retry warnings.

        Returns
        -------
        T
            The typed parse result of the first successful attempt.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the model does not support function calling, the attempts are
            exhausted, or the model claims support without implementing it.
        """
        if not self._llm_model.supports_function_calling():
            raise RAGRetrieverEvaluationError(
                f"{type(self._llm_model).__name__} does not support function "
                "calling; the LLM-backed retrievers require a model with "
                "function calling support."
            )
        return self._run_function_route(prompt_text, parse_call, function_route_label)

    def _run_function_route(
        self,
        prompt_text: str,
        parse_call: Callable[[Any], T],
        route_label: str,
    ) -> T:
        """Run the function-calling route with bounded retries.

        Parameters
        ----------
        prompt_text : str
            The rendered prompt sent as the user message.
        parse_call : Callable[[Any], T]
            Parses the function-call arguments into the typed result.
        route_label : str
            Human-readable route name used in retry warnings.

        Returns
        -------
        T
            The typed parse result.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the attempts are exhausted, or the model reports support without
            implementing ``generate_function_call`` (never retried).
        """
        spec = self._function_call_spec()

        def attempt(feedback: str | None) -> T:
            """Perform one function-calling attempt with optional feedback."""
            attempt_prompt = prompt_text
            if feedback:
                attempt_prompt = (
                    f"{prompt_text}\n\nYour previous decision was rejected: "
                    f"{feedback}. Correct it and call the function again."
                )
            messages = [{"role": "user", "content": attempt_prompt}]
            return self._attempt_function_call(messages, spec, parse_call)

        try:
            return self._retry(attempt, route_label)
        except NotImplementedError as err:
            # A model that claims function-calling support without implementing
            # it is a configuration error, not a transient malformed response:
            # never retry it.
            raise RAGRetrieverEvaluationError(
                f"{type(self._llm_model).__name__} reports function calling "
                "support but does not implement generate_function_call."
            ) from err

    def _attempt_function_call(
        self,
        messages: List[Dict[str, str]],
        spec: Dict[str, Any],
        parse_call: Callable[[Any], T],
    ) -> T:
        """Perform one function-call attempt and return the typed parse result.

        Parameters
        ----------
        messages : List[Dict[str, str]]
            The chat messages for this attempt, including any retry feedback.
        spec : Dict[str, Any]
            The function specification.
        parse_call : Callable[[Any], T]
            Parses the call arguments into the typed result.

        Returns
        -------
        T
            The typed parse result.

        Raises
        ------
        NotImplementedError
            If the model reports support but implements no function-calling
            method. Never retried; the caller converts it to a
            ``RAGRetrieverEvaluationError``.
        RAGRetrieverEvaluationError
            If the backend reports a malformed call or the call violates the
            contract.
        """
        try:
            result = self._llm_model.generate_function_call(
                messages=messages,
                functions=[spec],
            )
        except NotImplementedError:
            # NotImplementedError subclasses RuntimeError; re-raise it so the
            # caller can classify it as a non-retryable configuration error.
            raise
        except (ValueError, RuntimeError) as err:
            raise RAGRetrieverEvaluationError(
                f"Function calling failed: {err}"
            ) from err
        self._require_function_call(result)
        return parse_call(result.arguments)

    def _require_function_call(self, result: Any) -> None:
        """Validate the function-call response shape and name.

        Parameters
        ----------
        result : Any
            Raw return value of ``generate_function_call``.

        Returns
        -------
        None
            Nothing; the validated result is used by the caller.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the result is not a :class:`FunctionCallResult`, has no name, or
            names a different function.
        """
        if not isinstance(result, FunctionCallResult):
            raise RAGRetrieverEvaluationError(
                "The function-calling model returned an unexpected output shape: "
                f"{type(result).__name__}."
            )
        if not result.name:
            raise RAGRetrieverEvaluationError(
                "The function-calling model did not report a function name."
            )
        if result.name != self._expected_function:
            raise RAGRetrieverEvaluationError(
                f"The model called '{result.name}' instead of the expected "
                f"'{self._expected_function}'."
            )

    def _retry(
        self,
        attempt_fn: Callable[[str | None], T],
        route_label: str,
    ) -> T:
        """Run the function-calling route, retrying with bounded feedback.

        Parameters
        ----------
        attempt_fn : Callable[[str | None], T]
            Performs one full attempt. It receives ``None`` on the first call and
            the previous error summary on every retry.
        route_label : str
            Human-readable route name used in retry warnings.

        Returns
        -------
        T
            The first successful result.

        Raises
        ------
        RAGRetrieverEvaluationError
            The last evaluation error, once all attempts are exhausted. Other
            exceptions propagate unchanged.
        """
        last_error: RAGRetrieverEvaluationError | None = None
        feedback: str | None = None
        for attempt in range(1, self._function_call_max_trials + 1):
            try:
                return attempt_fn(feedback)
            except RAGRetrieverEvaluationError as err:
                last_error = err
                feedback = _summarize_error(err)
                if attempt >= self._function_call_max_trials:
                    break
                self._logger.warning(
                    "%s attempt %d of %d failed for %s; retrying: %s",
                    route_label,
                    attempt,
                    self._function_call_max_trials,
                    type(self._llm_model).__name__,
                    feedback,
                )
        if last_error is not None:
            raise last_error
        raise RAGRetrieverEvaluationError(
            "The evaluation did not produce a result and recorded no error."
        )

    def _function_call_spec(self) -> Dict[str, Any]:
        """Return the function spec exposed to the function-calling backend.

        Returns
        -------
        Dict[str, Any]
            The ``name``/``description``/``parameters`` specification.

        Raises
        ------
        RAGRetrieverEvaluationError
            If the caller declares no function spec.
        """
        if (
            not self._expected_function
            or not self._function_description
            or not self._function_parameters
        ):
            raise RAGRetrieverEvaluationError(
                "The evaluator does not declare a function spec to use function "
                "calling; declare the expected function, its description and "
                "parameters."
            )
        return {
            "name": self._expected_function,
            "description": self._function_description,
            "parameters": self._function_parameters,
        }
