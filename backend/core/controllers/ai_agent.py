"""This file is controller for the Fast API"""

from langchain.memory import ConversationBufferMemory
from graph_rag.ai_agent import MemoryParallelAgent
from graph_rag.ai_agent import MemorySequentialAgent

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
agent_executor = MemorySequentialAgent(memory=memory) 


def ask_agent(message: str) -> dict:
    return agent_executor.invoke(message)
