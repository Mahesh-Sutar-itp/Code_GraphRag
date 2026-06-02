import logging

from google.adk import Context
from google.adk.workflow import node
from google.genai.types import Content

from src.agent.agents import create_planner_agent, create_resolver_agent
from src.agent.models import GraphEdge, GraphNode, PlannerInput, PlannerOutput, ResolverInput
from src.agent.state_keys import QUERY_SPECIFIC_RELEVANT_NODES_KEY, USER_QUERY_KEY
from src.agent.utils_functions import error_response, extract_text_from_content, get_dummy_planner_output, get_pricing_graph_data, get_relevant_nodes_for_resolver, parse_planner_input_or_raise, parse_planner_output_or_raise, parse_resolver_input_or_raise, success_response

@node(name="query_context_fetcher", rerun_on_resume=False)
def fetch_query_context_for_planner_agent(ctx: Context, node_input: str):
    # Call Retrieval Pipeline once setup instead of below function returning dummy data.
    query_context: tuple[list[GraphNode], list[GraphEdge]]=get_pricing_graph_data()
    return PlannerInput(user_query=node_input, code_nodes=query_context[0], code_edges=query_context[1])

@node(name="relevant_ranked_nodes_fetcher", rerun_on_resume=False)
def fetch_relevant_ranked_nodes_for_resolver_agent(ctx: Context, node_input: PlannerOutput):
    user_query=ctx.session.state.get(USER_QUERY_KEY, "")
    # Call Retrieval Pipeline once setup instead of below function returning dummy data.
    return get_relevant_nodes_for_resolver(user_query=user_query, planner_output=node_input, retrieval_pipeline=None, total_input_context_window_tokens=8000)


# # Testable dummy planner output returning node. Removable after test.
# @node(name="dummy_planner_output_fetcher", rerun_on_resume=False)
# def fetch_dummy_planner_output(ctx: Context, node_input):
#     return get_dummy_planner_output()


@node(name="query_resolution_workflow", rerun_on_resume=True)
async def agent_workflow(ctx: Context, node_input:Content):
    
    #-----------Extract User Query--------------#
    user_query=extract_text_from_content(node_input)
    ctx.session.state[USER_QUERY_KEY]=user_query
    
    #-----------Retrieve Query Context--------------#
    try:
        query_context=await ctx.run_node(node=fetch_query_context_for_planner_agent, node_input=user_query)
    except Exception:
        logging.exception("Faced error while executing query_context_fetcher for Planner Agent")
        return error_response("500", msg="Something went wrong while finding the code data related to your query. Please try again.")

    try:
        structured_planner_input: PlannerInput = parse_planner_input_or_raise(query_context)
    except ValueError:
        logging.exception("Invalid Planner Input Structure from Query Context")
        return error_response(code="500", msg="Something went wrong while finding the code data related to your query. Please try again.")
    
    #-----------Activate Planner Agent--------------#
    try:
        generate_plan=await ctx.run_node(node=create_planner_agent(), node_input=structured_planner_input)
    except Exception:
        logging.exception("Faced error while executing Planner Agent")
        return error_response("500", msg="Something went wrong while planning. Please try again.")

    try:
        structured_planner_output: PlannerOutput = parse_planner_output_or_raise(generate_plan)
    except ValueError:
        logging.exception("Invalid Planner Output Structure from Planner Agent")
        return error_response("500", msg="Something went wrong while planning. Please try again.")

    
    # #-----------Dummy Planner Output and Validation--------------#
    # dummy_plan=await ctx.run_node(node=fetch_dummy_planner_output)
    # try:
    #     structured_planner_output: PlannerOutput = parse_planner_output_or_raise(dummy_plan)
    # except ValueError:
    #     logging.exception("Invalid Planner Output Structure from Planner Agent")
    #     return "Internal Server Error while resolving query plan"

    #-----------Retrieve Relevant Ranked Nodes for Resolver Agent--------------#
    try:
        relevant_nodes=await ctx.run_node(node=fetch_relevant_ranked_nodes_for_resolver_agent, node_input=structured_planner_output)
    except Exception:
        logging.exception("Faced error while executing relevant_ranked_nodes_fetcher for Resolver Agent")
        return error_response("500", msg="Something went wrong while resolving query. Please try again.")

    try:
        structured_relevant_nodes: ResolverInput = parse_resolver_input_or_raise(relevant_input=relevant_nodes)
        ctx.session.state[QUERY_SPECIFIC_RELEVANT_NODES_KEY]=[node.node_id for node in structured_relevant_nodes.code_nodes]
    except ValueError:
        logging.exception("Invalid Resolver Input Structure while fetching relevant nodes from PlannerOutput")
        return error_response("500", msg="Something went wrong while resolving query. Please try again.")

    #-----------Activate Resolver Agent--------------#
    try:
        resolved_output=await ctx.run_node(node=create_resolver_agent(), node_input=structured_relevant_nodes)
    except Exception:
        logging.exception("Faced error while executing relevant_ranked_nodes_fetcher for Resolver Agent")
        return error_response("500", msg="Something went wrong while resolving query. Please try again.")

    return success_response(msg=resolved_output, relevant_node_ids=ctx.session.state.get(QUERY_SPECIFIC_RELEVANT_NODES_KEY,[]))
