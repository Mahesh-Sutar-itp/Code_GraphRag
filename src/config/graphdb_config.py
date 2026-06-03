import os

from dotenv import load_dotenv
from neo4j import Driver, GraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

_driver: Driver|None = None

def get_neo4j_driver() -> Driver:
    global _driver

    if NEO4J_PASSWORD is None:
        raise RuntimeError(
            "NEO4J_PASSWORD not set. Make sure .env exists at project root."
        )
    
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    return _driver