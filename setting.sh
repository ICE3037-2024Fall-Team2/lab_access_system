#!/bin/bash

VENV_PATH="lamlai" 
FLASK_APP_PATH="flask_AI.py" 
MAIN_APP_PATH="filelamlai/main.py"  

echo "Activating virtual environment and starting Flask..."
source "$VENV_PATH/bin/activate"
nohup python3 "$FLASK_APP_PATH" > flask.log 2>&1 &  
FLASK_PID=$!  
echo "Flask started with PID $FLASK_PID"

deactivate

echo "Running main.py..."
python3 "$MAIN_APP_PATH"

echo "Stopping Flask with PID $FLASK_PID..."
kill $FLASK_PID

