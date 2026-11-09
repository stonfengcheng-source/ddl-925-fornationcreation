"""Check authentication for a download in an isolated local production-mode service."""
import json, os, subprocess, sys, time, uuid
from pathlib import Path
import httpx

root = Path(__file__).resolve().parents[1]
run = root / 'tmp/http-r9' / ('auth-' + uuid.uuid4().hex[:8]); run.mkdir(parents=True, exist_ok=True)
env = {**os.environ, 'APP_ENV':'production', 'AUTH_MODE':'password', 'SECRET_KEY':'isolated-test-only-key-0123456789abcdef',
       'DATABASE_URL':'sqlite:///' + (run / 'db.sqlite').as_posix(), 'PREPROJECT_DATA_DIR':str(run / 'storage'), 'CORS_ORIGINS':''}
with (run / 'server.log').open('w', encoding='utf-8') as log:
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '18873'], cwd=root / 'backend', env=env, stdout=log, stderr=log)
    try:
        with httpx.Client(base_url='http://127.0.0.1:18873', timeout=10, trust_env=False) as client:
            for _ in range(60):
                try:
                    if client.get('/health').status_code == 200: break
                except httpx.TransportError: pass
                time.sleep(.5)
            else: raise RuntimeError('production-mode service did not start')
            response = client.get('/api/preproject-data/tasks/' + 'a' * 32 + '/files/processed.jsonl')
            if response.status_code != 401: raise RuntimeError(f'unauthenticated download returned {response.status_code}')
            result = {'mode':'production', 'unauthenticated_download_status':response.status_code}
            (run.parent / 'auth_results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result))
    finally:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait()
