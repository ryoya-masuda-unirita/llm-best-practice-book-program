from google import genai
from openai import AsyncOpenAI

from src.config import config

google_genai_client = genai.Client(api_key=config.gemini_api_key)

openai_client = AsyncOpenAI(api_key=config.openai_api_key)
