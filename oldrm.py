import os
import re
from send2trash import send2trash

def remove_files_with_old():
    current_dir = os.getcwd()  # Get current working directory
    
    # List all files in the current directory
    files = os.listdir(current_dir)
    
    for filename in files:
        fileNamePattern = re.search(r'_(\d+)', filename, re.IGNORECASE)
        if fileNamePattern and '_old' in filename:
            send2trash(os.path.join(current_dir, filename))
            print(f"Removed {filename}")

# Call the function to remove files containing '_old' in their names
remove_files_with_old()

