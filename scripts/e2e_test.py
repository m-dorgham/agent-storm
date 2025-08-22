
import os
import uuid
from pathlib import Path
import logging
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.types import Command

from agent_storming.persona_factory import PersonaFactoryAgent
from agent_storming.persona_agent import PersonaAgent
from agent_storming.moderator_agent import BrainstormAgent
from agent_storming.utils import ensure_env
from agent_storming.config_loader import load_config


logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file automatically
load_dotenv()

def run_brainstorm_session():
    # Load config
    SCRIPT_DIR = Path(__file__).parent.parent
    config = load_config(SCRIPT_DIR / "agent_storming/config.yaml")

    ensure_env("OPENAI_API_KEY")
    ensure_env("TAVILY_API_KEY")
    ensure_env("LANGSMITH_API_KEY")

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = "agent-storming"

    PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

    llm = ChatOpenAI(
        model=config["llm"]["model"],
        temperature=config["llm"]["temperature"],
        max_retries=config["llm"]["max_retries"],
    )
    tavily_search = TavilySearch(max_results=config["search"]["max_results"])

    # Build sub-agents
    factory_agent = PersonaFactoryAgent(
        llm=llm,
        create_personas_instructions_path=PROMPTS_DIR /"create_personas_instructions.txt"
    )

    detailed_persona_agent = PersonaAgent(
        llm=llm,
        tavily_search=tavily_search,
        search_instructions_path=PROMPTS_DIR /"web_search_instructions.txt",
        opinion_instructions_path=PROMPTS_DIR /"generate_opinion_instructions.txt"
    )

    # Build orchestrator
    brainstorm_agent = BrainstormAgent(
        llm=llm,
        persona_factory_agent=factory_agent,
        persona_agent=detailed_persona_agent,  
        coordinator_instructions_path=PROMPTS_DIR /"coordinator_instructions.txt",
        compress_chat_instructions_path=PROMPTS_DIR /"compress_chat_instructions.txt",
        summarize_meeting_instructions_path=PROMPTS_DIR /"summarize_meeting_instructions.txt",
        MAX_MESSAGES_BEFORE_COMPRESSION=config["brainstorm"]["max_messages_before_compression"],
    )

    # Final graph
    graph = brainstorm_agent.build_graph()

    thread_id = str(uuid.uuid4())
    topic = "Who did really build the pyramids and how were they built?"
    thread = {"configurable": {"thread_id": thread_id}}

    # generate personas first
    result = graph.invoke(
        {"topic": topic, "max_personas": config["brainstorm"]["max_personas"]},
        thread, subgraphs=True
    )
    logging.info(result)
    logging.info("-------------------------------------------------------")

    parent_graph_state = graph.get_state(thread, subgraphs=True)
    logging.info(parent_graph_state)
    logging.info("-------------------------------------------------------")

    # assume no feedback from user
    graph.update_state(parent_graph_state.tasks[0].state.config, {"human_boss_feedback": None}, as_node="human_feedback")
    for event in graph.stream(None, thread, stream_mode="updates", subgraphs=True):
        logging.info(event)

    first_message = "What do you think?"

    results = graph.invoke(Command(resume={"human_input": first_message}), thread, subgraphs=True)
    results["messages"][-1].pretty_print()

if __name__ == "__main__":
    run_brainstorm_session()
