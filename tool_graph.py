from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
import utils.nodes as nodes
import utils.schema as schema
import utils.router as router
from dotenv import load_dotenv
import os

load_dotenv()

# Create memory saver for checkpointing
memory = MemorySaver()

# Create the graph builder
graph_builder = StateGraph(schema.State)

# Define nodes
graph_builder.add_node('task_analyzer', nodes.task_analyzer_agent)
graph_builder.add_node('tool_master', nodes.tool_master_agent)
graph_builder.add_node('tool_selector', nodes.tool_selector_agent)
graph_builder.add_node('tool_generator', nodes.tool_generator_agent)
graph_builder.add_node('human_approval', nodes.human_approval_agent)
graph_builder.add_node('task_solver', nodes.task_solver)

# Define edges
graph_builder.add_edge(START, "task_analyzer")
graph_builder.add_edge('task_analyzer', "tool_master")
graph_builder.add_edge('tool_master', "tool_selector")

# Add conditional routing
graph_builder.add_conditional_edges(
    "tool_selector", 
    router.router_tool_selector,
    ['tool_generator', 'task_solver']
)

# Add human-in-the-loop edge
graph_builder.add_edge('tool_generator', "human_approval")
graph_builder.add_edge('human_approval', "task_solver")
graph_builder.add_edge('task_solver', END)

# Compile the graph with interruption for human approval
graph = graph_builder.compile(
    checkpointer=memory,
    interrupt_before=["human_approval"]
)

# Example usage (when running this file directly)
if __name__ == "__main__":
    # Create a unique thread ID
    thread_id = "example_thread"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Test question
    user_query = "Extract all email addresses from this text: 'Contact us at support@example.com or sales@example.org for more information.'"
    
    # Start the graph execution
    print("Starting graph execution with query:", user_query)
    stream = graph.stream({"messages": [user_query], "max_turns": 3}, config, stream_mode="values")
    
    # Process the stream
    for output in stream:
        # If output is None, the graph was interrupted for human input
        if output is None:
            print("\n=== HUMAN APPROVAL REQUIRED ===")
            print("A tool has been generated and requires your approval.")
            
            while True:
                choice = input("Do you approve this tool? (yes/no): ").strip().lower()
                if choice in ["yes", "y"]:
                    feedback = input("Optional feedback for the system: ")
                    human_input = {"human_approved": True, "human_feedback": feedback}
                    break
                elif choice in ["no", "n"]:
                    feedback = input("Please provide feedback on why you rejected the tool: ")
                    human_input = {"human_approved": False, "human_feedback": feedback}
                    break
                else:
                    print("Invalid input. Please enter 'yes' or 'no'.")
            
            # Resume the graph with human input
            resume_stream = graph.stream(human_input, config, stream_mode="values")
            for resume_output in resume_stream:
                if resume_output is not None:
                    # Print final messages
                    if 'messages' in resume_output:
                        print("\n=== FINAL RESULT ===")
                        for msg in resume_output['messages']:
                            if hasattr(msg, 'content'):
                                print(msg.content)
        else:
            # Print any other outputs
            if 'messages' in output:
                print("\n=== FINAL RESULT ===")
                for msg in output['messages']:
                    if hasattr(msg, 'content'):
                        print(msg.content)

