# Universal Flow Registry Calculation Pipeline
# This file implements the calculation: 15/3+2*8 using registry tools

import json
import subprocess
import sys
from pathlib import Path

# Add project root to Python path to ensure modules can be imported
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load registry to get tool information
def load_registry():
    """Load the registry file to get tool definitions"""
    registry_path = Path("../a01_registry/TOOL_INDEX.json")
    with open(registry_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def execute_tool(tool_name, x, y):
    """Execute a tool from the registry with given parameters"""
    registry = load_registry()
    
    # Find the tool in registry
    tool_info = None
    for tool in registry['tools']:
        if tool['name'] == tool_name:
            tool_info = tool
            break
    
    if not tool_info:
        raise ValueError(f"Tool {tool_name} not found in registry")
    
    # Get environment configuration
    env_config = tool_info['environment']
    
    # Determine execution method
    if 'run_command' in env_config:
        run_command = env_config['run_command']
    elif 'run_shell_template' in env_config:
        run_command = env_config['run_shell_template']
    else:
        # Fallback to python as default
        run_command = "python3"
    
    # Get implementation details
    impl_module = env_config['impl_module']
    impl_attr = env_config['impl_attr']
    
    # Construct the command based on tool type
    if 'run_shell_template' in env_config:
        # Use shell template for execution
        command = env_config['run_shell_template'].format(
            project_root=str(project_root),
            x=x,
            y=y
        )
        
        # Execute the shell command
        try:
            result = subprocess.run(
                ['bash', '-c', command],
                capture_output=True,
                text=True,
                check=True
            )
            return float(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Tool execution failed: {e.stderr}")
    else:
        # Use direct python execution
        try:
            # Import and execute
            module = __import__(impl_module, fromlist=[impl_attr])
            func = getattr(module, impl_attr)
            return func(x, y)
        except Exception as e:
            raise RuntimeError(f"Tool execution failed: {str(e)}")

def main():
    """Main calculation function: 15/3+2*8"""
    print("Executing calculation: 15/3+2*8")
    
    # Step 1: Divide 15 by 3
    print("Step 1: Dividing 15 by 3...")
    result1 = execute_tool('divide', 15.0, 3.0)
    print(f"15/3 = {result1}")
    
    # Step 2: Multiply 2 by 8
    print("Step 2: Multiplying 2 by 8...")
    result2 = execute_tool('multiply', 2.0, 8.0)
    print(f"2*8 = {result2}")
    
    # Step 3: Add the results
    print("Step 3: Adding results...")
    final_result = execute_tool('addition', result1, result2)
    print(f"Final result: {result1} + {result2} = {final_result}")
    
    print(f"\nCalculation complete: 15/3+2*8 = {final_result}")
    return final_result

if __name__ == "__main__":
    main()
