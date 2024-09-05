"""AI Agent to handle user queries and provide answers using a set of tools."""

import argparse
import json
from typing import Union
import re

from langchain.agents import Tool, AgentExecutor, AgentOutputParser, create_react_agent
from langchain.prompts import StringPromptTemplate
from langchain.schema import AgentAction, AgentFinish
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel


from graph_rag.config import GRAPH_ENTITIES
from graph_rag.queries.graph_query import query_db
from graph_rag.prompts import MEMORY_PARALLEL_PROMPT_TEMPLATE, MEMORY_SEQUENTIAL_PROMPT_TEMPLATE, PARALLEL_PROMPT_TEMPLATE, SEQUENTIAL_PROMPT_TEMPLATE
from graph_rag.queries.semantic_query import similarity_search


TOOLS = [
    Tool(name="Query", func=query_db, description="Use this tool to find entities in the user prompt that can be used to generate queries"),
    Tool(name="Similarity Search", func=similarity_search, description="Use this tool to perform a similarity search in the database"),
]

TOOL_NAMES = [f"{tool.name}: {tool.description}" for tool in TOOLS]


class CustomPromptTemplate(StringPromptTemplate):
    """Custom prompt template for the agent."""

    template: str

    def format(self, **kwargs) -> str:
        # Get the intermediate steps (AgentAction, Observation tuples)
        intermediate_steps = kwargs.pop("intermediate_steps")
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought: "

        # Set the agent_scratchpad variable to that value
        kwargs["agent_scratchpad"] = thoughts

        # Create a tools variable from the list of tools provided
        kwargs["tools"] = "\n".join([f"{tool.name}: {tool.description}" for tool in TOOLS])

        # Create a list of tool names for the tools provided
        kwargs["tool_names"] = ", ".join([tool.name for tool in TOOLS])
        kwargs["graph_entity_types"] = json.dumps(GRAPH_ENTITIES, indent=4)

        return self.template.format(**kwargs)


class CustomOutputParser(AgentOutputParser):
    """Custom output parser for the agent."""

    def parse(self, llm_output: str) -> Union[AgentAction, AgentFinish]:  # pylint: disable=arguments-renamed
        """Parse the LLM output and return an AgentAction or AgentFinish object."""

        # Check if agent should finish
        if "Final Answer:" in llm_output:
            return AgentFinish(
                # Return values is generally always a dictionary with a single `output` key
                # It is not recommended to try anything else at the moment :)
                return_values={"output": llm_output.split("Final Answer:")[-1].strip()},
                log=llm_output,
            )

        # Parse out the action and action input
        regex = r"Action: (.*?)[\n]*Action Input:[\s]*(.*)"
        match = re.search(regex, llm_output, re.DOTALL)

        # If it can't parse the output it raises an error
        # You can add your own logic here to handle errors in a different way i.e. pass to a human, give a canned response
        if not match:
            raise ValueError(f"Could not parse LLM output: `{llm_output}`")
        action = match.group(1).strip()
        action_input = match.group(2)

        # Return the action and action input
        return AgentAction(tool=action, tool_input=action_input.strip(" ").strip('"'), log=llm_output)


class CombinedQueryTool(Tool):
    """Tool to run Query and Similarity Search in parallel and return combined results."""

    def __init__(self):
        super().__init__(name="Combined Query Tool", func=self._run, description="Runs Query and Similarity Search in parallel and returns combined results.")  # Use the method defined in this class

    def _run(self, input):  # pylint: disable=arguments-differ, redefined-builtin
        # Implement the parallel execution
        parallel_chain = RunnableParallel({"query_result": query_db, "similarity_result": similarity_search})

        results = parallel_chain.invoke(input)
        # Combine the results as needed, e.g., concatenate, merge, etc.
        combined_results = results["query_result"] + results["similarity_result"]
        return combined_results

    async def _arun(self, input):  # pylint: disable=arguments-differ, redefined-builtin
        # If you need async handling, implement it here.
        raise NotImplementedError("CombinedQueryTool does not support async")


# You would then use CombinedQueryTool as one of the tools in your agent
PARALLEL_TOOLS = [
    CombinedQueryTool(),
    # Other tools if necessary
]


