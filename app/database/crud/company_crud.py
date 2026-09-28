from pydantic import BaseModel,EmailStr
import logging
from app.RAG.vector_database.pinecone_client import index
from app.database.db_connection import connect_to_database

logger = logging.getLogger(__name__)



class Company(BaseModel):
    company_name: str
    namespace: str

def create_app(
    company_data: Company,
    full_name: str,
    email: EmailStr,
    phone: str,
    user_supabase_id: str
):
    con = None

    try:
        con = connect_to_database()

        with con.cursor() as cur:

            # 1. Create company
            cur.execute(
                """
                INSERT INTO companies (
                    company_name,
                    namespace
                )
                VALUES (%s, %s)
                RETURNING company_id;
                """,
                (
                    company_data.company_name,
                    company_data.namespace,
                ),
            )

            company_id = cur.fetchone()[0]

            # 2. Create first admin
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
                RETURNING *;
                """,
                (
                    user_supabase_id,
                    company_id,
                    full_name,
                    email,
                    "admin",
                    phone,
                ),
            )

            user_details = cur.fetchone()

            if user_details is None:
                raise RuntimeError(
                    "User INSERT returned no row."
                )

        # Both inserts succeeded
        con.commit()

        return {
            "company_id": company_id,
            "user_details": user_details,
        }

    except Exception:
        if con is not None:
            try:
                con.rollback()
            except Exception:
                logger.exception(
                    "Database rollback failed in create_app."
                )

        logger.exception("create_app failed.")
        raise

    finally:
        if con is not None:
            con.close()


def create_company(company_name: str, namespace: str):
    try:
        with connect_to_database() as con:
            with con.cursor() as cur:
                cur.execute("""
                    INSERT INTO companies (company_name, namespace)
                    VALUES (%s, %s)
                    RETURNING company_id, company_name, namespace;
                """, (company_name, namespace))

                company = cur.fetchone()
                con.commit()

                if company is None:
                    return False

                return {
                    "success": True,
                    "message": f"Company '{company[1]}' created successfully.",
                    "company": {
                        "company_id": str(company[0]),
                        "company_name": company[1],
                        "namespace": company[2]
                    }
                }

    except Exception as e:
        con.rollback()
        print(e)
        return {
            "success": False,
            "message": "Error creating company",
            "status": str(e)
        }
def check_company_existence(company_id: str):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM companies
                WHERE company_id = %s
                LIMIT 1;
                """,
                (company_id,)
            )

            return cur.fetchone() is not None
def delete_company(company_id: str):
    try:
        # Get company's Pinecone namespace
        if check_company_existence(company_id)!=True:
            return "Company is already deleted"

        company_namespace = get_namespace_by_company_id(company_id)

        if (
            not company_namespace
            or company_namespace is False
        ):
            return {
                "success": False,
                "message": "Company namespace not found."
            }

        namespace = str(
            company_namespace["namespace"]
        ).lower()

        # Delete company's entire namespace from Pinecone
        try:
            index.delete_namespace(namespace)
        except Exception as e:
            print(f"Pinecone namespace deletion error: {e}")

            return {
                "success": False,
                "message": "Unable to delete company vector data."
            }

        # Delete company from PostgreSQL
        try:
            with connect_to_database() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM companies
                        WHERE company_id = %s
                        RETURNING company_id;
                        """,
                        (company_id,)
                    )

                    company = cur.fetchone()

                    if not company:
                        con.rollback()

                        return {
                            "success": False,
                            "message": "Company not found."
                        }

                    con.commit()

        except Exception as e:
            print(f"Database company deletion error: {e}")

            return {
                "success": False,
                "message": (
                    "Company vector data was deleted, "
                    "but the company database record could not be deleted."
                )
            }

        return {
            "success": True,
            "message": f"Company '{company[0]}' deleted successfully.",
            "namespace": "deleted successfully"
        }

    except Exception as e:
        print(f"Unexpected company deletion error: {e}")

        return {
            "success": False,
            "message": "An unexpected error occurred while deleting the company."
        }
def get_company_by_id(company_id: str):
    try:
        with connect_to_database() as con:
            with con.cursor() as cur:
                cur.execute("SELECT * FROM companies WHERE company_id = %s;", (company_id,))
                company = cur.fetchone()
                if company is None:
                    return None
                return {"success": True,"company_name": company[1],"company_id": company[0],"company_namespace": company[3]}
    except Exception as e:
        print(e)
        return {"success":False,"error":e}
    finally:
        con.close()

def get_namespace_by_company_id(company_id:str):
    try:
        with connect_to_database() as con:
            with con.cursor() as cur:
                cur.execute("SELECT namespace FROM companies WHERE company_id = %s;", (company_id,))
                namespace = cur.fetchone()[0]
                con.commit()
                if namespace is None:
                    return False
            return {"success": True, "namespace": namespace}
    except Exception as e:
        print(e)
        return {"success":False,"error":str(e)}

def update_company_name(company_id,company_name):
    try:
        with connect_to_database() as con:
            with con.cursor() as cur:
                cur.execute("UPDATE companies SET company_name = %s WHERE company_id = %s RETURNING *;", (company_name,company_id,))
                company = cur.fetchone()
                con.commit()
                if company is None:
                    return False
                return {"success": True,"company_name": company[1]}
    except Exception as e:
        return str(e)

def get_namespace_index_stats(company_id:str):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute("SELECT namespace FROM companies WHERE company_id = %s;", (company_id,))
            namespace = cur.fetchone()[0]
            if namespace is None:
                return False
            status = index.describe_index_stats()
            used_usage = status["namespaces"][namespace]["vector_count"]
            if used_usage ==0:
                return {
                    "knowleadge_base": {
                        "namespace_name": namespace,
                        "used_vectors": used_usage,
                        "remaining_vectors": 0,
                        "usage_precentage": 0
                    }
                }
            remaining_usage = 10000 - used_usage
            usage_precentage = (used_usage / 10000) * 100
            return {
                "knowleadge_base":{
                    "namespace_name":namespace,
                    "used_vectors":used_usage,
                    "remaining_vectors":remaining_usage,
                    "usage_precentage":f"{usage_precentage}%"
                }
            }

def can_add_to_namespace(company_id:str,vectors_numbers:int):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute("SELECT namespace FROM companies WHERE company_id = %s;", (company_id,))
            namespace = cur.fetchone()[0]
            if namespace is None:
                return "Namespace not found."
            status = index.describe_index_stats()
            used_usage = status["namespaces"][namespace]["vector_count"]
            if used_usage+vectors_numbers >10000:
                return False
            return True

            


