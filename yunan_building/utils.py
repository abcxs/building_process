import json
import os

def json_dump(files, output_file):
    with open(output_file, 'w') as f:
        json.dump(files, f, ensure_ascii=False)

def json_load(input_file):
    with open(input_file, 'r') as f:
        files = json.load(f)
    return files