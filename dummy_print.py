import sys

# Check if an argument is provided
if len(sys.argv) > 1:
    # Get the argument passed from the command line
    argument = sys.argv[1]
    
    # Print the argument
    print(argument)
else:
    print("No argument provided.")