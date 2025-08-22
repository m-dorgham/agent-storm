"""
Persona agent

Contains the nodes of the persona agent.
"""

from typing import Optional
from pydantic import BaseModel, Field

from langgraph.graph import MessagesState, StateGraph
from langgraph.graph import START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_tavily import TavilySearch

from agent_storming.utils import read_file_contents
from agent_storming.persona_factory import Persona


class PersonaState(MessagesState):
    context: str # Source docs
    current_persona: Persona # Expert persona asking questions
    topic: str # Topic of discussion


class SearchQuery(BaseModel):
    search_query: str = Field(None, description="Search query for retrieval.", max_length=300)


class PersonaAgent:
    def __init__(
        self,
        llm,
        tavily_search: TavilySearch,
        search_instructions_path: str,
        opinion_instructions_path: str,
        checkpointer: Optional[MemorySaver] = None,
    ):
        """
        Initialize the PersonaAgent with prompt file paths.

        Args:
            llm: The language model to use.
            tavily_search: TavilySearch tool instance.
            search_instructions_path: Path to the .txt file for search query generation.
            opinion_instructions_path: Path to the .txt file for opinion generation.
            checkpointer: Optional checkpointing system (default: MemorySaver).
        """
        self.llm = llm
        self.tavily_search = tavily_search
        self.search_instructions = read_file_contents(search_instructions_path)
        self.opinion_instructions = read_file_contents(opinion_instructions_path)
        self.checkpointer = checkpointer or MemorySaver()

    def search_web(self, state: PersonaState):
        """
        Node: Retrieve documents from web search based on the current persona and topic.
        """
        topic = state["topic"]
        persona = state["current_persona"]
        messages = state["messages"]

        # Generate search query using structured LLM
        structured_llm = self.llm.with_structured_output(SearchQuery)
        system_message = self.search_instructions.format(topic=topic, persona=persona.to_string())
        search_query_msg = structured_llm.invoke(
            [SystemMessage(content=system_message)] + messages
        )

        search_query = search_query_msg.search_query
        if not search_query or not search_query.strip():
            search_query = f"{state['current_persona'].role} perspective on {state['topic']}"
            logging.info(f"Generated fallback search query: '{search_query}'")

        # Perform web search
        try:
            search_docs = self.tavily_search.invoke({"query": search_query})
        except Exception as e:
            logging.error(f"Search failed: {e}")
            search_docs = {"results": []}


        # Format results
        formatted_search_docs = "\n\n---\n\n".join(
            [
                f'<Document href="{doc["url"]}"/>\n{doc["content"]}\n</Document>'
                for doc in search_docs.get("results", [])
            ]
        )

        return {"context": formatted_search_docs}

    def generate_opinion(self, state: PersonaState):
        """
        Node: Generate an opinion from the current persona using retrieved context.
        """
        persona = state["current_persona"]
        messages = state["messages"]
        context = state["context"]
        topic = state["topic"]

        # Generate opinion
        system_message = self.opinion_instructions.format(
            topic=topic, persona=persona.to_string(), context=context
        )
        opinion = self.llm.invoke([SystemMessage(content=system_message)] + messages)

        return {"messages": [opinion]}

    def build_graph(self):
        """
        Builds and compiles the state graph.

        Returns:
            Compiled LangGraph graph with run name configured.
        """
        builder = StateGraph(PersonaState)

        builder.add_node("search_web", self.search_web)
        builder.add_node("generate_opinion", self.generate_opinion)

        builder.add_edge(START, "search_web")
        builder.add_edge("search_web", "generate_opinion")
        builder.add_edge("generate_opinion", END)

        graph = builder.compile(checkpointer=self.checkpointer)
        return graph.with_config(run_name="Expert Persona")

