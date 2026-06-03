from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk import Runner, Workflow
from google.genai import types

from src.agent.config import get_session_service
from src.agent.utils_functions import error_response

class ADKAgentRunner:
    """
    Small wrapper around ADK Runner for isolated agent execution.
    """

    def __init__(self, agent: Agent | Workflow, app_name: str, user_id: str, session_id: str):
        self.agent = agent
        self.app_name = app_name
        self.user_id = user_id
        self.session_id = session_id

        try:
            self.session_service = get_session_service()
        except Exception as e:
            return error_response(code="500", msg="Failed to start session. Please try Again.")

        self.runner = Runner(
            agent=self.agent, # type: ignore
            app_name=self.app_name,
            session_service=self.session_service,
            auto_create_session=True
        )

    def run(self, prompt: str) -> str:
        """
        Runs an agent synchronously and returns final response text.
        """

        content = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )

        final_response = ""

        events = self.runner.run(
            user_id=self.user_id,
            session_id=self.session_id,
            new_message=content
        )

        for event in events:
            if event.output:
                final_response = event.output

        return final_response.strip()
