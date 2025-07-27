import utils.schema as schema
from langgraph.graph import END


def router_tool_generator(state:schema.ToolState):
    """Route between question and answer"""
    messages = state["messages"][-1]
    if state['max_turns'] == 0:
        # print('MAXIMUM TURNS HAVE BEEN REACHED')
        return END

    # Check if we need to validate API code
    if isinstance(messages, dict) and 'execution_output' in messages:
        if messages.get('api_key_used', False):
            print("API key was successfully used in the execution.")
        return 'task_solver'
    
    # Check if we need to generate API code
    if "name =" in messages.content and "query =" in messages.content:
        # Check if API key is already in state
        if not state.get('api_key'):
            print("Note: This tool requires an API key. You will be prompted to enter it when the code is executed.")
        return 'api_documentation_pipeline'
    elif 'TERMINATE' in messages.content:
        return END
    else:
        return 'python_interpreter'
    
def router_tool_selector(state:schema.State):
    """Route between tool generator and task solver based on tool availability"""
    print("ROUTER CHECKING TOOLS: ", state.get("required_tools", []))
    
    # If human has approved and tools are available, go to task solver
    if state.get('human_approved', False):
        tools_available = any(tool.get('is_available', False) for tool in state.get('required_tools', []))
        if tools_available:
            print("Tools have been approved, routing to task solver")
            return 'task_solver'
    
    # If there are no required tools, go directly to task solver
    if not state.get("required_tools"):
        print("No tools required, going to task solver")
        return 'task_solver'
    
    # Check for tools that need to be generated
    unavailable_tools = [tool for tool in state.get("required_tools", []) if not tool.get('is_available', False)]
    print("Unavailable Tools: ", unavailable_tools)

    if unavailable_tools:
        print("Some tools need to be generated, routing to tool generator")
        return 'tool_generator'
    else:
        # All tools are available, proceed to task solver
        print("All tools are available, routing to task solver")
        return 'task_solver'
        