import sys, os
from pathlib import Path
# Add absolute project root to sys.path for streamlit to work
PROJECT_ROOT = Path(__file__).parent.resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import uuid
from pathlib import Path
import logging

from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.types import Command
import streamlit as st

from agent_storming.persona_factory import PersonaFactoryAgent
from agent_storming.persona_agent import PersonaAgent
from agent_storming.moderator_agent import BrainstormAgent
from agent_storming.utils import ensure_env
from agent_storming.config_loader import load_config


def build_graph():
    # Load config
    SCRIPT_DIR = Path(__file__).parent
    config = load_config(SCRIPT_DIR / "config.yaml")

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
    return brainstorm_agent.build_graph()



# Build the graph once at startup
if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
    st.session_state.thread = {"configurable": {"thread_id": str(uuid.uuid4())}}
    st.session_state.state = None
    st.session_state.stage = "setup"   # setup → feedback → discussion → done
    st.session_state.messages = []

st.title("🧠 Agent Storm: AI Brainstorming")

# Stage 1: User provides topic + personas
if st.session_state.stage == "setup":
    topic = st.text_input("Enter a topic", "Choosing the appropriate cloud provider for deploying our application.")
    max_personas = st.slider("Max personas", 2, 7, 3)

    if st.button("Generate Personas"):
        with st.spinner("Generating personas..."):
            st.session_state.state = st.session_state.graph.invoke(
                {"topic": topic, "max_personas": max_personas},
                st.session_state.thread, subgraphs=True
            )
        st.session_state.stage = "feedback"
        st.rerun()

# Stage 2: Human feedback on personas
elif st.session_state.stage == "feedback":
    st.subheader("Generated Personas")
    for persona in st.session_state.state["personas"]:
        st.write(f"Name: {persona.name}")
        st.write(f"Role: {persona.role}")
        st.write(f"Description: {persona.description}")

    feedback = st.text_area("Any feedback about these personas (Leave empty if you don't need any change)?")
    if st.button("Submit Feedback"):
        # st.write(st.session_state.graph.get_state(st.session_state.thread, subgraphs=True).tasks[0])
        st.session_state.graph.update_state(
            st.session_state.graph.get_state(st.session_state.thread, subgraphs=True).tasks[0][5][2],
            {"human_boss_feedback": feedback},
            as_node="human_feedback"
        )
        st.session_state.state = st.session_state.graph.invoke(None, st.session_state.thread, subgraphs=True)
        if feedback:
            # update again with none to resume from the interrupt
            st.session_state.graph.update_state(
                st.session_state.graph.get_state(st.session_state.thread, subgraphs=True).tasks[0][5][2],
                {"human_boss_feedback": None},
                as_node="human_feedback"
            )
            st.session_state.state = st.session_state.graph.invoke(None, st.session_state.thread, subgraphs=True)

        st.session_state.stage = "discussion"
        with st.spinner("Processing the first opinion..."):
            st.session_state.state = st.session_state.graph.invoke(
                Command(resume={"human_input": "What do you think?"}),
                st.session_state.thread,
                subgraphs=True
            )

        st.rerun()

# Stage 3: Discussion loop
elif st.session_state.stage == "discussion":
    st.subheader("Discussion")

    # Show existing messages
    for msg in st.session_state.state["messages"]:
        st.markdown(f"**{msg.type.upper()}**: {msg.content}")

    user_input = st.chat_input("Your input (type 'end' to finish and generate meeting summary):")
    if user_input:
        if user_input.strip().lower() == "end":
            st.session_state.stage = "done"

        with st.spinner("Processing..."):
            st.session_state.state = st.session_state.graph.invoke(
                Command(resume={"human_input": user_input}),
                st.session_state.thread,
                subgraphs=True
            )
        st.rerun()

# Stage 4: Final summary
elif st.session_state.stage == "done":
    st.success("✅ Brainstorming session finished!")
    st.subheader("Meeting Notes")
    st.write(st.session_state.state["summary"])

