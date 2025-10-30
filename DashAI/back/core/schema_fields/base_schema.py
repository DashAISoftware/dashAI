from pydantic import BaseModel


def replace_defs_in_schema(schema: dict):
    if "$defs" in schema:
        for prop in schema["properties"]:
            if "$ref" in schema["properties"][prop]:
                _, _, def_name = schema["properties"][prop]["$ref"].split("/")
                schema["properties"][prop] = schema["$defs"][def_name]
                schema["properties"][prop]["title"] = prop.title().replace("_", " ")
        schema.pop("$defs")
    return schema


class BaseSchema(BaseModel):
    pass

    """ @classmethod
    def model_validate(cls, raw_data: dict):
        schema_fields = cls.model_fields
        for field_name, field in schema_fields.items():
            if field_name not in raw_data:
                continue
            if field.annotation._name == 'Optional':
                if raw_data[field_name] == "":
                    raw_data[field_name] = None

        return super().model_validate(raw_data) """
