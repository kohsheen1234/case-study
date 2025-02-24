# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## PPT
https://docs.google.com/presentation/d/1C1cYQ6B2ONgeRiIXZ4P3HS0U2kkieBi5Fw2xB2TA3Mc/edit?usp=sharing

The provided code represents backend implementation designed to build an agentic AI chatbot that leverages Retrieval-Augmented Generation (RAG) techniques integrated with a Neo4j graph database. At its core, the system is built on FastAPI and is structured to process user queries through a series of carefully orchestrated components. The FastAPI controller exposes an endpoint ("/agent/") that captures incoming requests and passes them to an AI agent via the function `ask_agent`. This function itself delegates the query processing to a LangChain-based agent that uses either a sequential or parallel approach—with or without memory—to generate a response. Memory is managed using the `ConversationBufferMemory` from LangChain, ensuring that conversational context is maintained across interactions.

The agent architecture is highly modular and configurable. The code defines a base `Agent` class, which sets up the underlying agent executor using LangChain’s `create_react_agent`. Custom classes such as `CustomOutputParser` and `CustomPromptTemplate` are used to parse the language model's output and format the prompts, respectively. These components enforce a structured chain-of-thought format (including “Thought”, “Action”, “Observation”, and “Confidence” steps) that guides the agent’s reasoning process and ensures that every final answer is accompanied by a confidence score and interval. The design allows the agent to choose between different execution modes—sequential agents (both with and without memory) and parallel agents (using a combined query tool)—to dynamically decide whether to invoke tools like querying the graph database or performing semantic similarity searches.

The code further integrates sophisticated mechanisms for generating and refining Cypher queries to interact with the Neo4j graph database. A detailed system prompt (the `CYPHER_PROMPT`) outlines the entities, properties, and relationships present in the graph, and provides explicit instructions for translating natural language queries into precise Cypher queries. The function `generate_cypher_query` utilizes OpenAI’s API to generate an initial query, which is then passed through `correct_cypher_query`—a process that validates and optimizes the query according to best practices, ensuring both syntactical correctness and performance efficiency. This dynamic query generation is critical for ensuring that the agent can retrieve accurate, context-specific information from the graph.

Additionally, the system implements semantic search capabilities through an embedding-based similarity search module. By using OpenAI’s embedding models (e.g., "text-embedding-3-small"), the function `create_embedding` converts user inputs into dense vector representations. The `similarity_search` function then performs cosine similarity calculations within the Neo4j graph to retrieve contextually relevant nodes, complementing the traditional Cypher query approach. This hybrid retrieval method enhances the robustness of the system by enabling it to match on both explicit attributes and implicit semantic similarities. Furthermore, the code includes routines for vector indexing using `Neo4jVector`, which pre-indexes various entities (like Part, Model, Review, etc.) to accelerate similarity searches and improve overall query latency.

Finally, the overall application is wrapped in a FastAPI instance that configures essential middleware (including CORS and session management) and integrates the defined routers. This ensures that the system can handle real-time user interactions in a scalable and secure manner. In summary, the code demonstrates a sophisticated integration of modern AI techniques with graph database querying—a system that not only generates responses based on retrieval-augmented generation but also rigorously tracks conversation context, executes optimized queries, and provides confidence intervals for each answer. This design embodies state-of-the-art research in RAG, making it highly suitable for complex, context-aware chatbot applications.


## Scrape data from partsSelect
- cd ./partsSelect
- npm start

## Go to frontend
- cd ./frontend
- npm start 
// the server starts on localhost 3000

## Go to backend
- cd ./backend
- uvicorn main:app --reload
// the server starts on localhost 8000

## Neo4j 


<img width="1511" alt="Screenshot 2024-09-05 at 10 11 39 AM" src="https://github.com/user-attachments/assets/515c07ea-9cf8-413b-8a14-a9ace8398917">
<img width="1512" alt="Screenshot 2024-09-05 at 10 12 17 AM" src="https://github.com/user-attachments/assets/95215d34-543c-46a2-8d66-6e037ef3dcec">
