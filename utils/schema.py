from langgraph.graph import MessagesState
from typing_extensions import TypedDict

class RequiredTool(TypedDict):
    name: str
    description: str
    is_available: bool
    function: str

class State(MessagesState):
    max_turns: int = 2
    required_tools: list[RequiredTool] = []
    code_generation_success: bool = False
    human_approved: bool = False
    human_feedback: str = ""

class ToolState(MessagesState):
    context: list
    search_query: str
    api_name: str
    debugging: bool = False
    max_turns: int = 2
    required_tools: list[RequiredTool] = []
    code_generation_success: bool = False
    human_approved: bool = False
    human_feedback: str = ""
    api_key: str = None
    execution_output: str = None