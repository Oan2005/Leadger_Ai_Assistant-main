"""
insertion
=========

Upserts embedded chunks into the Pinecone index, using the shared
`index` handle from `pinecone_client`.
"""

from app.RAG.vector_database.pinecone_client import connect_to_namespace,index
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


def status_documents(document_id: str, namespace_name: str):
    try:
        # Validate input
        if not document_id:
            raise HTTPException(
                status_code=400,
                detail="Document ID is required."
            )

        if not namespace_name:
            raise HTTPException(
                status_code=400,
                detail="Namespace name is required."
            )

        # Fetch document chunk from Pinecone
        try:
            fetched_data = index.fetch_by_metadata(
                filter={
                    "document_id": {"$eq": document_id},
                    "chunk_index": {"$eq": 2},
                },
                namespace=namespace_name
            )

        except Exception:
            logger.exception("Pinecone fetch failed")

            raise HTTPException(
                status_code=503,
                detail="Unable to retrieve document status."
            )

        # Convert vectors to dictionary
        vectors = dict(fetched_data.vectors)

        # Expected vector ID
        vector_id = f"{document_id}-2"

        # Check if the expected chunk exists
        if vector_id not in vectors:
            raise HTTPException(
                status_code=404,
                detail="Document chunk not found."
            )

        # Check metadata exists
        metadata = vectors[vector_id].get("metadata")

        if not metadata:
            raise HTTPException(
                status_code=500,
                detail="Document metadata is missing."
            )

        # Check status exists
        status = metadata.get("status")

        if status is None:
            raise HTTPException(
                status_code=500,
                detail="Document status is missing."
            )

        return status

    except HTTPException:
        # Keep our intentional HTTP errors
        # without converting them into 500
        raise

    except Exception:
        # Unexpected error
        logger.exception("Unexpected document status failure")

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while retrieving document status."
        )
def insert_chunks(embedded_chunks, namespace_name: str):

    namespace_name = namespace_name.lower()

    response = index.upsert(
        vectors=embedded_chunks,
        namespace=namespace_name
    )

    stats = index.describe_index_stats()

    return stats
def delete_chunks(document_id, namespace_name):
    try:
        response = index.delete(
            filter={
                "document_id": {"$eq": document_id}
            },
            namespace=namespace_name
        )

        return {
            "status": "success",
            "document_id": document_id,
            "message": "Document chunks deleted successfully."
        }

    except Exception:
        logger.exception("Pinecone delete failed")
        raise
def archive_chunks(document_id, namespace_name):
    try:
        fetched_data = index.fetch_by_metadata(
            filter={
                "document_id": {"$eq": document_id}
            },
            namespace = namespace_name
        )

        archived_count = 0

        for record_key,values in fetched_data.vectors.items():
            index.update(
                id=record_key,
                set_metadata={
                    "status": "archived"
                },
                namespace = namespace_name
            )

            archived_count += 1

        return {
            "status": "success",
            "document_id": document_id,
            "archived_chunks": archived_count
        }

    except Exception:
        logger.exception("Pinecone archive failed")
        raise
def unarchive_documents(document_id: str, namespace_name: str):
    try:
        # -----------------------------
        # Validate input
        # -----------------------------
        if not document_id:
            raise HTTPException(
                status_code=400,
                detail="Document ID is required."
            )

        if not namespace_name:
            raise HTTPException(
                status_code=400,
                detail="Namespace name is required."
            )

        # -----------------------------
        # Fetch document chunks
        # -----------------------------
        try:
            fetched_data = index.fetch_by_metadata(
                filter={
                    "document_id": {"$eq": document_id}
                },
                namespace=namespace_name
            )

        except Exception:
            logger.exception("Pinecone fetch failed")

            raise HTTPException(
                status_code=503,
                detail="Unable to retrieve document from the vector database."
            )

        # -----------------------------
        # Check document exists
        # -----------------------------
        if not fetched_data.vectors:
            raise HTTPException(
                status_code=404,
                detail="Document not found."
            )

        # -----------------------------
        # Update chunks
        # -----------------------------
        document_count = 0

        try:
            for record_key in fetched_data.vectors.keys():

                index.update(
                    id=record_key,
                    set_metadata={
                        "status": "ready"
                    },
                    namespace=namespace_name
                )

                document_count += 1

        except Exception:
            logger.exception("Pinecone update failed")

            raise HTTPException(
                status_code=503,
                detail="Failed to unarchive document."
            )

        # -----------------------------
        # Success
        # -----------------------------
        return {
            "status": True,
            "message": "Document unarchived successfully.",
            "document_id": document_id,
            "updated_chunks": document_count
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected unarchive failure")

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while unarchiving the document."
        )
# def status_documents(document_id, namespace_name):
#     try:
#         fetched_data = index.fetch_by_metadata(
#             filter={
#                 "document_id": {"$eq": document_id},
#                 "chunk_index":{"$eq":2},
#             },
#             namespace = namespace_name
#         )
#         response = dict(fetched_data.vectors)
#         return response[f"{document_id}-2"]["metadata"]["status"]
#     except Exception as e:
#         raise
