import json
import os
import traceback
from tqdm import tqdm
from langgraph.graph import StateGraph, START, END
import utils.nodes as nodes
import utils.schema as schema
import utils.router as router
from dotenv import load_dotenv

def load_checkpoint(checkpoint_file):
    """
    Load checkpoint file to resume processing
    """
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return None

def save_checkpoint(checkpoint_file, results, current_index):
    """
    Save checkpoint with current results and processing index
    """
    checkpoint_data = {
        'results': results,
        'current_index': current_index
    }
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f, indent=4)

def handle_human_approval(config, thread_id):
    """
    Handle human approval during graph interruption
    
    Returns:
        dict: A dictionary with human approval decision and feedback
    """
    print("\n=== HUMAN APPROVAL REQUIRED ===")
    print("A tool has been generated and requires your approval.")
    
    while True:
        choice = input("Do you approve this tool? (yes/no): ").strip().lower()
        if choice in ["yes", "y"]:
            feedback = input("Optional feedback for the system: ")
            return {"human_approved": True, "human_feedback": feedback}
        elif choice in ["no", "n"]:
            feedback = input("Please provide feedback on why you rejected the tool: ")
            return {"human_approved": False, "human_feedback": feedback}
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

def perform_inference(graph, json_file, checkpoint_file='inference_checkpoint.json', resume=True):
    # Load environment variables
    load_dotenv()

    # Compile the graph
    atlass = graph

    # Check for existing checkpoint
    checkpoint = load_checkpoint(checkpoint_file) if resume else None
    
    # Determine starting point
    start_index = checkpoint['current_index'] + 1 if checkpoint else 0
    result = checkpoint['results'] if checkpoint else []

    # Read input data
    with open(json_file) as f:
        data = f.readlines()

    # Process data with resumable checkpoint
    try:
        for i in tqdm(range(start_index, len(data)), initial=start_index, total=len(data)):
            line = data[i]
            try:
                parsed_data = json.loads(line)
                question = parsed_data["question"]
                gt = parsed_data["answer"]

                print(f"Processing Question {i+1}: {question}")
                
                # Create a unique thread ID for this question
                thread_id = f"thread_{i}"
                config = {"configurable": {"thread_id": thread_id}}
                
                # Start the graph execution
                response = None
                
                # Initial invocation
                stream = atlass.stream({"messages": [question], "max_turns": 3}, config, stream_mode="values")
                
                try:
                    # Process the stream
                    for output in stream:
                        # If we get None, it means the graph was interrupted
                        if output is None:
                            print("Graph interrupted, waiting for human input...")
                            
                            # Get human approval input
                            human_input = handle_human_approval(config, thread_id)
                            
                            # Resume the graph with the human input
                            resume_stream = atlass.stream(human_input, config, stream_mode="values")
                            for resume_output in resume_stream:
                                if resume_output is not None:
                                    response = resume_output
                        else:
                            response = output
                except Exception as e:
                    print(f"Error in stream processing: {e}")
                    traceback.print_exc()
                
                if response:
                    # Prepare result item
                    result_item = {
                        "question": question,
                        "correct_answer": gt,
                        "answer": response['messages'][-1].content
                    }
                    result.append(result_item)

                    # Save checkpoint after each successful processing
                    save_checkpoint(checkpoint_file, result, i)

            except Exception as inner_error:
                print(f"Error processing line {i}: {inner_error}")
                traceback.print_exc()
                # Optionally, you can choose to continue or break based on your requirements
                continue

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        # Save final results
        with open("ATLASS_FINAL_RESULT_CRAFT.json1111", "w") as f:
            json.dump(result, f, indent=4)

    return result

# Main execution
if __name__ == "__main__":
    # Import the graph from graph.py
    from graph import graph
    
    json_file = "inference-data/CRAFT_ALL_DATA.jsonl1111"
    
    # First run
    results = perform_inference(graph, json_file, resume=True)
    
    print("Inference completed successfully!")