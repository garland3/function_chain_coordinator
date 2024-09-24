# Function Chain Coordinator

Function Chain Coordinator is a powerful Python package that simplifies the process of creating and managing complex function chains with integrated OpenAI-powered decision making. It's designed to help developers build flexible, intelligent workflows by connecting functions and using AI to make routing decisions.

## Features

- **Easy Function Registration**: Decorate your functions to easily integrate them into the coordinator.
- **Automatic Type Checking**: Ensures type consistency between connected functions.
- **AI-Powered Routing**: Utilize OpenAI's language models to make intelligent decisions about function execution order.
- **Flexible Chain Creation**: Build complex function chains with branching logic.
- **Logging and Debugging**: Built-in logging for easy troubleshooting and monitoring.
- **Callback Support**: Add custom callbacks for extended functionality.

## Installation

You can install the package directly from the repository:

```bash
conda activate agents1

# local install with pip
pip install -e .
```

## Quick Start

Here's a simple example to get you started:

```python
from function_chain_coordinator import CoordinatorInstance, register_function, FunctionResponse
import os

# Initialize the Coordinator
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")

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
    return x

# Create edges
coordinator.create_edge(add_one, router)
coordinator.create_edge(router, multiply_by_two)
coordinator.create_edge(router, subtract_three)

# Example usage with explicit router node
input_value = 4
function_response: FunctionResponse = coordinator.run(input_value)

print("FINAL OUTPUT: ", function_response.final_output)
```

## Why Use Function Chain Coordinator?

- **Simplify Complex Workflows**: Easily create and manage intricate function chains without getting lost in the complexity.
- **AI-Powered Decision Making**: Leverage OpenAI's language models to make intelligent routing decisions in your function chains.
- **Type Safety**: Automatic type checking ensures that your function chains are consistent and error-free.
- **Flexibility**: Adapt your function chains on the fly with dynamic routing capabilities.
- **Debugging Made Easy**: Comprehensive logging helps you understand the flow and identify issues quickly.

## Documentation

For more detailed information on how to use Function Chain Coordinator, please refer to the inline documentation in the source code.

## Contributing

We welcome contributions! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.