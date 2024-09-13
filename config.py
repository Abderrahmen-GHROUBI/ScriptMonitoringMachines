# config.py
import os 
import json  

def config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    with open(config_path, 'r') as config_file:
        return json.load(config_file)
