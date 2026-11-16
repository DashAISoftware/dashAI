import inspect
import logging
from typing import Any, Union

from beartype import beartype
from beartype.typing import Dict, List, Type

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.registry.relationship_manager import RelationshipManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_NAMESPACE = "dashai_plugins"


def owner_of(module: str) -> str:
    """The plugin id a component's module belongs to, or ``"dashai"``."""
    if not module.startswith(_NAMESPACE + ".p"):
        return "dashai"
    return module.split(".")[1][1:].replace("_", "-")


def component_id(cls_or_obj) -> str:
    """A component's id: its class name, ``<plugin-id>:Class`` for a plugin's."""
    cls = cls_or_obj if isinstance(cls_or_obj, type) else type(cls_or_obj)
    owner = owner_of(cls.__module__)
    return cls.__name__ if owner == "dashai" else f"{owner}:{cls.__name__}"


def _field_owners(schema_cls: Any) -> Dict[str, str]:
    """Each field of ``schema_cls`` and the plugin of the class that declares
    it (``"dashai"`` for dashAI's); a subclass's own fields win."""
    owners: Dict[str, str] = {}
    for klass in reversed(getattr(schema_cls, "__mro__", ())):
        for name in inspect.get_annotations(klass):
            owners[name] = owner_of(klass.__module__)
    return owners


class AmbiguousComponentError(KeyError):
    """A short name that more than one plugin's component has."""


