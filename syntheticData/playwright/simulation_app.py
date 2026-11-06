"""Process-local guard for the existing app; loaded only by serve.py."""
import os

from fastapi.responses import JSONResponse
from app.main import app
from app.core.config import get_settings

KEY = os.environ['SIMULATION_ACCESS_KEY']
RUN_ID = os.environ['SIMULATION_RUN_ID']
INSTANCE = os.environ['SIMULATION_INSTANCE_ID']
assert get_settings().mongodb_events_collection == 'simulation'


@app.middleware('http')
async def simulation_guard(request, call_next):
    if request.url.path.startswith('/api/') and request.headers.get('x-tikit-simulation-key') != KEY:
        return JSONResponse({'detail': 'This instance accepts only the simulation browser'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Tikit-Simulation-Collection'] = 'simulation'
    return response


@app.get('/api/v1/simulation-check', include_in_schema=False)
def simulation_check():
    return {'run_id': RUN_ID, 'instance_id': INSTANCE, 'collection': 'simulation'}
