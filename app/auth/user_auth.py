from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.supabase_client_package.supabase_connection import Supabase_client
from app.services.main_logics import get_user_role
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    access_token = credentials.credentials

    try:
        response = Supabase_client.auth.get_user(access_token)

        if not response.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication"
            )

        return response.user

    except HTTPException:
        raise

    except Exception as e:
        print("Auth error:", e)

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

def require_admin(current_user=Depends(get_current_user)):
    role = get_user_role(current_user.id)

    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to perform this operation"
        )

    return current_user

def require_hr(current_user=Depends(get_current_user)):
    role = get_user_role(current_user.id)
    if role != "hr":
        raise HTTPException(status_code=403, detail="You are not allowed to perform this operation")
    return current_user

def require_hr_admin(current_user=Depends(get_current_user)):
    role = get_user_role(current_user.id)

    if role != "hr" and role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to perform this operation"
        )

    return current_user
