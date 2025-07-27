import os
import utils.prompts as ctg
import utils.schema as schema
from dotenv import load_dotenv
import utils.utility as utility
from utils.localllm import LocalChatModel
from langchain_core.messages import SystemMessage
from utils.utility import retrieve_tool, store_tool
import json

load_dotenv()
llm_model = os.getenv("LLM_MODEL")

# Replace ChatOpenAI with our DeepSeekChatModel
llm = LocalChatModel(
    api_url="http://10.10.10.104:11434/api/generate",
    # model_name="deepseek-r1:671b",
    model_name=llm_model,
    temperature=0
)

def task_analyzer_agent(state:schema.State):
    system_message = ctg.task_analyzer_system_prompt
    
    # Get user query for context
    user_query = ""
    for msg in state.get("messages", []):
        if isinstance(msg, str):
            user_query = msg
            break
        elif hasattr(msg, "content") and isinstance(msg.content, str):
            user_query = msg.content
            break
    
    # Add a reminder to be minimal in the system message
    enhanced_prompt = f"{system_message}\n\nREMINDER: For this query: '{user_query}', provide only the ABSOLUTE MINIMUM number of subtasks needed (1-2 ideally)."
    
    messages = [SystemMessage(content=enhanced_prompt)]+state["messages"]
    response = llm.invoke(messages)
    
    print("------------- TASK ANALYZER START --------------")
    print("Task Analyzer Response: ", response.content)
    print("------------- TASK ANALYZER END --------------")
    
    # Post-process the response to ensure minimalism
    subtasks = response.content.strip().split('\n')
    if len(subtasks) > 3:
        print(f"Too many subtasks ({len(subtasks)}). Consolidating...")
        
        # If there are data fetch + visualization tasks, combine them
        has_data_task = any('data' in t.lower() or 'fetch' in t.lower() or 'api' in t.lower() for t in subtasks)
        has_viz_task = any('visual' in t.lower() or 'chart' in t.lower() or 'graph' in t.lower() or 'plot' in t.lower() for t in subtasks)
        
        if has_data_task and has_viz_task:
            # Create one consolidated task that combines data fetching and visualization
            consolidated_tasks = ["1. Fetch and visualize the required data to address the query."]
            for t in subtasks:
                if not ('data' in t.lower() or 'fetch' in t.lower() or 'visual' in t.lower() or 'chart' in t.lower()):
                    # Keep other unrelated tasks
                    consolidated_tasks.append(t)
            
            # Limit to maximum 3 tasks
            consolidated_tasks = consolidated_tasks[:3]
            response.content = '\n'.join(consolidated_tasks)
            print("Consolidated tasks: ", response.content)
    
    return {"messages": [response]}

def tool_master_agent(state:schema.State):
    print("------------- TOOL MASTER START --------------")
    print("Tool Master Request [-1]: ", state["messages"][-1].content)
    system_message = ctg.tool_master_system_prompt
    messages = [SystemMessage(content=system_message)]+[state["messages"][-1].content]
    response = llm.invoke(messages)
    print("Tool Master Response: ", response.content)
    print("------------- TOOL MASTER END --------------")
    return {"messages": [response]}


