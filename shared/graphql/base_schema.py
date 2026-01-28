# gateway/app/graphql/base_schema.py
import strawberry
from typing import Any

@strawberry.type
class Query:
    pass

@strawberry.type
class Mutation:
    pass

# Helper to merge multiple Query or Mutation classes
def merge_types(*types: Any) -> Any:
    """
    Dynamically merges multiple Strawberry Query or Mutation classes.
    """
    fields = {}
    for t in types:
        for k, v in t.__dict__.items():
            if not k.startswith("__") and callable(v):
                fields[k] = v
    return type("Merged", (object,), fields)