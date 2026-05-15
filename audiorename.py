import os

def remove_mux_sub():
    current_dir = os.getcwd()

    for filename in os.listdir(current_dir):
        if filename.endswith('waudio.mkv'):
            new_filename = filename.replace(
                '_waudio',
                ''
            )

            print(f"Renamed {filename} -> {new_filename}")
            os.rename(filename, new_filename)   

remove_mux_sub()