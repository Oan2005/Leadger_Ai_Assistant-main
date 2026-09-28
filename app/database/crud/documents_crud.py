from fastapi import HTTPException
from pydantic import BaseModel
from app.database.db_connection import connect_to_database
class documents(BaseModel):
    document_id:str
    company_id: str
    uploaded_by:str
    filename:str
    version:int
    status:str
    pinecone_namespace:str
    total_chunks:int

def create_documents(data: documents):
    try:
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (
                        document_id,
                        company_id,
                        uploaded_by,
                        filename,
                        version,
                        status,
                        pinecone_namespace,
                        total_chunks
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (
                        data.document_id,
                        data.company_id,
                        data.uploaded_by,
                        data.filename,
                        data.version,
                        data.status,
                        data.pinecone_namespace,
                        data.total_chunks,
                    )
                )

                record = cur.fetchone()
                if record is None:
                    return False
                conn.commit()

                return {
                    "success": True,
                    "message": record
                }

    except Exception as e:
        raise e

def delete_documents_from_database(document_id,company_id):
    try:
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE documents
                set 
                 status = 'deleted',
                 deleted_at = NOW()
                WHERE document_id = %s AND company_id = %s;
                    """
                ,(document_id,company_id))
                if cur.rowcount == 0:
                    return False
                conn.commit()
                return {"success": True,"message":f"the document {document_id} has been deleted from the pinecone database"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(400,str(e))

def get_documents(company_id:str):
    try:
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                SELECT * FROM documents
                WHERE company_id = %s AND status !='deleted';
                """,(company_id,))
                if cur.rowcount == 0:
                    return False
                record = cur.fetchall()
                return {"success": True, "record": record}
    except Exception as e:
        raise HTTPException(400,str(e))

def archive_documents_from_database(document_id:str, company_id:str):
    try:
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE documents
                    SET status = 'archived'
                    WHERE document_id = %s
                    AND company_id = %s
                    RETURNING *;
                    """,
                    (document_id, company_id)
                )
                record = cur.fetchone()
                if record is None:
                    return False
                conn.commit()
                return {"success": True,"message":"document archived successfully from pinecone database"}

    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"Error archiving document: {e}"}


def unrchive_documents_from_database(document_id:str, company_id:str):
    try:
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE documents
                    SET status = 'ready'
                    WHERE document_id = %s
                    AND company_id = %s;
                    """,
                    (document_id, company_id)
                )

                conn.commit()

                return {"success": True}

    except Exception as e:
        return {"success": False, "message": f"Error unarchiving document: {e}"}

