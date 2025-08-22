"""
Brainstorm Agent

Orchestrates a brainstorming session using multiple personas.
Implements persona coordination, chat compression, and meeting summarization.
"""

from typing import List
from typing_extensions import TypedDict, Literal

from langgraph.graph import MessagesState, StateGraph
from langgraph.graph import START, END
from langgraph.types import interrupt, Command
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.messages import RemoveMessage
from langgraph.checkpoint.memory import MemorySaver

from agent_storming.utils import read_file_contents
from agent_storming.persona_factory import Persona


class BrainStormState(MessagesState):
    topic: str
    max_personas: int 
    personas: List[Persona]
    current_persona: Persona 
    human_boss_feedback: str
    summary: str
   

class BrainstormAgent:
    def __init__(
        self,
        llm,
        persona_factory_agent: "PersonaFactoryAgent",
        persona_agent: "PersonaAgent", 
        coordinator_instructions_path: str,
        compress_chat_instructions_path: str,
        summarize_meeting_instructions_path: str,
        MAX_MESSAGES_BEFORE_COMPRESSION: int = 20,
        checkpointer=None,
    ):
        self.llm = llm
        self.persona_factory_agent = persona_factory_agent
        self.persona_agent = persona_agent  # Store the agent
        self.MAX_MESSAGES_BEFORE_COMPRESSION = MAX_MESSAGES_BEFORE_COMPRESSION
        self.checkpointer = checkpointer or MemorySaver()

        # Load prompt templates during initialization
        self.coordinator_instructions = read_file_contents(coordinator_instructions_path)
        self.compress_chat_instructions = read_file_contents(compress_chat_instructions_path)
        self.summarize_meeting_instructions = read_file_contents(summarize_meeting_instructions_path)

    def coordinate(self, state: BrainStormState) -> Command[Literal["meeting_notes", "active_persona"]]:
        """
        Node: Coordinate the brainstorm — decide next persona or end meeting.
        Can be interrupted for human feedback.
        """
        # interrupt execution to get human input
        response = interrupt("Do you have any comment?")
        human_input = response["human_input"]

        if human_input.strip().lower() == "end":
            return Command(
                goto="meeting_notes",
                update={
                    "messages": state["messages"],
                    "topic": state["topic"]
                }
            )

        # Otherwise, update messages with optional human input
        messages = state["messages"]
        if human_input.strip() != "":
            messages = messages + [HumanMessage(content=human_input)]

        # Prepare input for LLM to pick next persona
        topic = state["topic"]
        personas_str = '\n'.join([p.to_string() for p in state["personas"]])
        system_message = self.coordinator_instructions.format(topic=topic, personas=personas_str)

        structured_llm = self.llm.with_structured_output(Persona)
        selected_persona = structured_llm.invoke([SystemMessage(content=system_message)] + messages)

        return Command(
            goto="active_persona",
            update={
                "current_persona": selected_persona,
                "messages": messages,
                "topic": topic
            }
        )

    def compress_chat_history(self, state: BrainStormState):
        """
        Node: Compress older messages when chat gets too long to manage context.
        Keeps last 2 messages + a summary.
        """
        messages = state["messages"]

        if len(messages) <= self.MAX_MESSAGES_BEFORE_COMPRESSION:
            return {}  # No change needed

        # Compress all but the last two messages
        messages_to_compress = messages[:-2]
        conversation_text = "\n\n".join(
            [f"{msg.__class__.__name__}: {msg.content}" for msg in messages_to_compress]
        )

        compression_prompt = self.compress_chat_instructions.format(conversation_text=conversation_text)
        summary_response = self.llm.invoke([HumanMessage(content=compression_prompt)])

        # Construct new compressed message list
        compressed_messages = [summary_response]  # Summary as first message
        # duplicate the last two messages so that they come after summary with different ids (so that they are not removed in the next step)
        for msg in messages[-2:]:
            if isinstance(msg, HumanMessage):
                compressed_messages.append(HumanMessage(content=msg.content))
            else:
                compressed_messages.append(AIMessage(content=msg.content))

        messages += compressed_messages

        # Return instructions to remove old messages and append new ones
        return {
            "messages": [
                RemoveMessage(id=m.id) for m in messages[:-3]  # Remove all but last 3 (including summary)
            ]
        }

    def summarize_meeting(self, state: BrainStormState):
        """
        Node: Generate a final summary of the brainstorming session.
        """
        topic = state["topic"]
        messages = state["messages"]

        summarization_prompt = self.summarize_meeting_instructions.format(topic=topic)
        summary = self.llm.invoke([HumanMessage(content=summarization_prompt)] + messages)

        return {"summary": summary.content}

    def build_graph(self):
        """
        Builds the full brainstorming workflow.
        Compiles the persona_agent's graph internally for consistency.
        """
        builder = StateGraph(BrainStormState)

        persona_factory_graph = self.persona_factory_agent.build_graph()
        # Add nodes
        builder.add_node("persona_factory", persona_factory_graph)
        builder.add_node("coordinator", self.coordinate)

        # Build the subgraph now (lazy compilation)
        active_persona_graph = self.persona_agent.build_graph()
        builder.add_node("active_persona", active_persona_graph)

        builder.add_node("compress_chat_history", self.compress_chat_history)
        builder.add_node("meeting_notes", self.summarize_meeting)

        # Define edges
        builder.add_edge(START, "persona_factory")
        builder.add_edge("persona_factory", "coordinator")
        builder.add_edge("active_persona", "compress_chat_history")
        builder.add_edge("compress_chat_history", "coordinator")
        builder.add_edge("meeting_notes", END)

        # Compile main graph
        graph = builder.compile(
            checkpointer=self.checkpointer
        )

        return graph.with_config(run_name="Brainstorm Session")

