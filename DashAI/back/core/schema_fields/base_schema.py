from pydantic import BaseModel

from DashAI.back.core.utils import MultilingualString


def replace_defs_in_schema(schema: dict):
    # 1. Resolve $defs if present
    if "$defs" in schema:
        for prop, prop_schema in schema["properties"].items():
            if "$ref" in prop_schema:
                _, _, def_name = prop_schema["$ref"].split("/")
                schema["properties"][prop] = schema["$defs"][def_name]
        schema.pop("$defs")

    # 2. Normalize titles for ALL properties
    for prop, prop_schema in schema["properties"].items():
        display_name = prop_schema.pop("display_name", None)

        if isinstance(display_name, MultilingualString):
            prop_schema["title"] = display_name

        if isinstance(display_name, dict):
            # convert dict to MultilingualString
            prop_schema["title"] = MultilingualString(**display_name)

        elif isinstance(prop_schema.get("title"), MultilingualString):
            # already correct
            pass

        else:
            # fallback: derive from property name
            fallback_title = prop.replace("_", " ").title()
            prop_schema["title"] = MultilingualString(en=fallback_title)

    return schema


class BaseSchema(BaseModel):
    pass
