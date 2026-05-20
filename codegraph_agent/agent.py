import os

from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.genai import types
from google.adk.models.lite_llm import LiteLlm

import codegraph_agent.instructions.instruction_dump as instructions
from codegraph_agent.tools.fetch_context import fetch_codebase_and_relationship_context

load_dotenv()

llm_model = LiteLlm(
    model="openai/gpt-4o-mini",
    api_key=os.getenv("GITHUB_TOKEN"),
    api_base="https://models.inference.ai.azure.com"
)

root_agent = Agent(
    model= llm_model,
    name='codebase_analyzer',
    description='Principal Architectural Analyst that reverse-engineers code logic and interpret structural dependencies.',
    instruction=instructions.codebase_analyzer_instruction,
    tools=[fetch_codebase_and_relationship_context],
    generate_content_config=types.GenerateContentConfig(temperature=0.4)
)
