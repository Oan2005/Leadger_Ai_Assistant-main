from fastapi import HTTPException
from app.database.db_connection import connect_to_database
from pydantic import BaseModel,EmailStr
from app.supabase_client_package .supabase_connection import Supabase_admin
class users(BaseModel):
    company_id: str
    full_name:str
    email:EmailStr
    phone:str
    role:str


def get_users_by_company_id(company_id):
    try:
        with connect_to_database() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE company_id = %s;
                    """
                ,(company_id,))
                users = cur.fetchall()
                if users is None:
                    return False
                return {"success":True,"users":users}
    except Exception as e:
        raise e

def get_user_by_id(user_id):
    try:
        with connect_to_database() as con:
            with con.cursor() as cur:

                cur.execute(
                    """
                    SELECT
                        user_id,
                        company_id,
                        full_name,
                        email,
                        role,
                        phone
                    FROM users
                    WHERE user_id = %s;
                    """,
                    (user_id,)
                )

                user = cur.fetchone()

                if not user:
                    return None

                columns = [
                    "user_id",
                    "company_id",
                    "full_name",
                    "email",
                    "role",
                    "phone"
                ]

                return dict(zip(columns, user))

    except Exception:
        logger.exception("Failed to retrieve user")
        raise

def employee_update(
    user_id: str,
    company_id: str,
    full_name: str | None = None,
    phone: str | None = None
):
    try:
        with connect_to_database() as con:
            with con.cursor() as cur:

                fields = []
                values = []

                if full_name is not None:
                    fields.append("full_name = %s")
                    values.append(full_name)

                if phone is not None:
                    fields.append("phone = %s")
                    values.append(phone)

                if not fields:
                    return {
                        "success": False,
                        "error": "No fields to update"
                    }

                values.extend([user_id, company_id])

                query = f"""
                    UPDATE users
                    SET {", ".join(fields)}
                    WHERE user_id = %s
                    AND company_id = %s;
                """

                cur.execute(query, values)

                if cur.rowcount == 0:
                    return {
                        "success": False,
                        "error": "User not found"
                    }

                con.commit()

                return {"success": True}

    except Exception:
        logger.exception("Failed to update employee profile")
        return {
            "success": False,
            "error": "Unable to update employee profile."
        }


def admin_update_employee(
    user_id: str,
    company_id: str,
    full_name: str | None = None,
    phone: str | None = None,
    role: str | None = None
):
    try:
        with connect_to_database() as con:
            with con.cursor() as cur:

                fields = []
                values = []

                if full_name is not None:
                    fields.append("full_name = %s")
                    values.append(full_name)

                if phone is not None:
                    fields.append("phone = %s")
                    values.append(phone)

                if role is not None:
                    fields.append("role = %s")
                    values.append(role)

                if not fields:
                    return {
                        "success": False,
                        "error": "No fields to update"
                    }

                values.extend([user_id, company_id])

                query = f"""
                    UPDATE users
                    SET {", ".join(fields)}
                    WHERE user_id = %s
                    AND company_id = %s
                    Returning *;
                """

                cur.execute(query, values)

                if cur.rowcount == 0:
                    return {
                        "success": False,
                        "error": "Employee not found"
                    }

                con.commit()

                return {"success": True}

    except Exception:
        logger.exception("Failed to update employee")
        return {
            "success": False,
            "error": "Unable to update employee."
        }

def create_invited_user(
    user_id: str,
    company_id: str,
    full_name: str,
    email: str,
    role: str,
    phone: str
):
    try:
        with connect_to_database() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (
                        user_id,
                        company_id,
                        full_name,
                        email,
                        role,
                        phone
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING user_id;
                    """,
                    (
                        user_id,
                        company_id,
                        full_name,
                        email,
                        role,
                        phone
                    )
                )

                record = cur.fetchone()

                if record is None:
                    return False

                con.commit()

                return True

    except Exception:
        logger.exception("Failed to create invited user")
        return False
def create_user(data:users):
    try:
        with connect_to_database() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (company_id,full_name,phone,email,role)
                    VALUES (%s,%s,%s,%s,%s)
                    RETURNING user_id;
                    """
                    , (data.company_id, data.full_name, data.email,data.phone, data.role,))
                user = cur.fetchone()
                if user is None:
                    return False
                con.commit()
                return {
                    "sucess": True,"user_created as id":user.user_id,
                }
    except Exception:
        logger.exception("Failed to create user")
        return {"sucess": False, "error type": "Unable to create user."}

#Later
def delete_user_by_id(user_id: str, company_id: str):
    try:
        user_information = get_user_by_id(user_id)
        if (
            user_information is None
            or user_information["company_id"] != company_id
        ):
            return {
                "success": False,
                "error": "User not found"
            }

        email = user_information["email"]
        response = Supabase_admin.auth.admin.delete_user(user_id)

        Supabase_admin.table("invitations") \
        .delete() \
        .eq("email",email)\
        .eq("company_id",company_id)\
        .execute()

        return {
            "success": True,
            "message": "User deleted successfully",
            "user_id": user_id
        }

    except Exception:
        logger.exception("Failed to delete user")
        return {
            "success": False,
            "error": "Unable to delete user."
        }


def change_role(user_id: str, company_id: str, role: str):
    try:
        with connect_to_database() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET role = %s
                    WHERE user_id = %s
                    AND company_id = %s;
                    """,
                    (role, user_id, company_id)
                )

                if cur.rowcount == 0:
                    con.rollback()
                    return False

                con.commit()
                return True

    except Exception:
        logger.exception("Failed to change user role")
        raise HTTPException(
            status_code=500,
            detail="Unable to update user role."
        )

def check_user_exists(user_id: str, company_id: str | None = None):
    """
    this function turn is to check weather the passed user id exists in the company record or not

    Args:
        user_id:

    Returns:
        True -> in case the user exists
        False - in case the user does not exist
    Raises:
        error with status code 500 that describes the error occurred
    """
    try:
        with connect_to_database() as con:
            with con.cursor() as cur:
                if company_id is None:
                    cur.execute(
                        """
                        SELECT user_id
                        FROM users
                        WHERE user_id = %s;
                        """,
                        (user_id,)
                    )
                else:
                    cur.execute(
                        """
                        SELECT user_id
                        FROM users
                        WHERE user_id = %s
                        AND company_id = %s;
                        """,
                        (user_id, company_id)
                    )
                response = cur.fetchone()
                if response is None:
                    return False
                return True
    except Exception as e:
        logger.exception("Failed to check user existence")
        raise HTTPException(
            status_code=500,
            detail="Unable to check user existence."
        )

if __name__ == '__main__':
    check_user_exists("3800bca6-3868-42e2-a024-2e2dfb9186b7")
