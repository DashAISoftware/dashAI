"""Helpers to read the ``splits`` payload stored in a model session.

The payload is written by the frontend as a flat object: the selected
splitter's schema parameters at the top level, plus the meta keys
``splitter_name``, ``splitType`` and ``splitted_indexes``. Sessions created
before the splitter forms were generated from the component schemas used a
different set of keys, so every reader normalizes the payload first.
"""

from typing import Any, Dict, List, Tuple, Type

# Before fold splitters existed the payload named no splitter at all: every
# split was a holdout split.
DEFAULT_SPLITTER_NAME = "HoldoutSplitter"

INDEX_KEY_BY_SPLIT = {
    "train": "train_indexes",
    "test": "test_indexes",
    "validation": "val_indexes",
}

META_KEYS = ("splitter_name", "splitType", "splitted_indexes", "seed")


def normalize_splits_payload(splits_data: Dict[str, Any]) -> Dict[str, Any]:
    """Translate a legacy splits payload into the current contract.

    Three legacy shapes are handled:

    - No ``splitter_name``, from before fold splitters existed.
    - ``seed`` instead of the schema's ``random_state``.
    - ``train`` / ``test`` / ``validation`` holding index lists instead of
      proportions, which is how manual and predefined holdout splits used to
      be stored.

    Parameters
    ----------
    splits_data : dict
        The payload as stored in ``ModelSession.splits``.

    Returns
    -------
    dict
        A new dictionary following the current contract. The input is left
        untouched.
    """
    normalized = dict(splits_data)

    if not isinstance(normalized.get("splitter_name"), str):
        normalized["splitter_name"] = DEFAULT_SPLITTER_NAME

    if "random_state" not in normalized and "seed" in normalized:
        normalized["random_state"] = normalized["seed"]

    index_lists = {
        split: normalized[split]
        for split in INDEX_KEY_BY_SPLIT
        if isinstance(normalized.get(split), list)
    }
    if index_lists:
        splitted_indexes = dict(normalized.get("splitted_indexes") or {})
        for split, indexes in index_lists.items():
            splitted_indexes.setdefault(INDEX_KEY_BY_SPLIT[split], indexes)
            del normalized[split]
        normalized["splitted_indexes"] = splitted_indexes
        normalized.setdefault("splitType", "manual")

    return normalized


def schema_placeholder_defaults(splitter_cls: Type) -> Dict[str, Any]:
    """Collect the placeholder value declared for each schema parameter.

    The frontend seeds its form with these values, so filling them in makes a
    partial payload (for example a manual split, which carries no
    proportions) validate exactly as the form would have submitted it.

    Parameters
    ----------
    splitter_cls : type
        A splitter class exposing ``get_schema``.

    Returns
    -------
    dict
        Parameter name to placeholder value, skipping parameters that declare
        no placeholder.
    """
    properties = splitter_cls.get_schema().get("properties", {})
    return {
        name: prop["placeholder"]
        for name, prop in properties.items()
        if "placeholder" in prop
    }


def splitter_class_for(session_splits: Dict[str, Any], component_registry) -> Type:
    """Resolve the splitter class that produced a run.

    Parameters
    ----------
    session_splits : dict
        The ``ModelSession.splits`` payload, already parsed.
    component_registry : ComponentRegistry
        Registry used to resolve the splitter by name.

    Returns
    -------
    type
        The splitter class named by the payload.

    Raises
    ------
    ValueError
        If the payload names a splitter that is not registered.
    """
    splitter_name = normalize_splits_payload(session_splits)["splitter_name"]
    if splitter_name not in component_registry:
        raise ValueError(f"Splitter {splitter_name} does not exist in the registry.")
    return component_registry[splitter_name]["class"]


def explainable_indexes(
    splitter_class: Type, split_indexes: Dict[str, Any]
) -> Tuple[List[int], List[int], List[int]]:
    """Resolve the rows an explainer may use for a run of a given splitter.

    The partitions and their names come from the splitter itself; this maps them
    onto the three slots the explainers' dataset dictionary is built from.

    Parameters
    ----------
    splitter_class : type
        The splitter that produced the run.
    split_indexes : dict
        The ``Run.split_indexes`` payload, already parsed.

    Returns
    -------
    tuple[list[int], list[int], list[int]]
        Row indexes for the train, evaluation and validation slots. Splitters
        without a validation partition return an empty third list.

    Raises
    ------
    ValueError
        If the run has no rows in the partition explanations are measured on.
    """
    try:
        partitions = splitter_class.explainable_partitions(split_indexes)
    except (KeyError, NotImplementedError, TypeError) as e:
        raise ValueError(
            "The run's split indexes do not match the splitter that produced "
            "it, so there is no data to explain."
        ) from e

    training = splitter_class.TRAINING_PARTITION
    unseen = {
        name: indexes
        for name, indexes in partitions.items()
        if name != training and indexes
    }
    if not unseen:
        raise ValueError(
            "The run has no rows outside the data the model was fitted on "
            f"(its {splitter_class.EVALUATION_PARTITION} partition is empty), "
            "so there is nothing to explain."
        )

    # Explanations are measured on the splitter's preferred partition, falling
    # back to whichever unseen partition the run actually filled: a holdout run
    # configured without a test partition is explained on validation.
    evaluation = unseen.get(splitter_class.EVALUATION_PARTITION) or next(
        iter(unseen.values())
    )

    return partitions.get(training, []), evaluation, partitions.get("val", [])
