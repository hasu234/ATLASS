from typing import Any, Dict, List, Optional, Mapping
import json
import requests
import re
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import LLMResult
from dotenv import load_dotenv
import os
import inspect

load_dotenv()
llm_model = os.getenv("LLM_MODEL")

class LocalLLM(LLM):
    """Custom LLM wrapper for DeepSeek model running on Ollama."""
    
    api_url: str = "http://10.10.10.104:11434/api/generate"
    model_name: str = llm_model
    temperature: float = 0.1
    system_prompt: str = "You are a helpful assistant that provides accurate, presized responses."
    
    @property
    def _llm_type(self) -> str:
        return llm_model
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the DeepSeek model with the given prompt."""
        combined_prompt = f"<|system|>\n{self.system_prompt}\n<|user|>\n{prompt}"
        
        payload = json.dumps({
            "model": self.model_name,
            "prompt": combined_prompt,
            "stream": False,
            "temperature": self.temperature
        })
        
        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(self.api_url, data=payload, headers=headers)
        if response.status_code != 200:
            raise ValueError(f"Error from Ollama API: {response.text}")
        
        return response.json().get("response", "")


class LocalChatModel:
    """Custom Chat model wrapper for DeepSeek model running on Ollama."""
    
    def __init__(
        self,
        api_url: str = "http://10.10.10.104:11434/api/generate",
        model_name: str = llm_model,
        temperature: float = 0.1,
        system_prompt: str = "You are a helpful assistant that provides accurate, detailed responses."
    ):
        self.api_url = api_url
        self.model_name = model_name
        self.temperature = temperature
        self.system_prompt = system_prompt
    
    def _format_messages(self, messages: List[BaseMessage]) -> str:
        """Format messages for the DeepSeek model."""
        prompt_parts = []
        
        # Check if there's a system message
        system_content = self.system_prompt
        for message in messages:
            if isinstance(message, SystemMessage):
                system_content = message.content
                break
        
        prompt_parts.append(f"<|system|>\n{system_content}")
        
        for message in messages:
            if isinstance(message, SystemMessage):
                continue  # Already handled
            elif isinstance(message, HumanMessage):
                prompt_parts.append(f"<|user|>\n{message.content}")
            elif isinstance(message, AIMessage):
                prompt_parts.append(f"<|assistant|>\n{message.content}")
            else:
                # Default to user for other message types
                prompt_parts.append(f"<|user|>\n{message}")
        
        # Add assistant tag at the end to prompt model to generate assistant's response
        prompt_parts.append("<|assistant|>")
        
        return "\n".join(prompt_parts)
    
    def invoke(self, messages: List[BaseMessage]) -> AIMessage:
        """Call the DeepSeek model with the given messages."""
        formatted_prompt = self._format_messages(messages)
        
        payload = json.dumps({
            "model": self.model_name,
            "prompt": formatted_prompt,
            "stream": False,
            "temperature": self.temperature
        })
        
        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(self.api_url, data=payload, headers=headers)
        if response.status_code != 200:
            raise ValueError(f"Error from Ollama API: {response.text}")
        
        response_text = response.json().get("response", "")
        # 🧼 Strip <think> blocks and keep only the actual final output
        if "</think>" in response_text:
            response_text = response_text.split("</think>")[-1].strip()
        
        return AIMessage(content=response_text)
    
    def bind_tools(self, tools):
        """Implementation of bind_tools to enable tool usage with local LLMs."""
        self_instance = self
        
        class ToolBoundLocalChat:
            def __init__(self, llm, tools):
                self.llm = llm
                self.tools = {tool.__name__: tool for tool in tools}
                
                # Build tool descriptions with parameters
                tool_descriptions = []
                for tool in tools:
                    tool_name = tool.__name__
                    tool_description = tool.__doc__ or "No description"
                    
                    # Get parameter information
                    signature = inspect.signature(tool)
                    params = []
                    for param_name, param in signature.parameters.items():
                        param_type = param.annotation.__name__ if param.annotation != inspect.Parameter.empty else "any"
                        params.append(f"- {param_name}: {param_type}")
                    
                    # Format the tool description
                    description = f"Tool: {tool_name}\nDescription: {tool_description}\nParameters:\n" + "\n".join(params)
                    tool_descriptions.append(description)
                
                # Create comprehensive instructions
                self.tool_instructions = (
                    "You have access to the following tools:\n\n" + 
                    "\n\n".join(tool_descriptions) + 
                    "\n\nUse the tools to answer the user's question.\n" +
                    "After receiving the tool output, provide your final response based on the tool output."
                )
            
            def _parse_tool_calls(self, text):
                """Parse tool calls from the model's response."""
                tool_pattern = r"```tool\s*([\s\S]*?)```"
                matches = re.findall(tool_pattern, text)
                
                if not matches:
                    return None
                
                try:
                    tool_call = json.loads(matches[0])
                    return tool_call
                except json.JSONDecodeError:
                    return None
            
            def _execute_tool(self, tool_call):
                """Execute the specified tool with parameters."""
                if not tool_call or "tool_name" not in tool_call:
                    return "Error: Invalid tool call format"
                
                tool_name = tool_call["tool_name"]
                parameters = tool_call.get("parameters", {})
                
                if tool_name not in self.tools:
                    return f"Error: Tool '{tool_name}' not found"
                
                try:
                    tool_function = self.tools[tool_name]
                    result = tool_function(**parameters)
                    return result
                except Exception as e:
                    return f"Error executing tool '{tool_name}': {str(e)}"
            
            def _add_tool_instructions(self, messages):
                """Add tool instructions to the system message."""
                has_system = False
                new_messages = []
                
                for message in messages:
                    if isinstance(message, SystemMessage):
                        new_system = SystemMessage(content=message.content + "\n\n" + self.tool_instructions)
                        new_messages.append(new_system)
                        has_system = True
                    else:
                        new_messages.append(message)
                
                if not has_system:
                    new_messages.insert(0, SystemMessage(content=self.tool_instructions))
                
                return new_messages
            
            def invoke(self, messages):
                """Process messages, handle tool calls, and return final response."""
                # Step 1: Add tool instructions to system message
                new_messages = self._add_tool_instructions(messages)
                
                # Step 2: Get initial response from LLM
                initial_response = self_instance.invoke(new_messages)
                
                # Step 3: Check if response contains tool calls
                tool_call = self._parse_tool_calls(initial_response.content)
                
                # If no tool call is detected, return the initial response
                if not tool_call:
                    # Clean up the response by removing tool-related formatting
                    cleaned_content = re.sub(r"```tool[\s\S]*?```", "", initial_response.content).strip()
                    return AIMessage(content=cleaned_content)
                
                # Step 4: Execute the tool
                tool_result = self._execute_tool(tool_call)
                
                # Step 5: Append the tool result to conversation
                tool_message = f"Tool '{tool_call['tool_name']}' returned: {tool_result}"
                new_messages.append(AIMessage(content=initial_response.content))
                new_messages.append(HumanMessage(content=tool_message))
                
                # Step 6: Get final response from LLM with tool results
                final_response = self_instance.invoke(new_messages)
                
                return final_response
        
        return ToolBoundLocalChat(self, tools)