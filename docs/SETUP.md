# Setup Instructions

## Prerequisites

- Python 3.12 (per `Dockerfile`)
- A Pinecone account with an index named `"hr"` already created
- Network access to the n8n webhook endpoints used in
  `app/vector_database/llm_response/LLM.py`

## Local setup

```bash
# 1. Create and activate a virtual environment (recommended)
python3.12 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requierments.txt   # filename kept as in original project

# 3. Configure environment variables
cp .env.example .env
# edit .env and set PINECONE_API_KEY

# 4. Run the API
uvicorn api:app --reload
```

The API will be available at `http://127.0.0.1:8000`. Interactive docs at
`http://127.0.0.1:8000/docs` (FastAPI's built-in Swagger UI).

## Docker

```bash
docker build -t skyjet-knowledge-assistant .
docker run -p 8000:8000 --env-file .env skyjet-knowledge-assistant
```

**Note**: the original `Dockerfile` has a pre-existing typo,
`WORKDIR / app` (with a space, creating a directory literally named
`app` under the filesystem root `/`, rather than `/app`). This is
preserved as-is per the "do not change functionality" requirement — the
container still builds and runs correctly, since `COPY . .` and the
`CMD` are relative to whatever `WORKDIR` resolves to. See
`docs/KNOWN_ISSUES.md`.

## Verifying the setup

```bash
curl "http://127.0.0.1:8000/health"
# {"status":"healthy"}

curl -X POST "http://127.0.0.1:8000/upload" -F "file=@data/SkyJet_Benefits_Guide.docx"

curl "http://127.0.0.1:8000/chat?user_question=hello"
```
