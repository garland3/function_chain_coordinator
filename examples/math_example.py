# example_usage.py

from function_chain_coordinator import CoordinatorInstance, register_function, FunctionResponse
import os

# Initialize the Coordinator with your OpenAI API key and an optional system prompt
# You can set your OpenAI API key as an environment variable for security
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Ensure this environment variable is set
if not OPENAI_API_KEY:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")

# Optional: Define a custom system prompt for the Coordinator
# If not provided, a default prompt is used
custom_system_prompt = "You are ChatGPT, a helpful function chain coordinator."

CoordinatorInstance.initialize(openai_api_key=OPENAI_API_KEY, system_prompt=custom_system_prompt)
coordinator = CoordinatorInstance.get_instance()

@register_function(input_type=int, output_type=int)
def add_one(x):
    return x + 1

@register_function(input_type=int, output_type=int)
def multiply_by_two(x):
    return x * 2

@register_function(input_type=int, output_type=int)
def subtract_three(x):
    return x - 3

@register_function(input_type=int, output_type=int, is_router=True, direction_prompt="""You are picking the next function to run. Not executing the function, just picking the next one. 
if the number is even, pick multiply by two,
if the number is odd,subtract_three. use json.""")
def router(x):
    # This function's logic is handled by the RouterNode and LLM
    return x

# Create edges
coordinator.create_edge(add_one, router)          # add_one -> router
coordinator.create_edge(router, multiply_by_two)  # router -> multiply_by_two
coordinator.create_edge(router, subtract_three)    # router -> subtract_three

# Example usage with explicit router node
input_value = 4
function_response: FunctionResponse = coordinator.run(input_value)

print("FINAL OUTPUT: ", function_response.final_output)
