import os 
def delete_file(filename):
    file_path = os.path.join('./saved_states', filename)
    if os.path.exists(file_path):
        os.remove(file_path)