import logging
import os

from dotenv import load_dotenv
from google.adk.models import LiteLlm

load_dotenv()
GITHUB_TOKEN:str|None = os.environ.get("GITHUB_TOKEN", None)
GEMINI_API_KEY:str|None = os.environ.get("GEMINI_API_KEY", None)

def get_azure_openai_model(azure_model_name: str) -> LiteLlm:
    if GITHUB_TOKEN is None:
        raise Exception("Ensure that Github PAT Token are added in .env")
    
    return LiteLlm(
        model=azure_model_name,
        api_key= GITHUB_TOKEN, 
        api_base="https://models.inference.ai.azure.com"
    )

def get_gemini_model(gemini_model_name: str) -> str:
    if GEMINI_API_KEY is None:
        raise Exception("Ensure that Gemini API Key are added in .env")

    return gemini_model_name