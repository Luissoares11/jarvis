#!/bin/bash

cd ~/Desktop/projects/jarvis || exit

git pull

pkill -f "uvicorn server.main:app"

nohup uvicorn server.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &