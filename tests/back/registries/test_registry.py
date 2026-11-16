import pytest
from beartype.roar import BeartypeException
from kink import di

from DashAI.back.config_object import ConfigObject
from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.dependencies.registry.component_registry import (
    AmbiguousComponentError,
    component_id,
)
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.model_factory import ModelFactory

TEST_SCHEMA_1 = {
    "properties": {
        "parameter_1": {
            "type": "number",
        },
    }
}

TEST_SCHEMA_2 = {
    "properties": {
        "parameter_2": {
            "type": "string",
            "enum": ["a", "b"],
        },
    }
}


class BaseConfigComponent1(ConfigObject):
    TYPE = "ConfigComponent1"


class BaseConfigComponent2(ConfigObject):
    TYPE = "ConfigComponent2"


class BaseStaticComponent:
    TYPE = "StaticComponent"


class Component1(BaseConfigComponent1):
    @classmethod
    def get_schema(cls):
        return TEST_SCHEMA_1


class Component2(BaseConfigComponent1):
    @classmethod
    def get_schema(cls):
        return TEST_SCHEMA_2


class SubComponent1(Component1):
    @classmethod
    def get_schema(cls):
        return TEST_SCHEMA_1


class Component3(BaseStaticComponent):
    DESCRIPTION = "Some static component"


class RelatedComponent1(BaseStaticComponent):
    COMPATIBLE_COMPONENTS = ["Component1"]


class RelatedComponent2(BaseStaticComponent):
    COMPATIBLE_COMPONENTS = ["Component1", "Component2"]


class ComponentWithTwoBaseClasses(BaseConfigComponent1, BaseConfigComponent2): ...


class NoComponent: ...


class DatabaseHelper:
    """Unrelated class whose name merely CONTAINS 'Base' as a substring."""

    TYPE = "unrelated"


class ComponentWithBaseSubstringAncestor(BaseConfigComponent1, DatabaseHelper):
    @classmethod
    def get_schema(cls):
        return TEST_SCHEMA_1


class RelatedMixin:
    COMPATIBLE_COMPONENTS = ["Component1"]


class RelatedParentComponent(BaseStaticComponent):
    COMPATIBLE_COMPONENTS = ["Component2"]


class CombinedRelatedComponent(RelatedMixin, RelatedParentComponent):
    # Redeclares an inherited entry on purpose: the union must deduplicate.
    COMPATIBLE_COMPONENTS = ["Component1"]


COMPONENT1_DICT = {
    "name": "Component1",
    "type": "ConfigComponent1",
    "class": Component1,
    "configurable_object": True,
    "schema": {"properties": {"parameter_1": {"type": "number"}}},
    "metadata": None,
    "description": None,
    "display_name": None,
    "color": None,
    "required_credentials": [],
    "optional_credentials": [],
    "credentials_satisfied": True,
    "downloaded": True,
}
COMPONENT2_DICT = {
    "name": "Component2",
    "type": "ConfigComponent1",
    "class": Component2,
    "configurable_object": True,
    "schema": {"properties": {"parameter_2": {"type": "string", "enum": ["a", "b"]}}},
    "metadata": None,
    "description": None,
    "display_name": None,
    "color": None,
    "required_credentials": [],
    "optional_credentials": [],
    "credentials_satisfied": True,
    "downloaded": True,
}
SUBCOMPONENT1_DICT = {
    "name": "SubComponent1",
    "type": "ConfigComponent1",
    "class": SubComponent1,
    "configurable_object": True,
    "schema": {"properties": {"parameter_1": {"type": "number"}}},
    "metadata": None,
    "description": None,
    "display_name": None,
    "color": None,
    "required_credentials": [],
    "optional_credentials": [],
    "credentials_satisfied": True,
    "downloaded": True,
}
COMPONENT3_DICT = {
    "name": "Component3",
    "type": "StaticComponent",
    "class": Component3,
    "configurable_object": False,
    "schema": None,
    "metadata": None,
    "description": "Some static component",
    "display_name": None,
    "color": None,
    "required_credentials": [],
    "optional_credentials": [],
    "credentials_satisfied": True,
    "downloaded": True,
}
COMPONENT3_DICT_MS = COMPONENT3_DICT.copy()
COMPONENT3_DICT_MS["description"] = MultilingualString(en="Some static component")

RELATED_COMPONENT1_DICT = {
    "name": "RelatedComponent1",
    "type": "StaticComponent",
    "class": RelatedComponent1,
    "configurable_object": False,
    "schema": None,
    "metadata": None,
    "description": None,
    "display_name": None,
    "color": None,
    "required_credentials": [],
    "optional_credentials": [],
    "credentials_satisfied": True,
    "downloaded": True,
}
RELATED_COMPONENT2_DICT = {
    "name": "RelatedComponent2",
    "type": "StaticComponent",
    "class": RelatedComponent2,
    "configurable_object": False,
    "schema": None,
    "metadata": None,
    "description": None,
    "display_name": None,
    "color": None,
    "required_credentials": [],
    "optional_credentials": [],
    "credentials_satisfied": True,
    "downloaded": True,
}


def test__init__empty_tasks():
    # no initial components (by default None).
    test_registry = ComponentRegistry()

    assert hasattr(test_registry, "_registry")
    assert hasattr(test_registry, "registry")
    assert hasattr(test_registry, "_relationship_manager")

    assert isinstance(test_registry._registry, dict)
    assert test_registry.registry == {}
    assert test_registry.registry == test_registry._registry

    # inital components as a empty list
    test_registry = ComponentRegistry(initial_components=[])

    assert hasattr(test_registry, "_registry")
    assert hasattr(test_registry, "registry")
    assert hasattr(test_registry, "_relationship_manager")

    assert isinstance(test_registry._registry, dict)
    assert test_registry.registry == {}
    assert test_registry.registry == test_registry._registry


def test_basic_register_component():
    # this test does not include relationship creation.
    test_registy = ComponentRegistry()
    test_registy.register_component(Component1)

    assert test_registy.registry == {
        "ConfigComponent1": {"Component1": COMPONENT1_DICT}
    }


def test_basic_register_component_class_with_no_type():
    # this test does not include relationship creation.
    test_registy = ComponentRegistry()

    with pytest.raises(
        TypeError,
        match=(
            r"Component NoComponent does not inherit from any DashAI base class with "
            r"a 'TYPE' class attribute.*"
        ),
    ):
        test_registy.register_component(NoComponent)


def test__init__with_components():
    # init the test with two components
    test_registry = ComponentRegistry(
        initial_components=[
            Component1,
            Component2,
            Component3,
        ]
    )
    assert hasattr(test_registry, "_registry")
    assert hasattr(test_registry, "registry")
    assert isinstance(test_registry.registry, dict)

    assert test_registry.registry == {
        "ConfigComponent1": {
            "Component1": COMPONENT1_DICT,
            "Component2": COMPONENT2_DICT,
        },
        "StaticComponent": {"Component3": COMPONENT3_DICT_MS},
    }


def test_get_base_type_two_base_classes_typerror():
    test_register = ComponentRegistry()
    with pytest.raises(
        TypeError,
        match=(
            r"Component ComponentWithTwoBaseClasses has more than one base "
            r"class with a 'TYPE' class attribute: "
            r"\['BaseConfigComponent1', 'BaseConfigComponent2'\]."
        ),
    ):
        test_register.get_base_type(ComponentWithTwoBaseClasses)


def test_get_base_type_ignores_substring_base_match():
    # A class merely containing "Base" (e.g. "DatabaseHelper") must not be
    # mistaken for a real DashAI base class.
    test_register = ComponentRegistry()

    assert (
        test_register.get_base_type(ComponentWithBaseSubstringAncestor)
        == "ConfigComponent1"
    )


def test_get_base_type_no_base_classes_typerror():
    test_register = ComponentRegistry()
    with pytest.raises(
        TypeError,
        match=(
            r"Component NoComponent does not inherit from any DashAI base class "
            r"with a 'TYPE' class attribute.*"
        ),
    ):
        test_register.get_base_type(NoComponent)


def test_get_base_type():
    test_register = ComponentRegistry()
    assert test_register.get_base_type(Component3) == "StaticComponent"
    assert test_register.get_base_type(Component1) == "ConfigComponent1"
    assert test_register.get_base_type(Component2) == "ConfigComponent1"


def test__contains__():
    test_registry = ComponentRegistry(
        initial_components=[
            Component1,
            Component3,
        ]
    )

    assert "Component1" in test_registry
    assert "Component3" in test_registry
    assert "Component2" not in test_registry


def test__getitem__():
    test_registry = ComponentRegistry(
        initial_components=[
            Component1,
            Component2,
            Component3,
        ]
    )

    assert test_registry["Component1"] == COMPONENT1_DICT
    assert test_registry["Component2"] == COMPONENT2_DICT
    assert test_registry["Component3"] == COMPONENT3_DICT_MS


def test__getitem__key_error():
    test_registry = ComponentRegistry(
        initial_components=[
            Component1,
            Component2,
        ]
    )

    with pytest.raises(
        KeyError,
        match=r"Component 'StaticComponent1' does not exists in the registry.",
    ):
        test_registry["StaticComponent1"]


def test_get_components_by_type_select_and_ignore_none():
    test_registry = ComponentRegistry(
        initial_components=[
            Component1,
            Component2,
            SubComponent1,
            Component3,
        ]
    )

    # test with one component type
    assert test_registry.get_components_by_types() == [
        COMPONENT1_DICT,
        COMPONENT2_DICT,
        SUBCOMPONENT1_DICT,
        COMPONENT3_DICT_MS,
    ]


def test_get_components_by_type_select_param():
    test_registry = ComponentRegistry(
        initial_components=[
            Component1,
            Component2,
            SubComponent1,
            Component3,
        ]
    )

    # test with one component type
    assert test_registry.get_components_by_types(select="ConfigComponent1") == [
        COMPONENT1_DICT,
        COMPONENT2_DICT,
        SUBCOMPONENT1_DICT,
    ]

    # test with another component type
    assert test_registry.get_components_by_types(select="StaticComponent") == [
        COMPONENT3_DICT_MS
    ]

    # test with one component type as list
    assert test_registry.get_components_by_types(select=["ConfigComponent1"]) == [
        COMPONENT1_DICT,
        COMPONENT2_DICT,
        SUBCOMPONENT1_DICT,
    ]

    # test with two component type as list
    assert test_registry.get_components_by_types(
        select=["ConfigComponent1", "StaticComponent"]
    ) == [COMPONENT1_DICT, COMPONENT2_DICT, SUBCOMPONENT1_DICT, COMPONENT3_DICT_MS]


def test_get_components_by_type_select_param_errors():
    test_registry = ComponentRegistry(
        initial_components=[
            Component1,
            Component2,
            SubComponent1,
            Component3,
        ]
    )

    with pytest.raises(ValueError, match=r"Select list has not types to select."):
        test_registry.get_components_by_types(select=[])

    with pytest.raises(
        ValueError,
        match=r"Component type UnexistantComponents does not exist in the registry.",
    ):
        test_registry.get_components_by_types(
            select=["ConfigComponent1", "UnexistantComponents"]
        )


def test_get_components_by_type_ignore_param():
    test_registry = ComponentRegistry(
        initial_components=[
            Component1,
            Component2,
            SubComponent1,
            Component3,
        ]
    )

    # test with another component type
    assert test_registry.get_components_by_types(ignore="ConfigComponent1") == [
        COMPONENT3_DICT_MS
    ]
    # test with one component type
    assert test_registry.get_components_by_types(ignore="StaticComponent") == [
        COMPONENT1_DICT,
        COMPONENT2_DICT,
        SUBCOMPONENT1_DICT,
    ]

    # test with one component type as list
    assert test_registry.get_components_by_types(ignore=["ConfigComponent1"]) == [
        COMPONENT3_DICT_MS
    ]

    # test with two component type as list
    assert (
        test_registry.get_components_by_types(
            ignore=["ConfigComponent1", "StaticComponent"]
        )
        == []
    )


def test_get_components_by_type_ignore_param_errors():
    test_registry = ComponentRegistry(
        initial_components=[
            Component1,
            Component2,
            SubComponent1,
            Component3,
        ]
    )

    with pytest.raises(ValueError, match=r"Ignore list has not types to select."):
        test_registry.get_components_by_types(ignore=[])

    with pytest.raises(
        ValueError,
        match=r"Component type UnexistantComponents does not exist in the registry.",
    ):
        test_registry.get_components_by_types(
            ignore=["ConfigComponent1", "UnexistantComponents"]
        )


def test_get_child_classes():
    test_registry = ComponentRegistry(
        initial_components=[
            Component1,
            Component2,
            SubComponent1,
        ]
    )
    assert test_registry.get_child_components("BaseConfigComponent1") == [
        COMPONENT1_DICT,
        COMPONENT2_DICT,
    ]
    assert test_registry.get_child_components(
        "BaseConfigComponent1", recursive=True
    ) == [
        COMPONENT1_DICT,
        COMPONENT2_DICT,
        SUBCOMPONENT1_DICT,
    ]
    assert test_registry.get_child_components("Component1") == [SUBCOMPONENT1_DICT]
    assert test_registry.get_child_components("BaseConfigComponent2") == []

    assert test_registry.get_child_components("XYZ") == []


def test_relationships_module():
    test_registry = ComponentRegistry(
        initial_components=[
            Component1,
            Component2,
            SubComponent1,
        ]
    )

    test_registry.register_component(RelatedComponent1)
    test_registry.register_component(RelatedComponent2)

    assert test_registry._relationship_manager.relations == {
        "RelatedComponent1": {"compatible_components": ["Component1"]},
        "Component1": {
            "compatible_components": ["RelatedComponent1", "RelatedComponent2"]
        },
        "RelatedComponent2": {"compatible_components": ["Component1", "Component2"]},
        "Component2": {"compatible_components": ["RelatedComponent2"]},
    }

    assert test_registry.get_related_components("Component1") == [
        RELATED_COMPONENT1_DICT,
        RELATED_COMPONENT2_DICT,
    ]

    assert test_registry.get_related_components("Component2") == [
        RELATED_COMPONENT2_DICT
    ]

    # A plugin task subclassing a native one gets the native task's splitters.
    assert test_registry.get_related_components("SubComponent1") == [
        RELATED_COMPONENT1_DICT,
        RELATED_COMPONENT2_DICT,
    ]

    assert test_registry.get_related_components("RelatedComponent1") == [
        COMPONENT1_DICT
    ]

    assert test_registry.get_related_components("RelatedComponent2") == [
        COMPONENT1_DICT,
        COMPONENT2_DICT,
    ]


def test_get_related_components_skips_unregistered_names():
    test_registry = ComponentRegistry(initial_components=[Component1])

    # RelatedComponent2 declares Component1 (registered) and Component2
    # (NOT registered): lookups must skip the unregistered name.
    test_registry.register_component(RelatedComponent2)

    assert test_registry.get_related_components("RelatedComponent2") == [
        COMPONENT1_DICT
    ]
    assert [
        component["name"]
        for component in test_registry.get_related_components("Component1")
    ] == ["RelatedComponent2"]


def test_compatible_components_merge_across_bases():
    test_registry = ComponentRegistry(
        initial_components=[
            Component1,
            Component2,
        ]
    )

    test_registry.register_component(CombinedRelatedComponent)

    # The mixin contributes "Component1", the static base "Component2";
    # the subclass redeclaration of "Component1" does not duplicate it.
    assert test_registry._relationship_manager.get(
        "CombinedRelatedComponent", "compatible_components"
    ) == [
        "Component1",
        "Component2",
    ]
    assert test_registry.get_related_components("CombinedRelatedComponent") == [
        COMPONENT1_DICT,
        COMPONENT2_DICT,
    ]
    assert [
        component["name"]
        for component in test_registry.get_related_components("Component2")
    ] == ["CombinedRelatedComponent"]

    # Unregistering removes both inherited edges symmetrically.
    test_registry.unregister_component(CombinedRelatedComponent)
    assert (
        test_registry._relationship_manager.get(
            "CombinedRelatedComponent", "compatible_components"
        )
        == []
    )
    assert test_registry.get_related_components("Component1") == []
    assert test_registry.get_related_components("Component2") == []


class SharedComponentV1(BaseStaticComponent):
    COMPATIBLE_COMPONENTS = ["RelatedComponent1"]


SharedComponentV1.__name__ = "SharedComponent"


class SharedComponentV2(BaseStaticComponent):
    COMPATIBLE_COMPONENTS = ["RelatedComponent2"]


SharedComponentV2.__name__ = "SharedComponent"


def test_register_component_overwrite_replaces_relationships_not_duplicates():
    test_registry = ComponentRegistry(
        initial_components=[RelatedComponent1, RelatedComponent2]
    )

    test_registry.register_component(SharedComponentV1)
    test_registry.register_component(SharedComponentV2)

    relations = test_registry._relationship_manager
    assert relations.get("SharedComponent", "compatible_components") == [
        "RelatedComponent2"
    ]
    assert relations.get("RelatedComponent1", "compatible_components") == ["Component1"]
    assert relations.get("RelatedComponent2", "compatible_components") == [
        "Component1",
        "Component2",
        "SharedComponent",
    ]


def test_a_failed_replacement_keeps_the_registered_component():
    class BrokenSharedComponent(BaseStaticComponent):
        COMPATIBLE_COMPONENTS = [RelatedComponent1]  # a class, not a name

    BrokenSharedComponent.__name__ = "SharedComponent"
    test_registry = ComponentRegistry(initial_components=[SharedComponentV1])

    with pytest.raises(BeartypeException):
        test_registry.register_component(BrokenSharedComponent)

    assert test_registry["SharedComponent"]["class"] is SharedComponentV1
    assert test_registry._relationship_manager.get(
        "SharedComponent", "compatible_components"
    ) == ["RelatedComponent1"]


class CredentialComponentA:
    TYPE = "Credential"


class ComponentNeedsCred(BaseStaticComponent):
    REQUIRED_CREDENTIALS = ["CredentialComponentA"]


class ComponentOptionalCred(BaseStaticComponent):
    OPTIONAL_CREDENTIALS = ["CredentialComponentA"]


def test_register_records_credential_relations_and_flag():
    reg = ComponentRegistry(
        initial_components=[ComponentNeedsCred, ComponentOptionalCred]
    )

    # required credential present -> not satisfied until verified
    assert reg["ComponentNeedsCred"]["required_credentials"] == ["CredentialComponentA"]
    assert reg["ComponentNeedsCred"]["optional_credentials"] == []
    assert reg["ComponentNeedsCred"]["credentials_satisfied"] is False

    # only optional credential -> always satisfied
    assert reg["ComponentOptionalCred"]["optional_credentials"] == [
        "CredentialComponentA"
    ]
    assert reg["ComponentOptionalCred"]["credentials_satisfied"] is True

    assert reg.get_required_credentials("ComponentNeedsCred") == [
        "CredentialComponentA"
    ]
    assert reg.get_optional_credentials("ComponentOptionalCred") == [
        "CredentialComponentA"
    ]


def test_refresh_credentials_status_updates_flag():
    reg = ComponentRegistry(initial_components=[ComponentNeedsCred])
    assert reg["ComponentNeedsCred"]["credentials_satisfied"] is False

    reg.refresh_credentials_status({"CredentialComponentA": True})
    assert reg["ComponentNeedsCred"]["credentials_satisfied"] is True

    reg.refresh_credentials_status({"CredentialComponentA": False})
    assert reg["ComponentNeedsCred"]["credentials_satisfied"] is False


def test_refresh_credentials_status_only_targets_subset():
    reg = ComponentRegistry(initial_components=[ComponentNeedsCred])
    reg.refresh_credentials_status(
        {"CredentialComponentA": True}, only=["SomeOtherComponent"]
    )
    # not in `only` -> unchanged
    assert reg["ComponentNeedsCred"]["credentials_satisfied"] is False


def test_component_id_qualifies_only_plugin_classes():
    cls = type("X", (), {"__module__": "dashai_plugins.pmy_plugin.m"})
    dashai_cls = type("X", (), {"__module__": "DashAI.back.models.m"})

    assert component_id(cls()) == component_id(cls) == "my-plugin:X"
    assert component_id(dashai_cls) == "X"
    assert component_id(Component1) == "Component1"


def _plugin_class(plugin, name, base=BaseStaticComponent, **attrs):
    module = "dashai_plugins.p" + plugin.replace("-", "_") + ".m"
    return type(name, (base,), {"__module__": module, **attrs})


def test_a_plugin_component_coexists_with_a_dashai_one_of_its_name():
    dashai = type("LogisticRegression", (BaseStaticComponent,), {})
    plugin = _plugin_class("p", "LogisticRegression")
    registry = ComponentRegistry(initial_components=[dashai, plugin])

    assert registry["LogisticRegression"]["class"] is dashai
    assert registry["p:LogisticRegression"]["class"] is plugin


def test_a_short_name_resolves_only_if_one_plugin_has_it():
    plugin = _plugin_class("a", "X")
    registry = ComponentRegistry(initial_components=[plugin])
    assert registry["X"]["class"] is plugin

    registry = ComponentRegistry(initial_components=[plugin, _plugin_class("b", "X")])
    with pytest.raises(AmbiguousComponentError):
        registry["X"]
    assert "X" not in registry


def test_a_plugin_relates_to_dashai_by_name_and_to_its_own_by_id():
    task = type("TabularClassificationTask", (BaseStaticComponent,), {})
    explainer = _plugin_class("p", "MyExplainer")
    model = _plugin_class(
        "p",
        "MyModel",
        COMPATIBLE_COMPONENTS=["TabularClassificationTask", "MyExplainer"],
    )
    registry = ComponentRegistry(initial_components=[task, explainer, model])

    related = {c["name"] for c in registry.get_related_components("p:MyModel")}
    assert related == {"TabularClassificationTask", "p:MyExplainer"}


def test_a_plugin_schema_names_its_own_components_by_id():
    def schema(cls):
        children = {
            "type": "array",
            "items": {"parent": "BaseX"},
            "placeholder": [{"component": "Sub", "params": {}}],
        }
        return {
            "properties": {
                "sub": {"placeholder": {"component": "Sub"}},
                "unset": {"placeholder": {"component": ""}},
                "own": {"parent": "BaseX"},
                "of_dashai": {"parent": "BaseModel"},
                "children": children,
            }
        }

    dashai = type("MyModel", (BaseModel,), {"get_schema": classmethod(lambda cls: {})})
    plugin = _plugin_class(
        "a", "Comp", BaseConfigComponent1, get_schema=classmethod(schema)
    )
    registry = ComponentRegistry(initial_components=[dashai, plugin])

    properties = registry["a:Comp"]["schema"]["properties"]
    assert properties["sub"]["placeholder"]["component"] == "a:Sub"
    assert properties["unset"]["placeholder"]["component"] == ""
    assert properties["own"]["parent"] == "a:BaseX"
    assert properties["of_dashai"]["parent"] == "BaseModel"
    children = properties["children"]
    assert children["items"]["parent"] == "a:BaseX"
    assert children["placeholder"] == [{"component": "a:Sub", "params": {}}]


def _plugin_child(plugin):
    """A component of ``plugin`` whose base, ``BaseX``, is the plugin's own."""
    base = _plugin_class(plugin, "BaseX", object)
    return type("Child", (base, BaseStaticComponent), {"__module__": base.__module__})


