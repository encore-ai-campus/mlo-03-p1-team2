"""Launch guarded simulation servers without modifying existing files."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import time
from urllib.request import Request, urlopen
import uuid

from safety import save_json, check_server_identity

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def serve(args):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', args.run_id):
        raise ValueError('Invalid run-id')
    directory = HERE / 'artifacts' / args.run_id
    directory.mkdir(parents=True, exist_ok=True)
    target = {'run_id': args.run_id, 'instance_id': str(uuid.uuid4()),
              'key': secrets.token_urlsafe(32), 'base_url': 'http://127.0.0.1:5174'}
    backend_python = args.backend_python or str(ROOT / '.venv' / 'Scripts' / 'python.exe')
    node = args.node_executable or os.environ.get('TIKIT_NODE') or shutil.which('node')
    if not node or not Path(backend_python).exists():
        raise ValueError('Provide --node-executable and --backend-python for installed runtimes')
    env_backend = dict(os.environ, MONGODB_EVENTS_COLLECTION='simulation',
                       SIMULATION_ACCESS_KEY=target['key'], SIMULATION_RUN_ID=args.run_id,
                       SIMULATION_INSTANCE_ID=target['instance_id'],
                       PYTHONPATH=os.pathsep.join([str(HERE), str(ROOT / 'backend')]))
    env_frontend = dict(os.environ, BACKEND_URL='http://127.0.0.1:8001', VITE_API_BASE='/api/v1')
    children = []
    logs = []
    try:
        for name, command, cwd, env in [
            ('backend', [backend_python, '-m', 'uvicorn', 'simulation_app:app', '--host', '127.0.0.1', '--port', '8001'], ROOT / 'backend', env_backend),
            ('frontend', [node, 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5174', '--strictPort'], ROOT / 'frontend', env_frontend),
        ]:
            log = (directory / f'{name}.log').open('ab')
            logs.append(log)
            child = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=log,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            children.append(child)
        for _ in range(100):
            if any(child.poll() is not None for child in children):
                raise RuntimeError('A simulation server exited; inspect its artifacts log')
            try:
                request = Request(target['base_url'] + '/api/v1/simulation-check',
                                  headers={'X-Tikit-Simulation-Key': target['key']})
                with urlopen(request, timeout=1) as response:
                    check_server_identity(target, json.load(response))
                break
            except (OSError, ValueError):
                time.sleep(0.2)
        else:
            raise RuntimeError('Simulation server did not become ready')
        save_json(directory / 'server.json', target)
        print('Guarded simulation servers ready: 5174 -> 8001 -> simulation', flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        for log in logs:
            log.close()
        print('Simulation servers stopped', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--backend-python')
    parser.add_argument('--node-executable')
    serve(parser.parse_args())
