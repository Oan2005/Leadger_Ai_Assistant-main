import uuid

from app.database.db_connection import connect_to_database

from app.database.db_connection import connect_to_database

def create_conversation(
    company_id,
    session_id,
    user_id,
    question,
    answer,
    response_time_ms,
    confidence,
    prompt_tokens,
    completion_tokens,
    cached
):
    try:
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conversations (
                        company_id,
                        session_id,
                        user_id,
                        question,
                        answer,
                        response_time_ms,
                        confidence,
                        prompt_tokens,
                        completion_tokens,
                        cached
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
                    RETURNING conversation_id;
                    """,
                    (
                        company_id,
                        session_id,
                        user_id,
                        question,
                        answer,
                        response_time_ms,
                        confidence,
                        prompt_tokens,
                        completion_tokens,
                        cached,
                    )
                )
                conversation_id = cur.fetchone()[0]
                if conversation_id is None:
                    return False
                conn.commit()

                return {"success": True, "conversation_id": conversation_id}

    except Exception as e:
        print(e)
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    seasson_id = uuid.uuid4()
    request = create_conversation(
        company_id="ca1550f0-c096-46eb-a174-88a7e6c8ae61",
        session_id=str(seasson_id),
        question="purpose and scope",
        answer="The leave policy document sets out the categories of leave available to SkyJet Logistics Ltd. employees, including entitlement calculations, approval workflows, and required documentation. It applies to all full-time and part-time employees across all branches and should be read alongside the employee handbook (document ID sjl-hr-001). Temporary and seasonal staff are entitled to statutory leave only (as described in section 9), while contractors and consultants engaged through procurement are not covered by this policy — their leave, if any, is governed by their individual service agreement.",
        response_time_ms=10,
        confidence=1.0,
        prompt_tokens=55,
        completion_tokens=122,
        cached=False
    )
    print(request)










