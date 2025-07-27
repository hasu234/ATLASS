import subprocess
import re
from dotenv import load_dotenv
import utils.schema as schema
import utils.utility as utility
from langgraph.graph import END
import langchain_community.tools
from scraper.scrape import APICodeAgent
load_dotenv()

def api_documentation_pipeline(state:schema.ToolState):
    """Pipeline to handle API documentation retrieval and code generation"""
    query = state.get('search_query', '')
    api_name = state.get('api_name', '')
    api_key = state.get('api_key', None)
    
    if not query or not api_name:
        return {"context": ["Missing search query or API name"]}
    
    try:
        # Initialize the API code agent
        scraper = APICodeAgent()
        
        # Generate code using the scraper
        code = scraper.generate_api_code(query)
        
        if code and code != "no code found":
            # Create a temporary state for the interpreter
            interpreter_state = schema.ToolState(
                messages=[{"content": f"```python\n{code}\n```"}],
                max_turns=state.get('max_turns', 3),
                code_generation_success=False,
                api_key=api_key  # Pass the API key to the interpreter state
            )
            
            # Validate the generated code using the interpreter
            interpreter_result = python_interpreter(interpreter_state)
            
            if interpreter_result['code_generation_success']:
                return {
                    "messages": [code],
                    'code_generation_success': True,
                    'execution_output': interpreter_result['messages'][0],
                    'api_key_used': True  # Indicate that API key was used
                }
            else:
                return {
                    "messages": [f"Generated code failed validation: {interpreter_result['messages'][0]}"],
                    'code_generation_success': False
                }
        else:
            return {
                "messages": ["Failed to generate API code"],
                'code_generation_success': False
            }
    except Exception as e:
        return {
            "messages": [f"Error in API documentation pipeline: {str(e)}"],
            'code_generation_success': False
        }

# Define the file path where the Python script will be written
SCRIPT_PATH = "temp/generated_script.py"

def python_interpreter(state:schema.ToolState):
    # Extract Python code from the message
    python_code = re.findall(r"```python(.*?)```", state["messages"][-1].content, re.DOTALL)
    
    # If no code found, return early with success state
    if not python_code:
        return {
            "messages": ["No Python code found in the response."],
            'debugging': True,
            'code_generation_success': False
        }
        
    try:
        # Check for API key placeholder
        code_content = python_code[0]
        if "YOUR_API_KEY" in code_content:
            # Get API key from user
            api_key = input("Please enter your API key for this service: ")
            # Replace the placeholder with actual API key
            code_content = code_content.replace("YOUR_API_KEY", api_key)
        
        # Write the code to a file
        with open(SCRIPT_PATH, "w") as f:
            f.write(code_content)

        # Execute the script and capture the output
        result = subprocess.run(
            ["python", SCRIPT_PATH], capture_output=True, text=True
        )

        # Return the captured output or error message
        if result.returncode == 0:
            return {
                "messages": [str(result.stdout)], 
                'debugging': True,
                'code_generation_success': True
            }
        else:
            return {
                "messages": [f"Error:\n{result.stderr}"], 
                'debugging': True,
                'code_generation_success': False
            }
    except Exception as e:
        return {
            "messages": [f"Execution failed: {str(e)}"], 
            'debugging': True,
            'code_generation_success': False
        }

# rag_pipeline('SERP API Python Integration')

# result = search_with_serper_api("OpenWeatherMap API Python Integration")
# print(result)