def tool_selector_agent(state:schema.State):
    print("------------- TOOL SELECTOR START --------------")
    print("Tool Selector Request: ", state["messages"][-1].content)
    
    # If tools have already been executed, don't reprocess
    if state.get('tools_executed', False):
        print("Tools already executed, bypassing tool selection")
        return {"messages": state.get("messages", []), 'required_tools': state.get('required_tools', [])}
        
    # Check if we are coming back after human approval
    if state.get('human_approved', False):
        print("Human has approved tools, continuing with existing tools")
        return {"messages": state.get("messages", []), 'required_tools': state.get('required_tools', [])}
        
    system_message = ctg.tool_selector_system_prompt
    messages = [SystemMessage(content=system_message)]+[state["messages"][-1].content]
    print("Tool Selector System Message prepared")
    
    # Get tool selection from LLM
    response = llm.invoke(messages)
    print("Tool Selector Response: ", response.content)
    
    # Extract tools from response
    try:
        required_tool = utility.extract_json(response.content)
        if not required_tool:
            print("Failed to extract JSON from response, using regex fallback")
            # Try to extract using regex as fallback
            import re
            json_pattern = r'\[\s*{.*?}\s*\]'
            json_match = re.search(json_pattern, response.content, re.DOTALL)
            if json_match:
                try:
                    required_tool = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    print("Regex JSON extraction failed")
    except Exception as e:
        print(f"Error extracting tools: {str(e)}")
        required_tool = []
    
    # Ensure we have a valid list of tools
    if not required_tool:
        print("No tools identified, initializing empty tool list")
        required_tool = []
    elif not isinstance(required_tool, list):
        print("Converting non-list tool to list")
        required_tool = [required_tool]
    
    # Check for and remove duplicate tools by name
    unique_tools = []
    tool_names = set()
    for tool in required_tool:
        if tool.get('name') and tool['name'] in tool_names:
            print(f"Skipping duplicate tool: {tool['name']}")
            continue
        if tool.get('name'):
            tool_names.add(tool['name'])
        unique_tools.append(tool)
    
    if len(unique_tools) < len(required_tool):
        print(f"Removed {len(required_tool) - len(unique_tools)} duplicate tools")
        required_tool = unique_tools
    
    # Enforce tool efficiency: limit to a maximum of 3 tools
    if len(required_tool) > 3:
        print(f"Too many tools ({len(required_tool)}). Limiting to 3 most important tools.")
        # Prioritize API tools and visualization tools as they're more likely to be essential
        api_tools = [tool for tool in required_tool if any(k in tool.get('name', '').lower() for k in ['api', 'fetch', 'http'])]
        viz_tools = [tool for tool in required_tool if any(k in tool.get('name', '').lower() for k in ['visual', 'plot', 'chart'])]
        other_tools = [tool for tool in required_tool if tool not in api_tools and tool not in viz_tools]
        
        # Prioritize in order: API tools, visualization tools, then others
        prioritized_tools = api_tools + viz_tools + other_tools
        required_tool = prioritized_tools[:3]
        print(f"Selected these tools: {[tool.get('name', 'unnamed') for tool in required_tool]}")
    
    # Retrieve tool implementations if available
    if required_tool:
        print(f"Found {len(required_tool)} required tools")
    required_tool = retrieve_tool(required_tool)

    print("Required Tools: ", required_tool)
    print("------------- TOOL SELECTOR END --------------")

    # Return with tools_identified flag
    return {
        "messages": [response], 
        'required_tools': required_tool,
        'tools_identified': True
    }

tool_dataset_dir = 'data/tool_config.json'


def tool_generator_agent(state:schema.ToolState):
    print("------------- TOOL GENERATOR START --------------")
    print("Tool Generator Request: ", state["messages"][-1].content)
    
    # Get the original user query for context
    user_query = ""
    for msg in state.get("messages", []):
        if hasattr(msg, "content") and isinstance(msg.content, str):
            user_query = msg.content
            break
    
    # Check if human approval has been provided
    if 'human_approved' in state:
        if not state['human_approved']:
            # Human rejected the tool, so we need to regenerate it
            print(f"Tool rejected by human. Feedback: {state.get('human_feedback', 'None provided')}")
            # Reset success state to allow regeneration
            state['code_generation_success'] = False
            # Adjust max_turns to prevent infinite attempts
            if state['max_turns'] > 0:
                state['max_turns'] -= 1
    
    # Check if we've already succeeded
    if state.get('code_generation_success', False):
        return state

    # Ensure required_tools exists in state
    if 'required_tools' not in state:
        state['required_tools'] = [{
            'name': state['messages'][-1].content.get('name', ''),
            'description': state['messages'][-1].content.get('description', ''),
            'is_available': False,
            'function': None
        }]
    
    # Keep track of processed tools to prevent duplicates
    processed_tools = set()
    
    # Process each tool
    for i, tool in enumerate(state['required_tools']):
        # Skip already processed tools in this run
        if tool.get('name') and tool['name'] in processed_tools:
            print(f"Skipping already processed tool in this run: {tool['name']}")
            continue
            
        if not tool['is_available']:
            # Add context about the user query
            enhanced_description = f"{tool['description']}\n\nThis tool will be used to solve the following user query: '{user_query}'"
            
            # Check if this is an API-based tool
            if any(keyword in tool['name'].lower() for keyword in ['api', 'web', 'http', 'rest']):
                # Use web scraper for API tools
                from scraper.scrape import APICodeAgent
                scraper = APICodeAgent()
                code = scraper.generate_api_code(enhanced_description)
                
                if code and code != "no code found":
                    # Ensure the code has placeholders for customization
                    if 'API_KEY' not in code and 'YOUR_API_KEY' not in code:
                        code = code.replace("api_key = ", "API_KEY = 'YOUR_API_KEY'\napi_key = API_KEY")
                    
                    # Only update and store if the tool's function has changed
                    if state['required_tools'][i]['function'] != code:
                        state['required_tools'][i]['is_available'] = True
                        state['required_tools'][i]['function'] = code
                        store_tool(state, i)
                        
                    state['code_generation_success'] = True
                    state['tools_generated'] = True
                    
                    # Mark tool as processed
                    if tool.get('name'):
                        processed_tools.add(tool['name'])
                else:
                    state['max_turns'] -= 1
            else:
                # Use non-API based code writer prompt for non-API tools
                system_message = ctg.non_api_based_code_writer_system_prompt
                
                # Create a detailed tool request with user query context
                tool_request = {
                    'name': tool['name'],
                    'description': enhanced_description,
                    'user_query': user_query
                }
                
                messages = [SystemMessage(content=system_message)] + [str(tool_request)]
                response = llm.invoke(messages)
                
                # Extract Python code from the response
                code_block = utility.extract_python_code(response.content)
                
                if code_block:
                    state['required_tools'][i]['is_available'] = True
                    state['required_tools'][i]['function'] = code_block

                    store_tool(state, i)

                    state['code_generation_success'] = True
                    state['tools_generated'] = True
                    
                    
                    # Mark tool as processed
                    if tool.get('name'):
                        processed_tools.add(tool['name'])
                else:
                    state['max_turns'] -= 1
                
    result = {
        'messages': state['messages'], 
        'required_tools': state['required_tools'], 
        'max_turns': state['max_turns'], 
        'code_generation_success': state['code_generation_success'],
        'tools_generated': state.get('tools_generated', False),
        # Preserve human feedback if present
        'human_approved': state.get('human_approved', False),
        'human_feedback': state.get('human_feedback', '')
    }   
    print("Tool Generator Response: ", result)
    print("------------- TOOL GENERATOR END --------------")
    return result

