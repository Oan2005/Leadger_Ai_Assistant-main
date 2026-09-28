from fastapi import HTTPException

from pydantic import BaseModel,EmailStr
from app.database.db_connection import connect_to_database



def create_invitation(email, company_id, role, token_hash, admin_id,phone):
    try:
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO invitations (
                        email,
                        company_id,
                        role,
                        token_hash,
                        created_by,
                        expires_at,
                        phone
                    )
                    VALUES (%s, %s, %s, %s, %s, NOW() + INTERVAL '24 hours',%s)
                    RETURNING id;
                """, (
                    email,
                    company_id,
                    role,
                    token_hash,
                    admin_id,
                    phone
                ))

                invitation_id = cur.fetchone()[0]
                if invitation_id is None:
                    return None
            conn.commit()
            return invitation_id
    except Exception as e:
        conn.rollback()
        print(e)
        raise HTTPException(e)
def get_invitation(token_hash):
    try:
        columns = ["id","email","company_id","role","token_hash","created_by","phone","created_at","accepted_at","expires_at"]
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT  id,email,company_id,role,token_hash,created_by,phone,created_at,accepted_at,expires_at
                    FROM invitations
                    WHERE token_hash = %s;
                """, (token_hash,))
                record = cur.fetchone()
                if record is None:
                    return None
                return dict(zip(columns, record))

    except Exception as e:
        print(e)
        raise HTTPException(e)
def delete_invitation(invitation_id):
    try:
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM invitations
                    WHERE id = %s;
                """, (invitation_id,))

            if cur.rowcount == 0:
                return False
            conn.commit()
            return True
    except Exception as e:
        print(e)
        raise HTTPException(e)
    finally:
        conn.close()
def check_invitation_accepted(email: str):
    with connect_to_database() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT accepted_at
                FROM invitations
                WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                (email,)
            )

            response = cur.fetchone()

            # Email doesn't exist
            if response is None:
                return None

            # Email exists and invitation was accepted
            if response[0] is not None:
                return True

            # Email exists but invitation was NOT accepted
            return False
def mark_as_accepted(token_hash:str):
    try:
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE invitations
                    SET accepted_at = NOW()
                    WHERE token_hash = %s
                    RETURNING *;
                    """
                ,(token_hash,))
                response = cur.fetchone()
                columns = ["id","email","company_id","role","token_hash","created_by","phone","created_at","accepted_at","expires_at"]
                if response is None:
                    return False
                return dict(zip(columns, response))
    except Exception as e:
        raise
if __name__ == '__main__':
    print(get_invitation('e76b069168f4e764b9a23ad82ffd679637695352e8860041c6e1d14dc6c7a45e'))