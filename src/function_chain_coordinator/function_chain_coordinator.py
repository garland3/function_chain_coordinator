# function_chain_coordinator.py

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from functools import wraps
from pydantic import BaseModel, ValidationError, field_validator
import openai
import os
from openai import OpenAI

# ANSI color codes for colored logging
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Configure logging with color support
class ColoredFormatter(logging.Formatter):
    """Custom logging formatter to add colors based on log level."""

    def format(self, record):
        levelno = record.levelno
        if levelno >= logging.ERROR:
            color = Colors.FAIL
        elif levelno >= logging.WARNING:
            color = Colors.WARNING
        elif levelno >= logging.INFO:
            color = Colors.OKGREEN
        elif levelno >= logging.DEBUG:
            color = Colors.OKCYAN
        else:
            color = Colors.ENDC
        record.msg = f"{color}{record.msg}{Colors.ENDC}"
        return super().format(record)

# Set up colored logging
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter('%(levelname)s: %(message)s'))
logger = logging.getLogger(__name__)
logger.handlers = [handler]
logger.setLevel(logging.INFO)

# Callback type
Callback = Callable[['Coordinator'], None]

class FunctionStep(BaseModel):
    function_name: str
    input_value: Any
    output_value: Any

    @field_validator('input_value', 'output_value', mode='before')
    def not_none(cls, v, info):
        if v is None:
            raise ValueError(f"{info.field.name} cannot be None")
        return v

class FunctionResponse(BaseModel):
    steps: List[FunctionStep]
    final_output: Any

    @field_validator('final_output', mode='before')
    def final_output_not_none(cls, v, info):
        if v is None:
            raise ValueError("final_output cannot be None")
        return v

class FunctionChoice(BaseModel):
    reasoning_steps: List[str]
    function_name: str

    @field_validator('reasoning_steps', 'function_name', mode='before')
    def not_none(cls, v, info):
        if v is None:
            raise ValueError(f"{info.field.name} cannot be None")
        return v

class FunctionNode:
    def __init__(self, func: Callable, input_type: type, output_type: type, description_for_routing: Optional[str] = None):
        self.func = func
        self.input_type = input_type
        self.output_type = output_type
        self.description_for_routing = description_for_routing
        self.edges: List['FunctionNode'] = []

    def execute(self, input_value: Any) -> Any:
        logger.info(f"Executing {Colors.OKBLUE}{self.func.__name__}{Colors.ENDC} with input: {Colors.OKCYAN}{input_value}{Colors.ENDC}")
        return self.func(input_value)

class RouterNode(FunctionNode):
    def __init__(
        self,
        func: Callable,
        input_type: type,
        output_type: type,
        direction_prompt: str,
        system_prompt: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ):
        super().__init__(func, input_type, output_type)
        self.direction_prompt = direction_prompt
        self.system_prompt = system_prompt or "You are a helpful assistant for function routing."
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key must be provided either via parameter or environment variable 'OPENAI_API_KEY'.")
        openai.api_key = self.openai_api_key
        self.model = model

    def decide_path(self, input_value: Any) -> 'FunctionNode':
        # Construct the full prompt with function descriptions
        available_functions = ', '.join(
            [f"{edge.func.__name__}: {edge.description_for_routing or 'No description provided.'}" for edge in self.edges]
        )
        full_prompt = (
            f"{self.direction_prompt}\n"
            f"Given the input: {input_value}, decide which function to execute next.\n"
            f"Available functions:\n{available_functions}\n"
            f"Respond with a JSON object like {{'reasoning_steps': ['step1', 'step2', 'step3'], 'function_name': 'chosen_function'}}."
        )
        logger.debug(f"Router Prompt:\n{self.system_prompt}\n{full_prompt}")

        # Log the full prompt
        logger.info(f"Sending prompt to LLM for routing:\n{Colors.BOLD}System Prompt:{Colors.ENDC}\n {self.system_prompt}\n{Colors.BOLD}User Prompt:{Colors.ENDC}\n {full_prompt}\n")

        # Use the OpenAI client beta parse method with Pydantic response_format
        client = OpenAI()
        try:
            completion = client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                response_format=FunctionChoice,
                max_tokens=5000,  # Adjusted tokens to accommodate JSON response
                n=1,
                stop=None,
                temperature=0.0,
            )
        except Exception as e:
            logger.error(f"Error during OpenAI API call: {e}")
            raise

        choice = completion.choices[0].message.parsed
        # Log the reasoning steps
        reasoning_steps = choice.reasoning_steps
        chosen_function_name = choice.function_name
        logger.info(f"Router decided to use: {Colors.OKBLUE}{chosen_function_name}{Colors.ENDC} with reasoning steps: {Colors.OKCYAN}{reasoning_steps}{Colors.ENDC}")

        for edge in self.edges:
            if edge.func.__name__ == chosen_function_name:
                return edge
        raise ValueError(f"No function named '{chosen_function_name}' found among the edges.")

    def execute(self, input_value: Any) -> Any:
        logger.info(f"Router {Colors.OKBLUE}{self.func.__name__}{Colors.ENDC} called. Passing input through unchanged.")
        return input_value  # Pass the input through unchanged