def code_writer(state:schema.ToolState):
    print("------------- CODE WRITER START --------------")
    print("Code Writer Request: ", state["messages"][-1].content)
    # Check if we've already succeeded or run out of turns
    if state.get('code_generation_success', False):
        return state
        
    if state['max_turns'] <= 0:
        return {
            "messages": [
                "Maximum number of code generation attempts reached. Please review the process or try a different approach."
            ],
            'max_turns': 0,
            'code_generation_success': False
        }
    
    # Use non-API based code writer prompt for all non-API tools
    system_message = ctg.non_api_based_code_writer_system_prompt
    messages = [SystemMessage(content=system_message)] + [state["messages"][0].content]
    response = llm.invoke(messages)

    # Extract Python code from the response
    code_block = utility.extract_python_code(response.content)
    print("Code Writer Response: ", response.content)
    print("Code Block: ", code_block)
    print("------------- CODE WRITER END --------------")
    
    # If we found valid Python code, mark as successful
    if code_block:
        return {
            "messages": [response],
            'max_turns': state['max_turns'],
            'code_generation_success': True
        }
    
    # If no valid code found, decrement turns and continue
    return {
        "messages": [response],
        'max_turns': state['max_turns'] - 1,
        'code_generation_success': False
    }


def task_solver(state: schema.State):
    print("------------- TASK SOLVER START --------------")
    print("Task Solver Request state[message]: ", state["messages"][-1].content)
    print("Task Solver Required Tools state[required_tools]: ", state['required_tools'])
    
    # Check if we have the required tools
    if not state.get('required_tools'):
        return {
            "messages": [
                "No tools available to solve the task. Please ensure tools are properly configured."
            ],
            'required_tools': [],
            'max_turns': state['max_turns']
        }
    
    # Get the original user query from the first message
    user_query = ""
    for msg in state.get("messages", []):
        if isinstance(msg, str):
            user_query = msg
            break
        elif hasattr(msg, "content") and isinstance(msg.content, str):
            user_query = msg.content
            break
    
    print("User Query: ", user_query)
    
    # Import necessary modules
    import sys
    import os
    import subprocess
    import re
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    from utils.localllm import LocalChatModel  # Adjust import path as needed
    
    # Create a directory for tool execution if it doesn't exist
    if not os.path.exists('temp'):
        os.makedirs('temp')
    
    print(f"Found {len(state['required_tools'])} tools to execute")
    
    # Convert the required tools into executable Python functions
    tool_functions = []
    for i, tool in enumerate(state['required_tools']):
        if not tool.get('is_available', False) or not tool.get('function'):
            continue
            
        print(f"Processing tool {i+1}: {tool.get('name', 'unnamed')}")
        
        try:
            # Get tool code and handle API keys
            tool_code = tool['function']
            
            # Handle API key replacements and user query injection as before
            # [Your existing API key replacement code here]
            
            # Create a wrapper function that executes the tool code
            def create_tool_function(tool_name, tool_code, i):
                def wrapper_function(*args, **kwargs):
                    # Save the tool code to a temporary file
                    tool_filename = f"temp/tool_{i}.py"
                    with open(tool_filename, 'w') as f:
                        f.write(tool_code)
                    
                    # Append arguments to the file if needed
                    args_code = ""
                    if args or kwargs:
                        args_code = "\n\n# Arguments passed to the tool\n"
                        if args:
                            args_code += f"# Positional args: {args}\n"
                        if kwargs:
                            for k, v in kwargs.items():
                                args_code += f"{k} = {repr(v)}\n"
                        with open(tool_filename, 'a') as f:
                            f.write(args_code)
                    
                    # Execute the tool and capture its output
                    result = subprocess.run(
                        [sys.executable, tool_filename],
                        capture_output=True,
                        text=True,
                        timeout=60  # Add timeout to prevent hanging
                    )
                    
                    if result.returncode == 0:
                        return result.stdout.strip()
                    else:
                        return f"Error: {result.stderr}"
                
                # Add attributes needed for bind_tools to work
                wrapper_function.__name__ = tool['name']
                wrapper_function.__doc__ = f"Execute the {tool['name']} tool to solve the task."
                
                return wrapper_function
            
            # Create a unique function for this tool
            tool_function = create_tool_function(tool['name'], tool_code, i)
            tool_functions.append(tool_function)
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Exception preparing tool {tool['name']}: {str(e)}")
            print(f"Error trace: {error_trace}")
    
    # Prepare the system message
    system_content = f"""You are a task solver that executes the necessary tools to solve user queries. 
    
    User query: "{user_query}"
    
    Tools are available to help solve this query. Use these tools when needed to get information or perform actions.
    
    IMPORTANT: Respond as if you personally solved the task, not as if you're presenting tool results.
    """
    
    # Initialize the LLM
    llm = LocalChatModel()
    
    # Bind the tools to the LLM
    llm_with_tools = llm.bind_tools(tool_functions)
    
    # Create the messages
    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_query)
    ]
    
    # Get the response using the tool-enabled LLM
    response = llm_with_tools.invoke(messages)
    print("Task Solver generated a response using the bound tools")
    
    # Update the state with the response
    state['messages'].append(response)
    state['tools_executed'] = True

    print("------------- TASK SOLVER END --------------")
    return state

