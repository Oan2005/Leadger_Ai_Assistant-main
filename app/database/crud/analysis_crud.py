from app.database.db_connection import connect_to_database
def get_active_users(company_id:str):
    try:
        with connect_to_database() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT user_id)
                    FROM conversations
                    WHERE conversations.company_id = %s;
                    """
                ,(company_id,))
                result = cur.fetchone()

                if result is None:
                    return 0

                return result[0]
    except Exception as e:
        print(e)
def get_total_questions(company_id:str):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(conversation_id)
                FROM conversations
                WHERE conversations.company_id = %s;
                """
            ,(company_id,))
            return cur.fetchone()[0]
def get_avg_confidence(company_id:str):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT AVG(confidence)
                FROM conversations
                where company_id = %s;
                """
            ,(company_id,))
            return cur.fetchone()[0]
def get_avg_response_time(company_id:str):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT AVG(response_time_ms)
                FROM conversations
                WHERE company_id = %s;
                """
            ,(company_id,))
            return round(cur.fetchone()[0],2)
def get_unresolved_questions(company_id:str):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM conversation_analysis ca
                JOIN conversations c
                ON ca.conversation_id = c.conversation_id
                WHERE c.company_id = %s
                AND ca.resolved = FALSE;
                """
            ,(company_id,))
            return cur.fetchone()[0]
def get_hr_reviews(company_id:str):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM conversation_analysis ca
                JOIN conversations c
                ON ca.conversation_id = c.conversation_id
                WHERE c.company_id = %s
                AND ca.needs_hr_review = TRUE;
                """
            ,(company_id,))
            return cur.fetchone()[0]
def get_sentiment_distribution(company_id:str):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT ca.sentiment, COUNT(*)
                FROM conversation_analysis ca
                JOIN conversations c
                ON ca.conversation_id = c.conversation_id
                WHERE c.company_id = %s
                GROUP BY ca.sentiment;
                """
            ,(company_id,))
            return [
                {"sentiment": sentiment, "count": count}
                for sentiment, count in cur.fetchall()
            ]
def get_topics(company_id: str):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT ca.topic, COUNT(*)
                FROM conversation_analysis ca
                JOIN conversations c
                    ON ca.conversation_id = c.conversation_id
                WHERE c.company_id = %s
                GROUP BY ca.topic;
                """,
                (company_id,)
            )

            return [
                {"topic": topic, "count": count}
                for topic, count in cur.fetchall()
            ]
def get_questions_overtime(company_id: str):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT
                DATE(created_at) AS date,
                COUNT(*) AS question_count
                FROM conversations
                WHERE company_id = %s
                GROUP BY DATE(created_at)
                ORDER BY date;
                """,
                (company_id,)
            )

            return [{"date": date, "questions": questions} for date,questions in cur.fetchall()]


# Should be call from the HR employee
def get_company_analytics(company_id: str):

    return {
        "overview": {
            "active_users": get_active_users(company_id),
            "total_questions": get_total_questions(company_id),
            "avg_confidence": get_avg_confidence(company_id),
            "avg_response_time_ms": get_avg_response_time(company_id),
            "unresolved_questions": get_unresolved_questions(company_id),
            "hr_reviews": get_hr_reviews(company_id)
        },

        "sentiment_distribution": get_sentiment_distribution(company_id),

        "topics": get_topics(company_id),

        "questions_over_time": get_questions_overtime(company_id)
    }

