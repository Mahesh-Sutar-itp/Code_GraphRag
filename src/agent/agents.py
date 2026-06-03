import logging

from google.adk.agents import LlmAgent
from google.genai.types import Content, Part

from src.agent.llm_models import get_azure_openai_model
from src.agent.models import PlannerInput, PlannerOutput, ResolverInput
import src.agent.instruction_dump as instructions

# def create_llm_agent():
#     MODEL_API_KEY:str|None = os.environ.get("GITHUB_TOKEN", None)

#     if MODEL_API_KEY is None:
#         raise Exception("API Key Not found. Ensure GITHUB_TOKEN is included in .env file.")

#     llm_model=LiteLlm(
#         model="openai/gpt-4.1", 
#         api_key= MODEL_API_KEY, 
#         api_base="https://models.inference.ai.azure.com"
#     )

#     return LlmAgent(
#         name="code_analyzer",
#         model=llm_model,
#         static_instruction=Content(
#             role='user',
#             parts=[
#                 Part(text=instructions.CODEBASE_ANALYZER_INSTRUCTION)
#             ]
#         ),
#         output_schema=AgentDecision
#     )

def create_planner_agent():
    try:
        planner_llm_model=get_azure_openai_model("openai/gpt-4o")
        return LlmAgent(
            name='node_relevance_ranker',
            model=planner_llm_model,
            static_instruction=Content(
                role='user',
                parts=[Part(text=instructions.PLANNER_INSTRUCTION)]
            ),
            input_schema=PlannerInput,
            output_schema=PlannerOutput
        )
    except Exception:
        logging.exception("Internal Server Error: While fetching the planner llm model")
        raise RuntimeError("Internal Server Error: While fetching the planner llm model")

def create_resolver_agent():
    try:
        resolver_llm_model=get_azure_openai_model("openai/gpt-4.1")
        return LlmAgent(
            name='user_query_resolver',
            model=resolver_llm_model,
            static_instruction=Content(
                role='user',
                parts=[Part(text=instructions.RESOLVER_INSTRUCTION)]
            ),
            input_schema=ResolverInput
        )
    except Exception:
        logging.exception("Internal Server Error: While fetching the resolver llm model")
        raise RuntimeError("Internal Server Error: While fetching the resolver llm model")

# code_analyzer=create_llm_agent()

# def extract_query(content: Content) -> str:
#     if not content or not content.parts:
#         return ""
    
#     texts = []
#     for part in content.parts:
#         if hasattr(part, "text") and part.text:
#             texts.append(part.text)
    
#     return "\n".join(texts)

# def check_agent_output_schema_validity(agent_response) -> AgentDecision:
#     if isinstance(agent_response, AgentDecision):
#         return agent_response
    
#     if isinstance(agent_response, dict):
#         try:
#             print("/*******************************/")
#             print("Try coverting to agentdecision")
#             print("/*******************************/")
#             return AgentDecision(**agent_response)
#         except Exception as e:
#             print("/*******************************/")
#             print("Problem coverting to agentdecision")
#             print("/*******************************/")
#             raise ValueError(f"Schema validation failed: {agent_response}") from e

#     raise ValueError(f"Invalid agent response type: {type(agent_response)}")

# @node(rerun_on_resume=True)
# async def resolution_workflow(ctx: Context, node_input: Content):
#     user_query:str = extract_query(node_input)

#     query_context:str = await ctx.run_node(fetch_initial_context, node_input=node_input)
    
#     agent_input = f"""
#     User Query:
#     {user_query}

#     Retrieved Context:
#     {query_context}
#     """

#     agent_response = await ctx.run_node(code_analyzer, node_input=agent_input)
#     structured_agent_response=check_agent_output_schema_validity(agent_response)

#     loop:int = 0
#     while not structured_agent_response.is_sufficient:
#         node_ids = list(set(structured_agent_response.required_context_node_ids or []))

#         if loop>=5 or not node_ids:
#             agent_response=await ctx.run_node(code_analyzer, node_input=instructions.SYNTHESIS_INSTRUCTION)
#             structured_agent_response=check_agent_output_schema_validity(agent_response)

#             print("/***************************************/")
#             print("Break loop because context is sufficient")
#             print("/***************************************/")

#             break

#         if len(node_ids) > 3:
#             node_ids = node_ids[:3]

#         missing_node_context = await ctx.run_node(fetch_missing_nodes, node_input=node_ids)
        
#         agent_response = await ctx.run_node(code_analyzer, node_input=missing_node_context)
#         structured_agent_response=check_agent_output_schema_validity(agent_response)

#         loop+=1
    
#     return Content(
#         role="assistant",
#         parts=[Part(text=structured_agent_response.final_answer)]
#     )


