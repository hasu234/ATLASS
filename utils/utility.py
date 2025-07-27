import re
import os
import ast
import json
from dotenv import load_dotenv
from tiktoken import get_encoding

load_dotenv()

def extract_python_code(text: str) -> str:
    """Extracts Python code block from a given string."""
    match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
    return match.group(1) if match else ""

def extract_json(response: str):
    match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
    if match:
        json_content = match.group(1)
        try:
            return json.loads(json_content)
        except json.JSONDecodeError:
            return ""
    return ""

tool_dataset_dir = 'data/tool_config.json'
# Global cache to track updated tools
_updated_tools_cache = set()

def retrieve_tool(required_tool):
    with open(tool_dataset_dir, 'r') as file:
        tool_list = json.load(file) or []

    for i, tool_item in enumerate(required_tool):
        if tool_item['is_available']:
            # Get the name from the required tool
            name = tool_item['name']
            # If name is empty, try to find a tool with matching description
            if not name:
                for tool in tool_list:
                    if tool['description'].lower() == tool_item['description'].lower():
                        required_tool[i]['name'] = tool['name']
                        required_tool[i]['function'] = tool['function']
                        break
            else:
                # If name exists, try to find exact match first
                found = False
                for tool in tool_list:
                    if tool['name'].lower() == name.lower():
                        required_tool[i]['function'] = tool['function']
                        found = True
                        break
                
                # If no exact match found, try matching by description
                if not found:
                    for tool in tool_list:
                        if tool['description'].lower() == tool_item['description'].lower():
                            required_tool[i]['name'] = tool['name']
                            required_tool[i]['function'] = tool['function']
                            break

    return required_tool

def store_tool(state, i):
    # Use the global cache
    global _updated_tools_cache
    
    # Skip if index is invalid
    if i < 0 or i >= len(state['required_tools']):
        print(f"Invalid tool index: {i}")
        return
        
    with open(tool_dataset_dir, "r", encoding="utf-8") as file:
        try:
            tool_config = json.load(file)
        except json.JSONDecodeError:
            print("Error reading tool config, initializing empty list")
            tool_config = []
        
        # Get the tool to be added
        new_tool = state['required_tools'][i]
        
        # Skip if tool doesn't have a name
        if not new_tool.get('name'):
            print(f"Skipping unnamed tool at index {i}")
            return
            
        # Skip if tool doesn't have a function
        if not new_tool.get('function'):
            print(f"Skipping tool without function: {new_tool.get('name')}")
            return
            
        # Skip if we've already updated this tool in this session
        if new_tool.get('name') in _updated_tools_cache:
            print(f"Already updated tool in this session: {new_tool.get('name')}")
            return
            
        # Check if a tool with the same name already exists
        tool_exists = False
        for j, existing_tool in enumerate(tool_config):
            if existing_tool.get('name') == new_tool.get('name'):
                # Update the existing tool instead of adding a duplicate
                tool_config[j] = new_tool
                tool_exists = True
                print(f"Updating existing tool: {new_tool.get('name')}")
                _updated_tools_cache.add(new_tool.get('name'))
                break
        
        # Only append if the tool doesn't already exist
        if not tool_exists:
            tool_config.append(new_tool)
            print(f"Adding new tool: {new_tool.get('name')}")
            _updated_tools_cache.add(new_tool.get('name'))

    with open(tool_dataset_dir, "w", encoding="utf-8") as file:
        json.dump(tool_config, file, indent=4)


def extract_function_names(python_code: str):
    # Parse the code into an Abstract Syntax Tree (AST)
    tree = ast.parse(python_code)

    # Extract function names from AST nodes
    function_names = [
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    ]

    return function_names

file_path = 'temp/required_tools.py'

def prepare_tools(required_tools):
    function_names = []
    code_text = ''
    for tool in required_tools:
        function_names.append(extract_function_names(tool['function'])[0])
        code_text += tool['function'] + '\n'
    
    with open(file_path, "w") as file:
        file.write(code_text)
    return function_names