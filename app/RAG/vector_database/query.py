"""
query
=====

Handles similarity search against the Pinecone index for a user
question, and a lightweight greeting-detection helper used by the
`/chat` API endpoint to short-circuit retrieval for simple greetings.
"""
from torch.fx.experimental.unification.dispatch import namespace

from app.RAG.embedding.embedding_model import encoder_model
from app.RAG.vector_database.llm_response.LLM import LLM_response
from app.RAG.vector_database.pinecone_client import index


def pinecone_query(employee_question: str, top_k = 3,employee_namespace = None):
    """
    Embed a user question and retrieve the top-k most similar chunks.

    Args:
        company_namespace (str):The user namespace
        employee_question (str): The user's question text.
        top_k (int): Number of top matches to retrieve (default 3;
            the `/chat` endpoint calls this with `top_k=5`).

    Returns:
        list[dict]: Ranked matches, each with `rank`, `score`, and
        `text` (from the match's metadata).
    """
    # for name in index.list_namespaces():
    #     if name["name"] != employee_namespace:
    #         return "Index is not found in the pinecone"
    query_embedded = encoder_model.encode(employee_question)
    response = index.query(
        vector=query_embedded.tolist(),
        top_k=top_k,
        include_metadata=True,
        namespace = employee_namespace
    )
    if not response.matches:
        raise ValueError("No matches found.")
    docs = []
    for i, match in enumerate(response.matches):
        docs.append({
            "text": match["metadata"]["text"],
            "retrieval_score":match.score,
            "document_id": match["metadata"]["document_id"],
            "chunk_index":match["metadata"]["chunk_index"],
        })
    return docs



if __name__ == '__main__':
    query_test = pinecone_query("purpose and scope ",employee_namespace="supplycmd")
    print(query_test)
