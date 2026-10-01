from app.database.db_connection import connect_to_database
from pydantic import BaseModel
class conversation_analysis(BaseModel):
    conversation_id: str
    topic:str
    department:str
    sentiment:str
    resolved:bool
    needs_hr_review:bool
    missing_document:bool

def insert_conversation_analysis(data: conversation_analysis):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversation_analysis (
                    conversation_id,
                    topic,
                    department,
                    sentiment,
                    resolved,
                    needs_hr_review,
                    missing_document
                )
                VALUES (%s,%s, %s, %s, %s, %s, %s)
                RETURNING *;
                """,
                (
                    data.conversation_id,
                    data.topic,
                    data.department,
                    data.sentiment,
                    data.resolved,
                    data.needs_hr_review,
                    data.missing_document
                )
            )

            response = cur.fetchone()
            con.commit()
            if response is None:
                return False
            return response


def get_conversation_analysis(conversation_id):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT question,answer,confidence
                FROM conversations
                WHERE conversation_id=%s;
                """
            ,(conversation_id,))
            response = cur.fetchall()
            con.commit()
            if response is None:
                return False
            return response

    get_conversation_analysis(conversation_id="495759fd-b004-47ad-aad6-e0abd78b240d")