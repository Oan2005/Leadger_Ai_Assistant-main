from openai import OpenAI
from app.llm_config import OPENROUTER_BASE_URL, get_openrouter_api_key

client = OpenAI(
  base_url=OPENROUTER_BASE_URL,
  api_key=get_openrouter_api_key(),
)