class ComponentRegistry:
    """An object that stores all components registered in a execution of DashAI.

    Each object registered is saved as a component dict, which is an abstraction layer
    that stores all relevant component attributes.

    An example of component dict is:

    ```python
    {
        "name": "Component1",  # Component name.
        "type": "ComponentType",  # Component type.
        "class": Component1,  # Component class.
        "configurable_object": False,  # True if the object is a configurable one.
        "schema": {...},  # Configurable object schema if applies.
        "metadata": {...},  # Component metadata if applies.
        "description": "...",  # An object description.
        "display_name": "...",  # A readable label.
        "color": "...",  # A color associated to the component.
        "downloaded": True,  # False until a download-required component is fetched.
    }
    ```

    By default, every method of the registry should return a component dict or a list
    of component dicts.
    """

    @beartype
    def __init__(
        self,
        initial_components: Union[List[type], None] = None,
    ) -> None:
        """Initialize the component registry.

        Parameters
        ----------
        initial_components : Union[List[type], None]
            List with the initial objects to be entered in the registry,
            by default None.

        Raises
        ------
        TypeError
            If initial_components is not a list of types.
        TypeError
            If the task registry is neither none nor an instance of BaseRegistry.
        """
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._relationship_manager = RelationshipManager()

        if initial_components is not None:
            for component in initial_components:
                self.register_component(component)

        # Ensure every component carries the downloaded flag.
        self.seed_download_status()

    @property
    @beartype
    def registry(self) -> Dict[str, Dict[str, Any]]:
        """Obtains the internal registry object.

        Returns
        -------
        Dict[str, Dict[str, Any]]
            Registry dict.
        """
        return self._registry

    @registry.setter
    def registry(self, _: Any) -> None:
        raise RuntimeError("It is not allowed to set the registry values directly.")

    @registry.deleter
    def registry(self, _: Any) -> None:
        raise RuntimeError("It is not allowed to delete the registry list.")

    @beartype
    def __contains__(self, item: str) -> bool:
        """Indicate if some component is in the registry.

        Parameters
        ----------
        item : str
            The component name to be searched.

        Returns
        -------
        bool
            True if the component exists in the task registry, False otherwise.
        """
        try:
            self.resolve(item)
        except KeyError:
            return False
        return True

    @beartype
    def __getitem__(self, item: str) -> Dict[str, Any]:
        """Obtain a component from the registry using an indexer.

        Parameters
        ----------
        item : str
            A string to be used as an indexer.

        Returns
        -------
        Dict[str, type]
            The request component dict.

        Raises
        ------
        TypeError
            If the indexer is not a string.
        KeyError
            If the object does not exist in the registry.
        """
        return self.resolve(item)

    def _exact(self, component_id: str) -> Union[Dict[str, Any], None]:
        """The component registered as ``component_id``, or None."""
        for base_type_container in self._registry.values():
            if component_id in base_type_container:
                return base_type_container[component_id]
        return None

    @beartype
    def resolve(self, name: str, base_type: Union[str, None] = None) -> Dict[str, Any]:
        """The component ``name`` refers to: the one with that id, else the only
        plugin component with that class name. Only among ``base_type``'s
        components, if given.

        Raises
        ------
        AmbiguousComponentError
            If several plugins' components have that class name.
        KeyError
            If no component matches.
        """
        containers = (
            list(self._registry.values())
            if base_type is None
            else [self._registry.get(base_type, {})]
        )
        for base_type_container in containers:
            if name in base_type_container:
                return base_type_container[name]
        if ":" not in name:
            matches = [
                c
                for base_type_container in containers
                for c in base_type_container.values()
                if c["class"].__name__ == name
            ]
            if len(matches) == 1:
                return matches[0]
            if matches:
                raise AmbiguousComponentError(
                    f"Component '{name}' is ambiguous: "
                    f"{sorted(c['name'] for c in matches)}"
                )
        raise KeyError(f"Component '{name}' does not exists in the registry.")

    def _canonical_ref(self, ref: str, owner: str) -> str:
        """``ref`` as an id: a plugin's short name for its own component gets
        qualified; one of dashAI's, or already qualified, stays."""
        if not ref or ":" in ref or owner == "dashai" or self._exact(ref) is not None:
            return ref
        return f"{owner}:{ref}"

    def _canonical_parent(self, parent: str, owner: str) -> str:
        """``parent`` as an id: a base of dashAI's components stays, a plugin's
        own base gets qualified."""
        if ":" in parent or owner == "dashai":
            return parent
        for base_type_container in self._registry.values():
            for cid, entry in base_type_container.items():
                if ":" not in cid and any(
                    cls_.__name__ == parent for cls_ in entry["class"].__mro__
                ):
                    return parent
        return f"{owner}:{parent}"

    def canonical_schema(self, schema: Any, owner: str, schema_cls: Any = None) -> Any:
        """``schema`` with the components and bases its fields name as ids.
        A field's short names are of the plugin whose class in ``schema_cls``
        (the pydantic model ``schema`` comes from) declares it, else ``owner``'s."""
        if owner == "dashai" or not schema:
            return schema
        field_owners = _field_owners(schema_cls)
        for name, field in schema.get("properties", {}).items():
            field_owner = field_owners.get(name, owner)
            # A list of components declares its base in ``items`` and its
            # placeholder as a list.
            for spec in (field, field.get("items")):
                if isinstance(spec, dict) and isinstance(spec.get("parent"), str):
                    spec["parent"] = self._canonical_parent(spec["parent"], field_owner)
            placeholder = field.get("placeholder")
            values = placeholder if isinstance(placeholder, list) else [placeholder]
            for value in values:
                if isinstance(value, dict) and "component" in value:
                    value["component"] = self._canonical_ref(
                        value["component"], field_owner
                    )
        return schema

    @beartype
    def get_base_type(self, new_component: type) -> str:
        # select only base classes ancestors
        component_base_ancestors = [
            ancestor
            for ancestor in new_component.__mro__
            if ancestor.__name__.startswith("Base")
        ]

        base_classes_cantidates = [
            ancestor_cls
            for ancestor_cls in component_base_ancestors
            if hasattr(ancestor_cls, "TYPE")
        ]

        # check if there is only one type candidate.
        if len(base_classes_cantidates) == 0:
            raise TypeError(
                f"Component {new_component.__name__} does not inherit from any DashAI "
                f"base class with a 'TYPE' class attribute. Classes that the component "
                f"extends (MRO): {new_component.__mro__}."
            )
        elif len(base_classes_cantidates) > 1:
            raise TypeError(
                f"Component {new_component.__name__} has more than one base class with "
                f"a 'TYPE' class attribute: "
                f"{[_cls.__name__ for _cls in base_classes_cantidates]}."
            )

        if not hasattr(base_classes_cantidates[0], "TYPE"):
            raise TypeError(
                f"{base_classes_cantidates[0].__name__} "
                "base class has not class attribute TYPE"
            )

        return base_classes_cantidates[0].TYPE

    @beartype
    def _compatible_ids(self, component: type) -> List[str]:
        """The union of ``COMPATIBLE_COMPONENTS`` declared along the MRO, as ids.

        Each class in the component's MRO contributes only the entries it
        declares itself, so mixins and base classes compose instead of the
        first declaration shadowing the rest (e.g. a task mixin declaring the
        task plus a model base class declaring its supported explainers).
        A short name is of the plugin whose class declares it, also when
        another plugin's class inherits it.

        Parameters
        ----------
        component : type
            The component class to inspect.

        Returns
        -------
        List[str]
            Deduplicated compatible component ids in MRO order.
        """
        compatible_ids: List[str] = []
        for klass in component.__mro__:
            owner = owner_of(klass.__module__)
            for entry in vars(klass).get("COMPATIBLE_COMPONENTS", []):
                # Not a name (e.g. a class): the return type check refuses it.
                cid = (
                    self._canonical_ref(entry, owner)
                    if isinstance(entry, str)
                    else entry
                )
                if cid not in compatible_ids:
                    compatible_ids.append(cid)
        return compatible_ids

    @beartype
    def register_component(self, new_component: Type) -> None:
        """Register a component within the registry.

        Parameters
        ----------
        new_component : Type
            The object to be registred.


        """
        base_type = self.get_base_type(new_component)

        is_configurable_object = "ConfigObject" in [
            _class.__name__ for _class in new_component.__mro__
        ]

        if is_configurable_object and not hasattr(new_component, "get_schema"):
            raise TypeError(
                f"The component {new_component.__name__} does not implement "
                '"get_schema" method although it was declared as a configurable '
                "object."
            )

        _metadata = (
            new_component.get_metadata()
            if hasattr(new_component, "get_metadata")
            else None
        )

        # Format description and display_name as MultilingualString if they are str
        if hasattr(new_component, "DESCRIPTION"):
            description = new_component.DESCRIPTION
            if isinstance(description, str):
                new_component.DESCRIPTION = MultilingualString(en=description)

        if hasattr(new_component, "DISPLAY_NAME"):
            display_name = new_component.DISPLAY_NAME
            if isinstance(display_name, str):
                new_component.DISPLAY_NAME = MultilingualString(en=display_name)

        required_credentials = list(
            getattr(new_component, "REQUIRED_CREDENTIALS", []) or []
        )
        optional_credentials = list(
            getattr(new_component, "OPTIONAL_CREDENTIALS", []) or []
        )

        cid = component_id(new_component)
        owner = owner_of(new_component.__module__)
        new_register_component = {
            "name": cid,
            "type": base_type,
            "class": new_component,
            "configurable_object": is_configurable_object,
            "schema": self.canonical_schema(
                new_component.get_schema(),
                owner,
                getattr(new_component, "SCHEMA", None),
            )
            if is_configurable_object
            else None,
            "metadata": _metadata,
            "description": getattr(new_component, "DESCRIPTION", None),
            "display_name": getattr(new_component, "DISPLAY_NAME", None),
            "color": getattr(new_component, "COLOR", None),
            "required_credentials": required_credentials,
            "optional_credentials": optional_credentials,
            "credentials_satisfied": len(required_credentials) == 0,
        }
        compatible_components = self._compatible_ids(new_component)

        # Nothing below fails: a component that can't be registered leaves the
        # registry as it was. An id already registered gets replaced: undo
        # what it previously contributed (relationships included) first.
        previous = self._exact(cid)
        if previous is not None:
            self.unregister_component(previous["class"])

        if base_type not in self._registry:
            self._registry[base_type] = {cid: new_register_component}
        else:
            self._registry[base_type][cid] = new_register_component

        self._set_download_status(new_register_component)

        for compatible_component in compatible_components:
            self._relationship_manager.add_relationship(
                cid,
                compatible_component,
                "compatible_components",
            )

        for credential_name in required_credentials:
            self._relationship_manager.add_relationship(
                cid, credential_name, "required_credentials"
            )

        for credential_name in optional_credentials:
            self._relationship_manager.add_relationship(
                cid, credential_name, "optional_credentials"
            )

    def seed_download_status(self) -> None:
        """Populate the ``downloaded`` flag for every registered component.

        Downloadable components are checked via their ``is_downloaded`` method;
        all other components are always considered available.
        """
        for type_dict in self._registry.values():
            for _name, component_dict in type_dict.items():
                self._set_download_status(component_dict)

    def refresh_download_status(self, name: str) -> bool:
        """Recheck a single component's download status and update the registry.

        Parameters
        ----------
        name : str
            The component class name.

        Returns
        -------
        bool
            The reconciled ``downloaded`` value.
        """
        component_dict = self[name]
        return self._set_download_status(component_dict)

    def _set_download_status(self, component_dict: dict) -> bool:
        """Set the ``downloaded`` key on a component dict and return the value.

        Parameters
        ----------
        component_dict : dict
            A registry component dict to update in place.

        Returns
        -------
        bool
            The resolved download status for the component.

        Notes
        -----
        Exceptions from ``is_downloaded()`` are suppressed and treated as
        not-downloaded, so a component may appear not-downloaded without raising.
        """
        component_class = component_dict["class"]
        requires = bool(getattr(component_class, "REQUIRES_DOWNLOAD", False))
        if requires:
            try:
                downloaded = bool(component_class.is_downloaded())
            except Exception:
                downloaded = False
        else:
            downloaded = True
        component_dict["downloaded"] = downloaded
        return downloaded

    @beartype
    def unregister_component(self, component: Type) -> None:
        """Remove a component from the registry.

        Parameters
        ----------
        component : Type
            The object to be registred.


        """
        base_type = self.get_base_type(component)
        cid = component_id(component)

        try:
            self._registry[base_type].pop(cid)
            logger.info(f"Component removed: {cid}")
        except KeyError as e:
            raise ValueError(
                f"Error: Component named {cid} does not exist "
                f"in the registry. Exception: {e}"
            ) from e

        for compatible_component in self._compatible_ids(component):
            self._relationship_manager.remove_relationship(
                cid, compatible_component, "compatible_components"
            )

        for credential_name in getattr(component, "REQUIRED_CREDENTIALS", []) or []:
            self._relationship_manager.remove_relationship(
                cid, credential_name, "required_credentials"
            )

        for credential_name in getattr(component, "OPTIONAL_CREDENTIALS", []) or []:
            self._relationship_manager.remove_relationship(
                cid, credential_name, "optional_credentials"
            )

    @beartype
    def get_components_by_types(
        self,
        select: Union[str, List[str], None] = None,
        ignore: Union[str, List[str], None] = None,
    ) -> List[Dict[str, Any]]:
        """Obtain all the components dicts according to the indicated types.

        The function allows to select all components of one or several types at the
        same time (through the select parameter) or to ignore one or several
        types (through the ignore parameter).

        In case select and ignore are None, the function returns all registered
        components.

        In all cases, the function return a list of dictionaries describing
        the components.


        Parameters
        ----------
        select : Union[str, List[str], None], optional
            The types of components selected for return, by default None
        ignore : Union[str, List[str], None], optional
            The types of components ignored for return, by default None

        Returns
        -------
        List[Dict[str, Any]]
            A list with the selected components.

        Raises
        ------
        ValueError
            If select and ignore are not None.
        TypeError
            When select provided, if select is not a string o a list of strings.
        TypeError
            When select provided, if some element of select list is not a string.
        ValueError
            When select provided, when a provided type does not exists in the registry.
        TypeError
            When ignore provided, if ignore is not a string o a list of strings.
        TypeError
            When ignore provided, if some element of ignore list is not a string.
        ValueError
            When ignore provided, when a provided type does not exists in the registry.
        """
        if select is not None and ignore is not None:
            raise ValueError(
                "Only select or ignore can be provided, not both at the same time."
            )

        # Case 1: neither select nor ignore was provided.
        if select is None and ignore is None:
            return [
                self.__getitem__(component)
                for component_type in self.registry
                for component in self._registry[component_type]
            ]

        # Case 2: only select is provided.
        if select is not None:
            # check passed select types
            if not isinstance(select, (str, list)):
                raise TypeError(
                    f"Select must be a string or an array of strings, got {select}."
                )
            # cast select into string
            if isinstance(select, str):
                select = [select]

            if len(select) == 0:
                raise ValueError("Select list has not types to select.")

            for idx, component_type in enumerate(select):
                if not isinstance(component_type, str):
                    raise TypeError(
                        f"Select type at position {idx} should be a string, "
                        f"got {component_type}."
                    )
                if component_type not in self._registry:
                    raise ValueError(
                        f"Component type {component_type} does not exist in the "
                        "registry."
                    )

            return [
                self.__getitem__(component)
                for selected_type in select
                for component in self._registry[selected_type]
            ]

        # Case 3: only ignore is provided.
        else:
            # check passed ignore types
            if not isinstance(ignore, (str, list)):
                raise TypeError(
                    f"Ignore must be a string or an array of strings, got {ignore}."
                )
            # cast select into string
            if isinstance(ignore, str):
                ignore = [ignore]

            if len(ignore) == 0:
                raise ValueError("Ignore list has not types to select.")

            # check each type
            for idx, component_type in enumerate(ignore):
                if not isinstance(component_type, str):
                    raise TypeError(
                        f"Ignore type at position {idx} should be a string, got "
                        f"{component_type}."
                    )
                if component_type not in self._registry:
                    raise ValueError(
                        f"Component type {component_type} does not exist in the "
                        "registry."
                    )

            return [
                self.__getitem__(component)
                for component_type in self.registry
                if component_type not in ignore
                for component in self._registry[component_type]
            ]

    @beartype
    def get_child_components(
        self, parent_name: str, recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """Obtain the compoments that inherits from the specified parent component.

        Note that the method will not raise an exception when a non existant parent
        name is passed.

        Parameters
        ----------
        parent_name : str
            Id of the parent component (see ``component_id``)
        recursive : bool
            If True, search for all child and subchild classes.

        Returns
        -------
        List[Dict[str, Any]]
            List of component dicts that inherits from the parent component.
        """
        selected_components = []
        for type_registry in self._registry.values():
            for component_dict in type_registry.values():
                component_bases = (
                    component_dict["class"].__mro__
                    if recursive
                    else component_dict["class"].__bases__
                )
                component_bases_names = [component_id(cls_) for cls_ in component_bases]

                if parent_name in component_bases_names:
                    selected_components.append(component_dict)

        return selected_components

    @beartype
    def get_related_components(self, name: str) -> List[Dict[str, Any]]:
        """Obtain any related component of the given component name.

        If the component has no related components, then the method returns an empty
        list. Related names that are not registered components (e.g. an explainer
        declared by a model but provided by an uninstalled plugin) are skipped.

        Parameters
        ----------
        name : str
            A registered component name.

        Returns
        -------
        List[Dict[str, Any]]
            A list with component dicti with all related components.

        Raises
        ------
        KeyError
            If component id does not exists in the registry.
        """
        # A subclass also takes what was declared compatible with its ancestors.
        related = dict.fromkeys(
            related_id
            for klass in self.resolve(name)["class"].__mro__
            for related_id in self._relationship_manager.get(
                component_id(klass), "compatible_components"
            )
        )
        return [
            self._exact(related_component_id)
            for related_component_id in related
            if self._exact(related_component_id) is not None
        ]

    @beartype
    def get_required_credentials(self, component_id: str) -> List[str]:
        """Return the names of credentials a component requires.

        Parameters
        ----------
        component_id : str
            A registered component name.

        Returns
        -------
        List[str]
            Names of required credential components (empty if none).
        """
        return self._relationship_manager.get(component_id, "required_credentials")

    @beartype
    def get_optional_credentials(self, component_id: str) -> List[str]:
        """Return the names of credentials a component can optionally use.

        Parameters
        ----------
        component_id : str
            A registered component name.

        Returns
        -------
        List[str]
            Names of optional credential components (empty if none).
        """
        return self._relationship_manager.get(component_id, "optional_credentials")

    @beartype
    def refresh_credentials_status(
        self,
        statuses: Dict[str, bool],
        only: Union[List[str], None] = None,
    ) -> None:
        """Recompute the ``credentials_satisfied`` flag of components.

        A component is satisfied when every credential in its
        ``required_credentials`` is verified. Components with no required
        credentials are always satisfied.

        Parameters
        ----------
        statuses : Dict[str, bool]
            Mapping of credential component name to verified status.
        only : Union[List[str], None]
            If provided, only these component names are recomputed. If None,
            all components are recomputed.
        """
        for type_registry in self._registry.values():
            for name, component_dict in type_registry.items():
                if only is not None and name not in only:
                    continue
                required = component_dict.get("required_credentials", [])
                component_dict["credentials_satisfied"] = all(
                    statuses.get(credential_name, False) for credential_name in required
                )