def test_the_children_of_a_plugin_base_are_only_that_plugins():
    child_a, child_b = _plugin_child("a"), _plugin_child("b")
    registry = ComponentRegistry(initial_components=[child_a, child_b])

    children = registry.get_child_components("a:BaseX")
    assert [c["class"] for c in children] == [child_a]


def test_a_plugin_model_is_a_child_of_a_dashai_base():
    model = _plugin_class(
        "p", "MyModel", BaseModel, get_schema=classmethod(lambda cls: {})
    )
    registry = ComponentRegistry(initial_components=[model])

    children = registry.get_child_components("BaseModel", recursive=True)
    assert [c["class"] for c in children] == [model]


def test_model_factory_reads_a_plugin_models_own_schema():
    def model(module, dtype):
        return type(
            "LogisticRegression",
            (BaseConfigComponent1,),
            {
                "__module__": module,
                "__init__": lambda self, **kwargs: None,
                "get_schema": classmethod(
                    lambda cls: {"properties": {"c": {"type": dtype}}}
                ),
            },
        )

    plugin = model("dashai_plugins.pp.m", "integer")
    registry = ComponentRegistry(initial_components=[model(__name__, "number"), plugin])
    di["component_registry"] = registry
    try:
        factory = ModelFactory(
            plugin,
            {"c": {"optimize": True, "fixed_value": 1, "lower_bound": 1}},
        )
    finally:
        del di["component_registry"]

    ((_, _, _, dtype),) = factory.optimizable_parameters
    assert dtype == "integer"


def _related(registry, cid):
    return {c["name"] for c in registry.get_related_components(cid)}


def _inherited_components():
    """``a:Model`` (with ``["Task"]``), its task, and ``b:Child``, which
    inherits it and names its own ``"Task"`` too."""
    task_a, task_b = _plugin_class("a", "Task"), _plugin_class("b", "Task")
    model = _plugin_class("a", "Model", COMPATIBLE_COMPONENTS=["Task"])
    child = _plugin_class("b", "Child", model, COMPATIBLE_COMPONENTS=["Task"])
    return task_a, task_b, model, child


def test_inherited_compatible_components_ownership():
    task_a, task_b, model, child = _inherited_components()
    child_first = ComponentRegistry(initial_components=[child, model, task_a, task_b])
    child_last = ComponentRegistry(initial_components=[task_a, task_b, model, child])

    assert _related(child_first, "b:Child") == {"a:Task", "b:Task"}
    assert _related(child_last, "b:Child") == {"a:Task", "b:Task"}


def test_inherited_compatible_components_unregistration():
    task_a, task_b, model, child = _inherited_components()
    registry = ComponentRegistry(initial_components=[task_a, task_b, model, child])

    registry.unregister_component(child)

    assert _related(registry, "a:Task") == {"a:Model"}
    assert _related(registry, "a:Model") == {"a:Task"}


def test_inherited_schema_field_ownership():
    class ParentSchema(BaseSchema):
        inherited: dict = {}

    class ChildSchema(ParentSchema):
        own: dict = {}

    ParentSchema.__module__ = "dashai_plugins.pa.m"
    ChildSchema.__module__ = "dashai_plugins.pb.m"

    def field():
        return {"parent": "BaseSub", "placeholder": {"component": "Sub"}}

    child = _plugin_class(
        "b",
        "Comp",
        BaseConfigComponent1,
        SCHEMA=ChildSchema,
        get_schema=classmethod(
            lambda cls: {"properties": {"inherited": field(), "own": field()}}
        ),
    )
    registry = ComponentRegistry(initial_components=[child])

    properties = registry["b:Comp"]["schema"]["properties"]
    assert properties["inherited"]["parent"] == "a:BaseSub"
    assert properties["inherited"]["placeholder"]["component"] == "a:Sub"
    assert properties["own"]["parent"] == "b:BaseSub"
    assert properties["own"]["placeholder"]["component"] == "b:Sub"
