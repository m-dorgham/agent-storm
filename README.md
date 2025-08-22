# 🧠 Agent Storm: AI Brainstorming System  

Agent Storm is an **AI-powered brainstorming framework** that coordinates multiple autonomous personas to generate, discuss, and refine ideas collaboratively.  
It combines **LLMs, search tools, and a coordinating agent** in a structured graph execution flow, with a lightweight **Streamlit web interface** for human interaction.  

---

## 🚀 Architecture  

The system is built around **LangGraph** to orchestrate different agents:  

- **PersonaFactoryAgent** → generates initial candidate personas for the brainstorming session.  
- **PersonaAgent** → personas that research, form opinions, and contribute to the discussion.  
- **BrainstormAgent (Coordinator)** → moderates the discussion, compresses history, and produces a final summary.  
- **Human-in-the-loop** → at key stages (persona approval, discussion turns), the graph pauses and waits for user feedback.  

![Architecture Diagram](docs/architecture.png)  
*(Optional: add an image if you like)*  

Execution flow:  
1. **Persona Generation** → LLM proposes a set of personas.  
2. **Human Feedback** → user reviews and refines the personas.  
3. **Discussion Loop** → personas debate, user may interject.  
4. **Final Summary** → coordinator produces meeting notes.  

---

## 📦 Installation  

Clone the repo and install dependencies:  

```bash
git clone https://github.com/<your-username>/agent-storming.git
cd agent-storming
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
