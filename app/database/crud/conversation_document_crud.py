from app.database.db_connection import connect_to_database

def create_documents_from_pinecone(
    conversation_id: str,
    pinecone_documents: list[dict]
):
    with connect_to_database() as con:
        with con.cursor() as cur:

            records = []

            for document in pinecone_documents:
                records.append((
                    conversation_id,
                    document["document_id"],
                    document["chunk_index"],
                    document["retrieval_score"]
                ))

            cur.executemany(
                """
                INSERT INTO conversation_documents
                (conversation_id, document_id, chunk_index, retrieval_score)
                VALUES (%s, %s, %s, %s);
                """,
                records
            )

            return len(records)

