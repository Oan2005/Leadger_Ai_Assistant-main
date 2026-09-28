from app.database.db_connection import connect_to_database
from app.database.crud.analysis_crud import get_company_analytics
from app.database.crud.analysis_crud import *




def get_questions_last_7_days(company_id: str):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    DATE(created_at) AS date,
                    COUNT(*) AS count
                FROM conversations
                WHERE company_id = %s
                  AND created_at >= NOW() - INTERVAL '18 days'
                  AND created_at <= NOW()
                GROUP BY DATE(created_at)
                ORDER BY date;
                """,
                (company_id,)
            )

            rows = cur.fetchall()

            return [
                {
                    "date": row[0].isoformat(),
                    "count": row[1]
                }
                for row in rows
            ]
def get_recent_activities(company_id: str):
    with connect_to_database() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.conversation_id,
                    u.full_name,
                    ca.topic,
                    c.created_at
                FROM conversations c
                JOIN conversation_analysis ca
                    ON c.conversation_id = ca.conversation_id
                JOIN users u
                    ON c.user_id = u.user_id
                WHERE c.company_id = %s
                ORDER BY c.created_at DESC
                LIMIT 10;
                """,
                (company_id,)
            )

            return [
                {
                    "conversation_id": conversation_id,
                    "employee": full_name,
                    "topic": topic,
                    "created_at": created_at
                }
                for conversation_id, full_name, topic, created_at in cur.fetchall()
            ]

def get_dashboard_data(company_id: str):
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

        "questions_over_time": get_questions_overtime(company_id),

        "recent_activities": get_recent_activities(company_id)
    }





