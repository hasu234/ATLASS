from langgraph.graph import StateGraph, START, END
import utils.nodes as nodes
import utils.schema as schema
import utils.router as router
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

# Create a memory saver for checkpointing
memory = MemorySaver()

# Build the graph with improved structure
graph = StateGraph(schema.State)

# Add nodes
graph.add_node('task_analyzer', nodes.task_analyzer_agent)
graph.add_node('tool_master', nodes.tool_master_agent)
graph.add_node('tool_selector', nodes.tool_selector_agent)
graph.add_node('tool_generator', nodes.tool_generator_agent)
graph.add_node('human_approval', nodes.human_approval_agent)
graph.add_node('task_solver', nodes.task_solver)

# Connect the graph
graph.add_edge(START, "task_analyzer")
graph.add_edge('task_analyzer', "tool_master")
graph.add_edge('tool_master', "tool_selector")

# Add conditional routing from tool selector
graph.add_conditional_edges(
    "tool_selector", 
    router.router_tool_selector, 
    ['tool_generator', 'task_solver']
)

# Add human approval after tool generation
graph.add_edge('tool_generator', "human_approval")

# After human approval, go back to tool selector to check if all tools are available
graph.add_edge('human_approval', "tool_selector")

# Add direct path to task solver if needed
graph.add_edge('human_approval', "task_solver")

# Complete the task with available tools
graph.add_edge('task_solver', END)

# Compile the graph with human-in-the-loop at the human_approval node
graph = graph.compile(
    checkpointer=memory,
    interrupt_before=["human_approval"]  # Interrupt before human approval
)

# display(Image(graph.get_graph().draw_mermaid_png()))

# user_query = """Extract all email addresses from this text: 'Contact us at support@example.com or sales@example.org for more information.'. After extracting the email addresses,reverse those strings. And after that convert all charecters in that string into uppercase and give me that final output"""
# # user_query = "Find who is the current president of Bangladesh is"
# user_query = "Perform addition of 5 and 19"
user_query = """Extract all email addresses from this text: 'Contact us at support@example.com or sales@example.org for more information.'"""
# user_query = """Given the following daily stock prices, calculate the 3-day and 5-day moving averages and generate a plot overlaying these on the price chart."""

# Example usage when running this file directly
if __name__ == "__main__":
    # user_query = "Get the last 10 days stock price of Meta and visualize it."
    
    # Create a config with a thread_id (required by the checkpointer)
    config = {"configurable": {"thread_id": "example_thread"}}
    
    # Use the stream method to properly handle interrupts
    stream = graph.stream({"messages": [user_query], "max_turns": 2}, config, stream_mode="values")
    
    response = None
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
                    response = resume_output
        else:
            response = output
    
    # Print results at the end
    if response and 'messages' in response:
        print("\n=== FINAL RESULT ===")
        for msg in response['messages']:
            if hasattr(msg, 'content'):
                print(msg.content)