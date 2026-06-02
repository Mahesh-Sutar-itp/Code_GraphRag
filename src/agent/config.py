import logging
import os
from dotenv import load_dotenv
from google.adk import Runner, Workflow
from google.adk.agents import BaseAgent
from google.adk.sessions import DatabaseSessionService, BaseSessionService, InMemorySessionService

load_dotenv()
SESSION_DB_URL=os.environ.get("SESSION_DB_URL", None)

def get_session_service() -> BaseSessionService:
    try:
        if SESSION_DB_URL:
            session_service = DatabaseSessionService(db_url=SESSION_DB_URL)
            logging.info("✅ Persistent PostgreSQL session service initialized successfully.")
        else:
            session_service = InMemorySessionService()
            logging.info("✅ Fallback: In-memory session service initialized successfully.")
        return session_service
    except Exception as e:
        logging.exception(f"❌ Failed to connect to Session service: {e}")
        raise e