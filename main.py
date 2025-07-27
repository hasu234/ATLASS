import sys
import json
import os
from dotenv import load_dotenv
from graph import graph

def print_banner(text, char='=', width=80):
    """Print a formatted banner with the given text"""
    print(f"\n{char * width}")
    print(f"{text.center(width)}")
    print(f"{char * width}\n")

def main():
    """
    Main function to run the agent with human-in-the-loop functionality
    """
    load_dotenv()
    
    # Get user query from command line or use a default one
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        print_banner("LLM Agent with Tool Generation", "=")
        print("This agent will analyze your query, generate and run tools to solve it.")
        print("You will be asked to approve each tool before it is executed.")
        print("\nType your query below or press Ctrl+C to exit.")
        user_query = input("\nQuery: ")
    
    print_banner(f"EXECUTING QUERY: {user_query}", "=")
    print("Step 1: Analyzing the task")
    print("Step 2: Identifying required tools")
    print("Step 3: Generating tool code")
    print("Step 4: Human review of generated tools")
    print("Step 5: Executing tools and solving task")
    print("\nStarting execution...")
    
    # Create a unique thread ID
    thread_id = f"thread_{os.urandom(4).hex()}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Track whether tools were used
    tools_used = False
    tools_approved = False
    
    # Start the graph execution with streaming to handle interruptions
    stream = graph.stream({"messages": [user_query], "max_turns": 5}, config, stream_mode="values")
    
    response = None
    
    try:
        for output in stream:
            # If output is None, the graph was interrupted for human input
            if output is None:
                print_banner("TOOL REVIEW REQUIRED", "!")
                print("A tool has been generated and requires your approval.")
                print("Please review the code carefully before approving.")
                
                while True:
                    choice = input("\nDo you approve this tool? (yes/no): ").strip().lower()
                    if choice in ["yes", "y"]:
                        feedback = input("Optional feedback for the system: ")
                        human_input = {"human_approved": True, "human_feedback": feedback}
                        tools_approved = True
                        break
                    elif choice in ["no", "n"]:
                        feedback = input("Please provide feedback on why you rejected the tool: ")
                        human_input = {"human_approved": False, "human_feedback": feedback}
                        break
                    else:
                        print("Invalid input. Please enter 'yes' or 'no'.")
                
                print_banner("RESUMING EXECUTION", "-")
                if tools_approved:
                    print("✓ Tool approved! The agent will now execute this tool to solve your task.")
                else:
                    print("✗ Tool rejected. The agent will try to regenerate or find an alternative approach.")
                    
                # Resume the graph with human input
                resume_stream = graph.stream(human_input, config, stream_mode="values")
                for resume_output in resume_stream:
                    if resume_output is not None:
                        response = resume_output
            else:
                response = output
                
            # Print progress updates based on current state
            if output and isinstance(output, dict):
                # Mark tool generation success
                if output.get('code_generation_success') and not tools_used:
                    print("✓ Code generation completed successfully")
                    tools_used = True
                
                # Print current stage if available
                for key in output.keys():
                    if key == 'task_analyzer_complete':
                        print("✓ Task analysis completed")
                    elif key == 'tools_identified' and not tools_used:
                        print("✓ Required tools identified")
                    elif key == 'tools_generated' and not tools_used:
                        print("✓ Tools generated")
                    elif key == 'tools_executed':
                        print("✓ Tools executed successfully")
                        tools_used = True
                        
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user.")
        return
    except Exception as e:
        print(f"\n\nAn error occurred during execution: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Print the final result
    if response and 'messages' in response:
        print_banner("SOLUTION", "=")
        
        # Get the last message as the answer
        last_msg = None
        
        # Try to find the last message with content
        if isinstance(response['messages'], list):
            # Go through messages in reverse to find the latest content
            for msg in reversed(response['messages']):
                if hasattr(msg, 'content') and msg.content:
                    last_msg = msg.content
                    break
                elif isinstance(msg, dict) and 'content' in msg:
                    last_msg = msg['content']
                    break
                elif isinstance(msg, str):
                    last_msg = msg
                    break
                    
        if not last_msg and len(response['messages']) > 0:
            # If we didn't find content above, check the last message directly
            last_item = response['messages'][-1]
            if hasattr(last_item, 'content'):
                last_msg = last_item.content
            elif isinstance(last_item, dict) and 'content' in last_item:
                last_msg = last_item['content']
            elif isinstance(last_item, str):
                last_msg = last_item
                
        # Print the answer if we found one
        if last_msg:
            print(last_msg)
        else:
            print("No solution was generated. Please try again with a different query.")
        
        # Print tool execution confirmation
        if tools_used and tools_approved:
            print("\n✓ The solution was generated using custom-built and executed tools.")
        elif tools_used:
            print("\n✓ Tools were generated but may not have been fully executed.")
        else:
            print("\n⚠️ No tools were executed to solve this task.")

if __name__ == "__main__":
    main() 