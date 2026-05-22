from typing import Any, Dict

import polars as pl
import yaml

TYPE_MAP = {
    "int": pl.Int64,
    "float": pl.Float64,
    "str": pl.Utf8,
    "bool": pl.Boolean,
}


def load_schema(schema_path: str) -> Dict[str, Dict[str, Any]]:
    """Reads a yaml file and returns a dictionary of column configurations."""
    with open(schema_path, "r") as f:
        config = yaml.safe_load(f)

    schema_dict = {}
    fields = config.get("fields", {})

    for field_name, rules in fields.items():
        if isinstance(rules, str):
            rules = {"type": rules}

        type_str = rules.get("type")
        if type_str not in TYPE_MAP:
            raise ValueError(f"Unsupported type '{type_str}' for field '{field_name}'")

        rules["type"] = TYPE_MAP[type_str]
        schema_dict[field_name] = rules

    return schema_dict