def human_approval_agent(state:schema.ToolState):
    """
    Human-in-the-loop node to approve or reject generated tools.
    This function will be interrupted by LangGraph when using interrupt_before,
    allowing for manual intervention.
    """
    print("------------- HUMAN APPROVAL START --------------")
    print("\nTOOL FOR APPROVAL")
    print("====================")
    
    # Extract tool information for display
    tools_for_approval = []
    for i, tool in enumerate(state.get('required_tools', [])):
        # Only show tools that have been generated but not yet approved
        if tool.get('is_available', False) and tool.get('function') and not state.get('human_approved', False):
            # Check if tool requires API key
            requires_api_key = 'YOUR_API_KEY' in tool.get('function', '') or 'API_KEY' in tool.get('function', '')
            
            tools_for_approval.append({
                'index': i,
                'name': tool.get('name', 'Unnamed Tool'),
                'description': tool.get('description', 'No description'),
                'function_code': tool.get('function', 'No function code available'),
                'requires_api_key': requires_api_key
            })
    
    # Print tool info for human review
    if tools_for_approval:
        for tool in tools_for_approval:
            print(f"\n--- TOOL: {tool['name']} ---")
            print(f"DESCRIPTION: {tool['description']}")
            
            if tool.get('requires_api_key', False):
                print("\n⚠️  NOTE: This tool requires an API key! ⚠️")
                print("  You will be prompted to enter it during execution")
            
            print("\nCODE:")
            print("-" * 80)
            # Print code with line numbers for better readability
            for i, line in enumerate(tool['function_code'].split('\n')):
                print(f"{i+1:4d} | {line}")
            print("-" * 80)
            
            # Give instructions for API tools
            if tool.get('requires_api_key', False):
                print("\nThis tool uses an API that requires authentication.")
                print("If you approve this tool, you'll need to provide your API key when prompted.")
    else:
        print("No tools available for approval currently.")
    
    # The actual approval will happen when the graph is interrupted
    # and then resumed with human input
    
    # If we have human approval status, print it
    if 'human_approved' in state:
        print(f"\nHuman approval status: {'APPROVED' if state['human_approved'] else 'REJECTED'}")
        if state.get('human_feedback'):
            print(f"Feedback: {state['human_feedback']}")
        
        # Flag to ensure execution after approval
        if state['human_approved']:
            print("\nTools approved! Proceeding to execute tools...")
            state['proceed_to_execution'] = True
    
    print("\n------------- HUMAN APPROVAL END --------------")
    # Return the state with human approval information preserved
    return {
        'messages': state.get('messages', []),
        'required_tools': state.get('required_tools', []),
        'max_turns': state.get('max_turns', 3),
        'code_generation_success': state.get('code_generation_success', False),
        'tools_generated': state.get('tools_generated', False),
        'human_approved': state.get('human_approved', False),
        'human_feedback': state.get('human_feedback', ''),
        'proceed_to_execution': state.get('human_approved', False)
    }