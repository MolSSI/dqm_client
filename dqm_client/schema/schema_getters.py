"""
Assists in grabbing the requisite schema
"""

import copy
import glob
import os
import jsonschema

from .definitions_schema import get_definition
from .molecule_schema import molecule_schema

__all__ = ["get_schema", "validate"]

_schemas = {}

# Add in molecule
for req in molecule_schema["requied_definitions"]:
    molecule_schema["definitions"][req] = get_definition(req)
_schemas["molecule"] = molecule_schema

# Load molecule schema


def get_schema(name):
    if name not in _schemas:
        raise KeyError("Schema name %s not found." % name)
    return copy.deepcopy(_schemas)


def validate(data, schema_name):
    if schema_name not in _schemas:
        raise KeyError("Schema name %s not found." % name)

    jsonschema.validate(data, _schemas[schema_name])
