"""
Persona factory agent

Contains the nodes of the persona generation agent.
"""

from typing import List, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


from agent_storming.utils import read_file_contents


class Persona(BaseModel):
    name: str = Field(
        description="Name of the persona."
    )
    role: str = Field(
        description="Role of the persona in the context of the topic.",
    )
    description: str = Field(
        description="Description of the persona focus, concerns, and expertise.",
    )
    
    def to_string(self) -> str:
        return f"Name: {self.name}\nRole: {self.role}\nDescription: {self.description}\n"


class Perspectives(BaseModel):
    personas: List[Persona] = Field(
        description="Comprehensive list of personas with their names, roles and descriptions.",
    )


class GeneratePersonasState(TypedDict):
    topic: str # Topic of discussion
    max_personas: int # Number of personas
    human_boss_feedback: str # Human feedback
    personas: List[Persona] # experienced personas


class PersonaFactoryAgent:
    def __init__(self, llm, create_personas_instructions_path: str, checkpointer=None,):
        """
        Initialize the agent with required components.

        Args:
            llm: The language model instance.
            create_personas_instructions: Prompt template string with {topic}, {human_boss_feedback}, {max_personas}
        """
        self.llm = llm
        self.create_personas_instructions = read_file_contents(create_personas_instructions_path)
        self.checkpointer = checkpointer or MemorySaver()

    def create_personas(self, state: GeneratePersonasState):
        """
        Node: Create personas based on the topic and feedback.
        """
        topic = state['topic']
        max_personas = state['max_personas']
        human_boss_feedback = state.get('human_boss_feedback', '')

        # Enforce structured output
        structured_llm = self.llm.with_structured_output(Perspectives)

        # Format system message using the template
        system_message = self.create_personas_instructions.format(
            topic=topic,
            human_boss_feedback=human_boss_feedback,
            max_personas=max_personas
        )

        # Generate personas
        response = structured_llm.invoke([
            SystemMessage(content=system_message),
            HumanMessage(content="Generate the group of experts.")
        ])

        return {"personas": response.personas}

    def human_feedback(self, state: GeneratePersonasState):
        """
        No-op node intended for human-in-the-loop feedback (to be interrupted on).
        """
        # This is a placeholder where execution can pause for human input
        return {}

    def pass_state(self, state: GeneratePersonasState):
        return {}

    def should_continue(self, state: GeneratePersonasState):
        """ Return the next node to execute """

        # Check if human feedback
        human_boss_feedback=state.get('human_boss_feedback', None)
        if human_boss_feedback:
            return "create_personas"
    
        # Otherwise end
        return "pass_state"


    def build_graph(self):
        builder = StateGraph(GeneratePersonasState)
        builder.add_node("create_personas", self.create_personas)
        builder.add_node("human_feedback", self.human_feedback)
        builder.add_node("pass_state", self.pass_state)
        builder.add_edge(START, "create_personas")
        builder.add_edge("create_personas", "human_feedback")
        builder.add_conditional_edges(
            "human_feedback", 
            self.should_continue, 
            {
                "create_personas": "create_personas",
                "pass_state": "pass_state"
            }
        )

        return builder.compile(interrupt_before=['human_feedback'], checkpointer=self.checkpointer)

