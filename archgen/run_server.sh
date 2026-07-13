#!/bin/bash
cd /home/admin/.openclaw/workspace/behavior_recorder_service/archgen
exec python3 -c "
import uvicorn
from main import create_app
app = create_app()
uvicorn.run(app, host='0.0.0.0', port=8960, log_level='info')
"
