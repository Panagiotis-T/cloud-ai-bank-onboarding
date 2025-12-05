"""
Banking Onboarding Agent (ReAct + Tools + Memory)
"""

from langchain_classic.agents import create_react_agent, AgentExecutor
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langsmith import uuid7
from app.prompts import get_agent_prompt_template
from app.tools import get_tools

def get_agent():
    llm = OllamaLLM(model="gpt-oss:120b-cloud", temperature=0) #gpt-oss-safeguard:20b, gpt-oss:20b-cloud, gpt-oss:120b-cloud
    tools = get_tools()

    template_str = get_agent_prompt_template()
    prompt = PromptTemplate(
        input_variables=["input", "agent_scratchpad", "tools", "tool_names", "messages"],
        template=template_str
    )

    react_agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
    return AgentExecutor(
        agent=react_agent,
        tools=tools,
        verbose=True,
        max_iterations=10,
        handle_parsing_errors=True,
        return_intermediate_steps=False
    )


# ---------------------------
# CONVERSATION MEMORY
# ---------------------------
store = {}

def get_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]


def get_conversational_agent():
    base_agent = get_agent()
    return RunnableWithMessageHistory(
        base_agent,
        lambda session_id: get_history(session_id),
        input_messages_key="input",
        history_messages_key="messages",
    )


conv_agent = get_conversational_agent()


def chat():
    session_id = str(uuid7())
    print("(type 'exit' or 'quit' to end)\n")
    while True:
        user_message = input("> \n")
        if user_message.lower() in ["exit", "quit"]:
            break
        response = conv_agent.invoke(
            {"input": user_message},
            config={"configurable": {"session_id": session_id}}
        )
        print("Agent:", response["output"])

        # --- DEBUG: PRINT FULL HISTORY ---
        history = get_history(session_id)
        print("\n--- CHAT HISTORY ---")
        for msg in history.messages:
            print(f"{msg.type.upper()}: {msg.content}")
        print("---------------------\n")
