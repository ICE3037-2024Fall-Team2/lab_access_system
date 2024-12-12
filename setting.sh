#!/bin/bash

VENV_PATH="lamlai" 
FLASK_APP_PATH="flask_AI.py" 
MAIN_APP_PATH="filelamlai/main.py"  

echo "Activating virtual environment and starting Flask..."
source "$VENV_PATH/bin/activate"
nohup python3 "$FLASK_APP_PATH" > flask.log 2>&1 &  

deactivate

echo "Running main.py..."
python3 "$MAIN_APP_PATH"
