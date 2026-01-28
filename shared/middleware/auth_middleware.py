from fastapi import Request
from shared.http.http_exceptions import HttpUnauthorizedError
from typing import List, Optional
import jwt, os

# Import your context variables
from shared.context import auth_token_ctx, refresh_token_ctx, jwt_claims_ctx

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-default-secret")
JWT_ALGORITHM = "HS256"

def global_auth_middleware(exclude_paths: Optional[List[str]] = None):
    exclude_paths = exclude_paths or []

    async def auth_middleware(request: Request, call_next):
        path = request.url.path

        # Initialize context tokens to None to avoid UnboundLocalError in finally block
        token_ctx_token = None
        refresh_ctx_token = None
        claims_ctx_token = None

        try:
            # 1. Extract Token
            cookie_name = os.getenv("JWT_COOKIE_NAME", "jwt_token")
            auth_token = request.cookies.get(cookie_name)

            if not auth_token:
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    auth_token = auth_header[len("Bearer "):].strip()

            refresh_token = request.cookies.get("refresh-token")

            # 2. Store Raw Tokens in Context
            if auth_token:
                token_ctx_token = auth_token_ctx.set(auth_token)
            
            if refresh_token:
                refresh_ctx_token = refresh_token_ctx.set(refresh_token)

            # 3. Check Exclusions
            is_excluded = "*" in exclude_paths or any(path.startswith(ex) for ex in exclude_paths)

            if is_excluded:
                # Try to decode loosely for public paths (e.g., "My Profile" on homepage)
                if auth_token:
                    try:
                        payload = jwt.decode(auth_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                        # Capture the token so we can reset it later!
                        claims_ctx_token = jwt_claims_ctx.set(payload)
                    except:
                        pass # Ignore errors on public paths
                
                response = await call_next(request)
                return response

            # 4. Strict Validation (Non-Excluded Paths)
            if not auth_token:
                raise HttpUnauthorizedError("Missing auth token")

            try:
                payload = jwt.decode(auth_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                # Capture the token here too
                claims_ctx_token = jwt_claims_ctx.set(payload)
                
            except jwt.ExpiredSignatureError:
                raise HttpUnauthorizedError("Token expired")
            except jwt.InvalidTokenError:
                raise HttpUnauthorizedError("Invalid token")

            # 5. Validate Refresh Token (Optional)
            if refresh_token:
                try:
                    jwt.decode(refresh_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                except jwt.ExpiredSignatureError:
                    raise HttpUnauthorizedError("Refresh token expired")
                except jwt.InvalidTokenError:
                    raise HttpUnauthorizedError("Invalid refresh token")

            # 6. Process Request
            response = await call_next(request)
            return response

        finally:
            # 7. Context Cleanup (SAFE VERSION)
            if token_ctx_token: 
                auth_token_ctx.reset(token_ctx_token)
            if refresh_ctx_token: 
                refresh_token_ctx.reset(refresh_ctx_token)
            if claims_ctx_token: 
                jwt_claims_ctx.reset(claims_ctx_token)
            
    return auth_middleware