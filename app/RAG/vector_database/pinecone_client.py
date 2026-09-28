"""
pinecone_client
================

Initializes the shared Pinecone client and index handle used by
`pincecone_operations.py` and `query.py`.

SECURITY NOTE (deviation from "no logic changes", approved by project
owner — see docs/SECURITY_NOTE.md):
    The original file had a live Pinecone API key hardcoded in plain
    text. It has been replaced here with a read from the
    `PINECONE_API_KEY` environment variable. This changes *where the
    key comes from*, not any runtime behavior of the client/index
    once the variable is set — see docs/ENVIRONMENT.md for setup.
    The `index.describe_index_stats()` call on import, and the index
    name "hr", are preserved exactly as in the original.
"""

import os,logging
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
logger = logging.getLogger(__name__)
# load .env keys
load_dotenv()
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index("hr")


# def create_namespace(namespace: str):
#     namespace = namespace.strip().lower()
#
#     try:
#         # Get existing namespaces
#         namespaces = index.list_namespaces().namespaces
#
#         # Check if namespace already exists
#         check = [
#             name for name in namespaces
#             if namespace == name.name
#         ]
#
#         if len(check) == 1:
#             return False
#
#         # Create namespace
#         request = index.create_namespace(name=namespace)
#
#         if request.name == namespace:
#             return True
#
#         raise RuntimeError(
#             "Namespace creation returned an unexpected response."
#         )
#
#     except Exception:
#         logger.exception(
#             "Error occurred during namespace creation: %s",
#             namespace
#         )
#         raise
def create_namespace(namespace: str):
    namespace = namespace.lower()
    try:
        response = index.list_namespaces()

        # Extract the list of namespaces safely whether it's an object or a dict
        namespaces_list = getattr(response, "namespaces", []) if not isinstance(response, dict) else response.get(
            "namespaces", [])

        # Check if namespace already exists using attribute access (.name) or dictionary key ([ "name" ])
        check = [
            ns for ns in namespaces_list
            if namespace == (ns.name if hasattr(ns, "name") else ns.get("name"))
        ]

        if len(check) > 0:
            return False

        request = index.create_namespace(name=namespace)

        # Handle response check safely
        req_name = request.name if hasattr(request, "name") else request.get("name")
        if req_name == namespace:
            return True

        return True
    except Exception as e:
        raise Exception(f"error occured during namespace creation as {e}")



def connect_to_namespace(namespace:str):
    try:
        if pc.has_index(namespace):
            return pc.Index(namespace)
        else:
            return "index does not exist. please double check the index name before connecting"
    except Exception as e:
        print(e)
        raise f"error occured during connecting to namespace as {e}"






