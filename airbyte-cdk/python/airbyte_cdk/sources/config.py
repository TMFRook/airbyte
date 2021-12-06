#
# Copyright (c) 2021 Airbyte, Inc., all rights reserved.
#

from typing import MutableMapping, List, Dict, Any, Optional

from pydantic import BaseModel
from jsonschema import RefResolver


class BaseConfig(BaseModel):
    """ Base class for connector spec
    """

    @classmethod
    def _rename_key(cls, schema: Any, old_key: str, new_key: str) -> None:
        """ Iterate over nested dictionary and replace one key with another. Used to replace anyOf with oneOf."

        :param schema: schema that will be patched
        :param old_key: name of the key to replace
        :param new_key: new name of the key
        """
        if not isinstance(schema, MutableMapping):
            return

        for key, value in schema.items():
            cls._rename_key(value, old_key, new_key)
            if old_key in schema:
                schema[new_key] = schema.pop(old_key)

    @classmethod
    def _expand_refs(cls, schema: Any, ref_resolver: Optional[RefResolver] = None) -> None:
        """ Iterate over schema and replace all occurrences of $ref with their definitions

        :param schema:
        :param ref_resolver:
        """
        ref_resolver = ref_resolver or RefResolver.from_schema(schema)

        if isinstance(schema, MutableMapping):
            if "$ref" in schema:
                ref_url = schema.pop("$ref")
                _, definition = ref_resolver.resolve(ref_url)
                cls._expand_refs(definition, ref_resolver=ref_resolver)  # expand refs in definitions as well
                schema.update(definition)
            else:
                for key, value in schema.items():
                    cls._expand_refs(value, ref_resolver=ref_resolver)
        elif isinstance(schema, List):
            for value in schema:
                cls._expand_refs(value, ref_resolver=ref_resolver)

    @classmethod
    def schema(cls, **kwargs) -> Dict[str, Any]:
        """We're overriding the schema classmethod to enable some post-processing
        """
        schema = super().schema(**kwargs)
        cls._rename_key(schema, old_key="anyOf", new_key="oneOf")  # UI supports only oneOf
        cls._expand_refs(schema)  # UI and destination doesn't support $ref's
        schema.pop("definitions", None)
        return schema
