from http.client import HTTPException
from app.database.crud.users_crud import get_user_by_id
from app.supabase_client_package.supabase_connection import Supabase_client, Supabase_admin
from .auth_exceptions import InvalidCredentialsError
from app.supabase_client_package.supabase_connection import Supabase_client
from app.auth.auth_exceptions import InvalidCredentialsError
from supabase_auth.errors import AuthApiError
import logging

logger = logging.getLogger(__name__)
from pydantic import BaseModel,EmailStr
class SignInRequest(BaseModel):
    email:EmailStr
    password:str


def sign_in(data: SignInRequest):
    try:
        response = Supabase_client.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })

        if not response.session or not response.user:
            raise InvalidCredentialsError(
                "Authentication was unsuccessful."
            )

        return {
            "user_id": response.user.id,
            "email": response.user.email,
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }

    except InvalidCredentialsError:
        raise

    except AuthApiError as exc:
        if getattr(exc, "code", None) == "invalid_credentials":
            raise InvalidCredentialsError("Authentication was unsuccessful.") from exc
        raise

    except Exception:
        logger.exception("Sign in workflow failed")
        raise



if __name__ == "__main__":
    # Example usage
    test_data = SignInRequest(email="test-employee-pepsi@gmail.com", password="Hassan1977")
    print(sign_in(test_data))



