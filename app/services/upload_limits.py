import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

try:
    MAX_UPLOAD_SIZE_MB = float(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
except ValueError:
    MAX_UPLOAD_SIZE_MB = 25.0

if MAX_UPLOAD_SIZE_MB <= 0:
    MAX_UPLOAD_SIZE_MB = 25.0

MAX_UPLOAD_SIZE_BYTES = int(MAX_UPLOAD_SIZE_MB * 1024 * 1024)
UPLOAD_CHUNK_SIZE = 1024 * 1024


async def save_upload_with_limit(upload_file, destination: str) -> int:
    total_bytes = 0

    with open(Path(destination), "wb") as output:
        while True:
            chunk = await upload_file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break

            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="The uploaded file exceeds the maximum allowed size."
                )
            output.write(chunk)

    return total_bytes