class Coordinator:
    def __init__(self, openai_api_key: Optional[str] = None, system_prompt: Optional[str] = None):
        self.functions: Dict[str, FunctionNode] = {}
        self.callbacks: List[Callback] = []
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key must be provided either via parameter or environment variable 'OPENAI_API_KEY'.")
        self.system_prompt = system_prompt or "You are ChatGPT, a helpful assistant."
        openai.api_key = self.openai_api_key
        logger.info(f"Coordinator {Colors.OKGREEN}initialized{Colors.ENDC}.")

    def register_function(
        self,
        func: Callable,
        input_type: type,
        output_type: type,
        is_router: bool = False,
        direction_prompt: Optional[str] = None,
        router_system_prompt: Optional[str] = None,
        description_for_routing: Optional[str] = None,
    ) -> Callable:
        if is_router:
            if not direction_prompt:
                raise ValueError("Router nodes must have a 'direction_prompt' to guide the LLM.")
            node = RouterNode(
                func,
                input_type,
                output_type,
                direction_prompt,
                router_system_prompt,
                self.openai_api_key
            )
            logger.info(f"Registered {Colors.OKBLUE}router function{Colors.ENDC}: {func.__name__} with input type {input_type.__name__} and output type {output_type.__name__}")
        else:
            node = FunctionNode(
                func,
                input_type,
                output_type,
                description_for_routing
            )
            logger.info(f"Registered {Colors.OKBLUE}function{Colors.ENDC}: {func.__name__} with input type {input_type.__name__} and output type {output_type.__name__}")
        self.functions[func.__name__] = node
        return func

    def create_edge(self, source_func: Callable, target_func: Callable):
        source_node = self.functions.get(source_func.__name__)
        target_node = self.functions.get(target_func.__name__)
        if not source_node or not target_node:
            raise ValueError("Both source and target functions must be registered before creating an edge.")
        if source_node.output_type != target_node.input_type:
            raise TypeError(f"Type mismatch: {source_node.output_type.__name__} -> {target_node.input_type.__name__}")
        source_node.edges.append(target_node)
        logger.info(f"Created edge from '{Colors.OKBLUE}{source_func.__name__}{Colors.ENDC}' to '{Colors.OKBLUE}{target_func.__name__}{Colors.ENDC}'")

    def add_callback(self, callback: Callback):
        self.callbacks.append(callback)
        logger.info("Added a new callback.")

    def run(self, initial_input: Any) -> FunctionResponse:
        # Identify the starting function(s)
        starting_functions = [fn for fn in self.functions.values() if not any(fn in node.edges for node in self.functions.values())]
        if not starting_functions:
            raise ValueError("No starting function found. There might be a cycle or no entry point.")
        if len(starting_functions) > 1:
            raise ValueError("Multiple starting functions found. Please ensure there is only one entry point.")
        current_node = starting_functions[0]
        input_value = initial_input
        steps = []

        while True:
            if isinstance(current_node, RouterNode):
                next_node = current_node.decide_path(input_value)
            else:
                if len(current_node.edges) > 1:
                    raise ValueError(f"Function '{current_node.func.__name__}' has multiple outgoing edges. Use a router node to handle branching.")
                elif len(current_node.edges) == 0:
                    # End of the chain
                    output = current_node.execute(input_value)
                    steps.append(FunctionStep(function_name=current_node.func.__name__, input_value=input_value, output_value=output))
                    logger.info(f"Final output: {Colors.OKGREEN}{output}{Colors.ENDC}")
                    break
                next_node = current_node.edges[0]

            output = current_node.execute(input_value)
            steps.append(FunctionStep(function_name=current_node.func.__name__, input_value=input_value, output_value=output))
            input_value = output
            current_node = next_node

        # Execute callbacks
        for callback in self.callbacks:
            callback(self)

        function_response = FunctionResponse(steps=steps, final_output=output)
        return function_response

def register_function(
    input_type: type,
    output_type: type,
    is_router: bool = False,
    direction_prompt: Optional[str] = None,
    router_system_prompt: Optional[str] = None,
    description_for_routing: Optional[str] = None,
):
    def decorator(func: Callable):
        coordinator = CoordinatorInstance.get_instance()
        return coordinator.register_function(
            func,
            input_type,
            output_type,
            is_router,
            direction_prompt,
            router_system_prompt,
            description_for_routing
        )
    return decorator

class CoordinatorInstance:
    _instance: Optional[Coordinator] = None

    @classmethod
    def initialize(cls, openai_api_key: Optional[str] = None, system_prompt: Optional[str] = None):
        if cls._instance is None:
            cls._instance = Coordinator(openai_api_key, system_prompt)
            logger.info("Coordinator instance initialized.")
        return cls._instance

    @classmethod
    def get_instance(cls) -> Coordinator:
        if cls._instance is None:
            raise ValueError("Coordinator is not initialized. Call CoordinatorInstance.initialize(api_key) first.")
        return cls._instance