class Agent:
    """Base Agent class to handle the agent execution."""

    def __init__(self, tools, prompt_template):
        self.tools = tools
        self.prompt_template = prompt_template
        self.agent_executor = self._init_agent_executor()

    def _init_agent_executor(self) -> AgentExecutor:
        prompt = PromptTemplate(
            template=self.prompt_template,
        )
        llm = ChatOpenAI(temperature=0, model="gpt-4o")
        output_parser = CustomOutputParser()

        agent = create_react_agent(
            llm=llm,
            tools=self.tools,
            prompt=prompt,
            output_parser=output_parser,
            stop_sequence=["\nObservation:"],
        )

        agent_executor = AgentExecutor.from_agent_and_tools(agent=agent, tools=self.tools, verbose=True)
        return agent_executor

    def invoke(self, user_input: str) -> str:
        """Invoke the agent with the user input."""
        result = self.agent_executor.invoke({"input": user_input})
        return result["output"]


class SequentialAgent(Agent):
    """Sequential agent without memory."""

    def __init__(self):
        super().__init__(tools=TOOLS, prompt_template=SEQUENTIAL_PROMPT_TEMPLATE)


class MemorySequentialAgent(Agent):
    """Sequential agent with memory."""

    def __init__(self, memory=None):
        super().__init__(tools=TOOLS, prompt_template=MEMORY_SEQUENTIAL_PROMPT_TEMPLATE)
        self.memory = memory

    def invoke(self, user_input: str) -> str:
        """Invoke the agent with the user input and memory."""
        if self.memory:
            # Save the input in memory
            self.memory.save_context({"input": user_input}, {"output": ""})
            chat_history = self.memory.load_memory_variables({})["chat_history"]

            # Invoke with memory
            result = self.agent_executor.invoke({"input": user_input, "chat_history": chat_history})

            # Save the agent's response in memory (explicitly specifying the output key)
            self.memory.save_context({"input": user_input}, {"output": result["output"]})
        else:
            # Invoke without memory
            result = self.agent_executor.invoke({"input": user_input})

        return result["output"]


class ParallelAgent(Agent):
    """Parallel agent without memory."""

    def __init__(self):
        super().__init__(tools=PARALLEL_TOOLS, prompt_template=PARALLEL_PROMPT_TEMPLATE)


class MemoryParallelAgent(Agent):
    """Parallel agent with memory."""

    def __init__(self, memory: ConversationBufferMemory = None):
        super().__init__(tools=PARALLEL_TOOLS, prompt_template=MEMORY_PARALLEL_PROMPT_TEMPLATE)
        self.memory = memory

    def invoke(self, user_input: str) -> str:
        """Invoke the agent with the user input and memory."""
        if self.memory:
            # Save the input in memory
            self.memory.save_context({"input": user_input}, {"output": ""})
            chat_history = self.memory.load_memory_variables({})["chat_history"]

            # Invoke with memory
            result = self.agent_executor.invoke({"input": user_input, "chat_history": chat_history})

            # Save the agent's response in memory (explicitly specifying the output key)
            self.memory.save_context({"input": user_input}, {"output": result["output"]})
        else:
            # Invoke without memory
            result = self.agent_executor.invoke({"input": user_input})

        return result["output"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed entities in the Neo4j graph")
    parser.add_argument("--message", type=str, help="The message to send to the agent")
    parser.add_argument("--parallel", action="store_true", help="Whether to run the agent in parallel mode")
    parser.add_argument("--memory", action="store_true", help="Whether to include memory")
    args = parser.parse_args()

    if args.memory:
        # Simulate a conversation with memory
        test_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        test_memory.save_context({"input": "Hello, my name is John Doe"}, {"output": "Hello, John Doe"})

    if args.parallel:
        agent_exe = MemoryParallelAgent(memory=test_memory) if args.memory else ParallelAgent()
    else:
        agent_exe = MemorySequentialAgent(memory=test_memory) if args.memory else SequentialAgent()

    print(f"Using {'parallel' if args.parallel else 'sequential'} agent mode")
    print(f"\n\n--->Result: \n{agent_exe.invoke(args.message)}\n\n")
