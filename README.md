# 🧠 Agent Storm: AI Brainstorming System  

Agent Storm is an **AI multi-agent system** that allows one to have brainstorming sessions with a team of AI experts. This agentic system will generate multiple personas (LLM instances with specific personalities) depending on the topic you want to discuss. It will then coordinate the discussion between you and these autonomous personas to refine ideas collaboratively.  

**Human-in-the-loop** support: The system enables human intervention at key stages (persona approval, discussion turns), the graph pauses and waits for user feedback. 

#### Tools & Technologies:
**LangGraph**, **LangChain**, **OpenAI API**, with a lightweight **Streamlit web interface** for human interaction.

---

## 🚀 Architecture  

The system is built with **LangGraph** to orchestrate different agents:  

- **PersonaFactoryAgent** → generates initial candidate personas for the brainstorming session.  
- **PersonaAgent** → personas that research, form opinions, and contribute to the discussion.  
- **BrainstormAgent (Coordinator)** → moderates the discussion, compresses history, and produces a final summary.   

#### High-Level Workflow Diagram

![Architecture Diagram](docs/agent_storm_graph.png)  

#### Execution flow:
1. **Persona Generation** → LLM proposes a set of personas.  
2. **Human Feedback** → user reviews and refines the personas.  
3. **Discussion Loop** → personas debate, user may interject.  
4. **Final Summary** → coordinator produces meeting notes.

**P.S:** since there is only one persona that can talk at a time we don't need to duplicate the persona agent *n* times in our graph. A smarter approach would be to have one agent representing the active persona at a given time. That means, when the execution flow comes to the persona agent, it is told which persona it is supposed to represent now. In other words, the persona agent wears a different persona hat each iteration.

Below is the architecture diagram of the persona factory agent and the active persona agent.

The **persona factory agent** will generate an initial group of personas based on the topic you propose for discussion. The user can then give their feedback, asking for modifications if they want. After that these personas are fixed for the entire session.

The **persona agent** is equiped with the ability to do web search in order to obtain up-to-date information about the ideas being discussed. After retrieving the relevant context information an LLM is used to generate its opinion or answer any questions directed to it.

<table width="100%">
<tr>
  <td width="50%" align="center"><h4>Persona Factory Agent</h4></td>
  <td width="50%" align="center"><h4>Active Persona Agent</h4></td>
</tr>
<tr>
  <td width="50%" align="center">
    <img src="docs/persona_factory_graph.png" alt="Architecture Diagram"/>
    <img width="441" height="1">
  </td>
  <td width="50%" align="center">
    <img src="docs/persona_agent_graph.png" alt="System Workflow"/>
  </td>
</tr>
</table>

---

## 📦 Installation  

Clone the repo and install dependencies:  

```bash
git clone https://github.com/m-dorgham/agent-storm.git
cd agent-storm
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## ⚡ Usage  

### Run the web interface  

The project comes with a **Streamlit UI** (`app.py`) for easy testing:  

```bash
streamlit run agent_storming/app.py
```
This launches a simple web app where you can:

- Enter a **topic** and the number of personas to generate.
- Provide **feedback** on the generated personas.
- Participate in the **discussion loop** until typing end.
- View the **final summary** of the brainstorming session.

---

## 🔑 API Keys  

This project requires a few API keys to run:  

- `OPENAI_API_KEY`  
- `TAVILY_API_KEY`  
- `LANGSMITH_API_KEY`  

The easiest way to provide them is by creating a `.env` file in the project root:  

```bash
# .env
OPENAI_API_KEY=your_openai_key_here
TAVILY_API_KEY=your_tavily_key_here
LANGSMITH_API_KEY=your_langsmith_key_here
```

The project uses `python-dotenv` to load these automatically, so you don’t need to export them manually in your shell.

---

## 📜 License  

MIT License.  
