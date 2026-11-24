"""Persistence signature of a retriever configuration.

A retriever's configuration mixes two kinds of parameters. Some shape what is
stored on disk and in the database (the embedding model, the vectorizer, the
BM25 weights); others only act at query time (``top_k``, the distance metric,
the retrieve-then-expand options, a composite's merge strategy). Only the first
kind may take part in the identity under which a fitted retriever is looked up,
stored and cleaned up, or tuning a query-time knob would force a re-index.

Each retriever class declares its query-time parameters in
``NON_PERSISTENT_PARAMS``. The signature of a configuration is the
configuration without those parameters, resolved recursively: a parameter
holding a ``{component, params}`` reference is replaced by the signature of
that component, using the nested component class's own declaration, and a
``children`` list is resolved the same way. A class without a declaration
(converters, similarity functions, language models) keeps all of its
parameters, because nothing is known to be query-time only.

Mappings are returned with their keys sorted at every level, while lists keep
their order. The signature is compared as JSON text by the database natural-key
lookups, so two configurations that differ only in key order must serialise
identically.
"""

from typing import Any, Dict, Final, List, Tuple

from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.exceptions import RAGComponentNotFoundError
from DashAI.back.models.RAG.retrievers.ref_utils import (
    COMPONENT_KEY,
    PARAMS_KEY,
    is_component_ref,
)

#: Name of the class attribute listing a class's query-time parameters.
NON_PERSISTENT_ATTRIBUTE: Final[str] = "NON_PERSISTENT_PARAMS"


def _non_persistent_params(model_class: type) -> Tuple[str, ...]:
    """Return the query-time parameter names declared by *model_class*.

    A class without a ``NON_PERSISTENT_PARAMS`` declaration contributes no
    exclusions, so all of its parameters count toward the identity.

    Parameters
    ----------
    model_class : type
        Component class to inspect.

    Returns
    -------
    Tuple[str, ...]
        The declared names, or an empty tuple when the class declares none.
    """
    if hasattr(model_class, NON_PERSISTENT_ATTRIBUTE):
        return tuple(getattr(model_class, NON_PERSISTENT_ATTRIBUTE))
    return ()


def _resolve_class(component: str, registry: ComponentRegistry) -> type:
    """Return the class registered under *component*.

    Parameters
    ----------
    component : str
        Registered name of the component, as stored in a reference.
    registry : ComponentRegistry
        Registry the name is looked up in.

    Returns
    -------
    type
        The component class registered under *component*.

    Raises
    ------
    RAGComponentNotFoundError
        If *component* is not registered.
    """
    if component not in registry:
        raise RAGComponentNotFoundError(
            f"Component '{component}' not found in registry"
        )
    return registry[component]["class"]


def _mapping_signature(
    mapping: Dict[str, Any], ignored: Tuple[str, ...], registry: ComponentRegistry
) -> Dict[str, Any]:
    """Return *mapping* without the *ignored* keys, sorted, with values resolved.

    Parameters
    ----------
    mapping : Dict[str, Any]
        Parameters to reduce.
    ignored : Tuple[str, ...]
        Keys to drop at this level only.
    registry : ComponentRegistry
        Registry used to resolve nested components.

    Returns
    -------
    Dict[str, Any]
        A new mapping whose keys are sorted and whose values are signatures.
    """
    signature: Dict[str, Any] = {}
    for key in sorted(mapping):
        if key in ignored:
            continue
        signature[key] = _value_signature(mapping[key], registry)
    return signature


def _reference_signature_value(
    reference: Dict[str, Any], registry: ComponentRegistry
) -> Dict[str, Any]:
    """Return the signature of a ``{component, params}`` reference.

    Raises
    ------
    ValueError
        If the reference's ``params`` is not a dict. The message names the
        component.
    RAGComponentNotFoundError
        If the component is not registered.
    """
    component = reference[COMPONENT_KEY]
    params = reference[PARAMS_KEY]
    if not isinstance(params, dict):
        raise ValueError(
            f"The parameters of component '{component}' must be a dict, "
            f"got {type(params).__name__}."
        )
    nested_class = _resolve_class(component, registry)
    signature: Dict[str, Any] = {}
    for key in sorted(reference):
        if key == PARAMS_KEY:
            signature[key] = persistence_signature(nested_class, params, registry)
        else:
            signature[key] = _value_signature(reference[key], registry)
    return signature


def _value_signature(value: Any, registry: ComponentRegistry) -> Any:
    """Return the signature of a parameter value.

    References are resolved through the registry, plain mappings are searched
    for references and canonically ordered, lists keep their order, and every
    other value is returned unchanged.

    Parameters
    ----------
    value : Any
        A parameter value, possibly a reference, mapping, list or scalar.
    registry : ComponentRegistry
        Registry used to resolve nested components.

    Returns
    -------
    Any
        The signature of *value*, in the same shape it was given.

    Raises
    ------
    ValueError
        If a nested reference's ``params`` is not a dict.
    RAGComponentNotFoundError
        If a nested component is not registered.
    """
    if is_component_ref(value):
        return _reference_signature_value(value, registry)
    if isinstance(value, dict):
        return _mapping_signature(value, (), registry)
    if isinstance(value, list):
        items: List[Any] = []
        for item in value:
            items.append(_value_signature(item, registry))
        return items
    return value


def reference_signature(
    reference: Dict[str, Any], registry: ComponentRegistry
) -> Dict[str, Any]:
    """Return the persistence signature of a ``{component, params}`` reference.

    Parameters
    ----------
    reference : Dict[str, Any]
        Component reference, as stored in a session's parameters.
    registry : ComponentRegistry
        Registry used to resolve the component and its nested components.

    Returns
    -------
    Dict[str, Any]
        The reference with ``params`` replaced by its persistence signature.

    Raises
    ------
    ValueError
        If *reference* is not a ``{component, params}`` reference, or its
        ``params`` is not a dict.
    RAGComponentNotFoundError
        If a component is not registered.
    """
    if not is_component_ref(reference):
        raise ValueError(
            f"Expected a {{component, params}} reference, got {reference!r}."
        )
    return _reference_signature_value(reference, registry)


def persistence_signature(
    model_class: type, params: Dict[str, Any], registry: ComponentRegistry
) -> Dict[str, Any]:
    """Return the parameters of a configuration that shape what is persisted.

    Parameters
    ----------
    model_class : type
        Class the configuration belongs to. Its ``NON_PERSISTENT_PARAMS`` are
        dropped from *params*.
    params : Dict[str, Any]
        Configuration parameters, possibly holding nested component references.
    registry : ComponentRegistry
        Registry used to resolve the classes of nested components.

    Returns
    -------
    Dict[str, Any]
        A new mapping without the query-time parameters, at every level, with
        keys sorted at every level. The input is never mutated.

    Raises
    ------
    ValueError
        If a nested reference's ``params`` is not a dict.
    RAGComponentNotFoundError
        If a nested component is not registered.
    """
    return _mapping_signature(params, _non_persistent_params(model_class), registry)
