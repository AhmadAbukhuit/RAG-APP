from functools import wraps
from fastapi import HTTPException, status
from typing import List, Union, Dict, Any

from shared.context import jwt_claims_ctx

RoleExpression = Union[str, Dict[str, Any]] 

def require_roles(expression: RoleExpression):
    """
    Decorator to enforce complex role-based access control using structured expressions.

    Examples:
        require_roles("admin")  # single role
        require_roles({"and": ["manager", "admin"]})
        require_roles({"or": ["sadmin", {"and": ["manager", "admin"]}]})
    """
    def evaluate(expr: RoleExpression, user_roles: List[str]) -> bool:
        if isinstance(expr, str):
            return expr in user_roles
        elif isinstance(expr, dict):
            if "and" in expr:
                return all(evaluate(sub_expr, user_roles) for sub_expr in expr["and"])
            elif "or" in expr:
                return any(evaluate(sub_expr, user_roles) for sub_expr in expr["or"])
            else:
                raise ValueError("Invalid logical operator in role expression")
        else:
            raise ValueError("Invalid role expression format")

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            claims = jwt_claims_ctx.get()
            if not claims or "roles" not in claims:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="No roles found in token")
            user_roles = claims.get("roles", [])

            if not evaluate(expression, user_roles):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="Insufficient permissions")

            return await func(*args, **kwargs)
        return wrapper
    return decorator