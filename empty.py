# THIS FILE JUST MAKES IT EASY TO RESET THE NETWORK, IT CLEANS OUT ALL THE CHANNELS AND OUTPUT FILES

import os
def empty(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
                print(f"Removed '{file_path}'")
        except Exception as e:
            print(f"Error deleting '{file_path}': {e}")
empty("channels")
empty("output")
