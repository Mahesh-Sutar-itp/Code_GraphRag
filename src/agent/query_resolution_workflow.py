from google.adk import Workflow

from src.agent.agent_runner import ADKAgentRunner
from src.agent.nodes import agent_workflow

class QueryResolutionWorkflow:
    def __init__(self, user_id: str, session_id: str):
        root_agent=Workflow(
            name="query_resolution_workflow_agent",
            edges=[("START", agent_workflow)]
        )

        self.runner=ADKAgentRunner(agent=root_agent, app_name='code_graph_rag', user_id=user_id, session_id=session_id)

    def resolve_query(self, query: str):
        # Logic of prompt enhancement if required.

        final_response=self.runner.run(prompt=query)
        return final_response