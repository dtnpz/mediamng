import os
import re

def remove_mux_sub():
    current_dir = os.getcwd()  # Get current working directory
    
    # List all files in the current directory
    files = os.listdir(current_dir)
    
    for filename in files:
        if '_sub' not in filename and filename.endswith('.mkv'):
            fileNamePattern = re.search(r'_(\d+)', filename, re.IGNORECASE)
            if fileNamePattern:
                new_filename = f"{os.path.splitext(filename)[0]}_old{os.path.splitext(filename)[1]}"  # Append '_old' to the filename
                os.rename(os.path.join(current_dir, filename), os.path.join(current_dir, new_filename))
                print(f"Renamed {filename} to {new_filename}")
    
    for filename in files:
        if '_sub' in filename:
            fileNamePattern = re.search(r'_(\d+)', filename, re.IGNORECASE)
            if fileNamePattern:
                new_filename = filename.replace('_sub', '')  # Remove '_sub' from the filename
                os.rename(os.path.join(current_dir, filename), os.path.join(current_dir, new_filename))
                print(f"Renamed {filename} to {new_filename}")

# Call the function to perform the renaming process
remove_mux_sub()
