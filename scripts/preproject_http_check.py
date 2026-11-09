import json, os, re, subprocess, sys, time, uuid
from pathlib import Path
import httpx

root = Path(__file__).resolve().parents[1]
run = root / 'tmp/http-r9' / uuid.uuid4().hex[:8]
run.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env.update(DATABASE_URL='sqlite:///' + (run / 'test.db').as_posix(),
           PREPROJECT_DATA_DIR=str(run / 'storage'), AUTH_MODE='passwordless', DEV_AUTH_USERNAME='v2_test_admin')
log = (run / 'server.log').open('w', encoding='utf-8')
proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '18872'],
                        cwd=root / 'backend', env=env, stdout=log, stderr=log)
events = []
try:
    with httpx.Client(base_url='http://127.0.0.1:18872/api/preproject-data', timeout=60, trust_env=False) as client:
        for _ in range(60):
            try:
                r = client.get('/catalog')
                if r.status_code == 200: break
            except httpx.TransportError: pass
            time.sleep(.5)
        else: raise RuntimeError('service did not start')
        def record(name, response, expected=200):
            events.append({'action': name, 'status': response.status_code})
            if response.status_code != expected: raise RuntimeError(f'{name}: {response.status_code} {response.text[:500]}')
            return response
        record('catalog', r)
        record('untrusted_origin_blocked', client.get('/catalog', headers={'Origin':'https://example.invalid'}), 403)
        record('untrusted_host_blocked', client.get('/catalog', headers={'Host':'example.invalid'}), 403)
        record('sources', client.get('/sources'))
        demo = record('test_only_initialize', client.post('/sources/demo-fixture'), 201).json()
        if demo.get('source_type') != 'test_fixture': raise RuntimeError('test fixture is not labelled')
        demo_task = record('test_only_task', client.post('/tasks', json={'source_id':demo['source_id'],'version_name':'test-only-demo'}), 202).json()['task']
        data = {'dataset_id':'ecnu-icalk/educhat-sft-002-data-osm', 'source_url':'https://huggingface.co/datasets/ecnu-icalk/educhat-sft-002-data-osm', 'license':'cc-by-nc-4.0', 'revision':'unverified-viewer', 'split':'train'}
        with (root / 'data/preproject/incoming/200/educhat_raw_200.jsonl').open('rb') as f:
            source = record('upload', client.post('/sources/upload', data=data, files={'file': ('educhat.jsonl', f, 'application/x-ndjson')}), 201).json()
        sid = source['source_id']
        record('validate', client.post(f'/sources/{sid}/validate'))
        record('preview', client.get(f'/sources/{sid}/preview'))
        task = record('create', client.post('/tasks', json={'source_id':sid, 'version_name':'http-v2'}), 202).json()['task']
        tid = task['task_id']
        for _ in range(480):
            task = record('poll', client.get(f'/tasks/{tid}')).json()
            if task['status'] in ('completed','failed','cancelled'): break
            time.sleep(.25)
        if task['status'] != 'completed': raise RuntimeError(f'task ended {task.get("status")}: {task.get("error")}')
        result = record('results', client.get(f'/tasks/{tid}/results')).json()
        if result['statistics']['final_retained_count'] != 200 or result['gate']['release_eligible']:
            raise RuntimeError('unexpected quality or release state')
        sample_page = record('sample_comparison', client.get(f'/tasks/{tid}/samples?limit=2')).json()
        if len(sample_page['items']) != 2 or not sample_page['items'][0]['before']: raise RuntimeError('sample comparison unavailable')
        stage_page = record('stage_drilldown', client.get(f'/tasks/{tid}/samples', params={'issue':'stage:deduplication'})).json()
        if stage_page['total'] != 0: raise RuntimeError('unexpected real-data dedup issues')
        record('review_queue', client.get(f'/tasks/{tid}/review-items'))
        versions_response = record('versions', client.get('/versions'))
        for public_response in (client.get('/sources'), versions_response, client.get(f'/tasks/{tid}'), client.get(f'/tasks/{tid}/results')):
            if re.search(r'(?<![A-Za-z0-9])[A-Za-z]:[\\/]', json.dumps(public_response.json(), ensure_ascii=False).replace('\\\\', '\\')):
                raise RuntimeError('public response leaked an internal path')
        for name in ('processed.jsonl','qualified.jsonl','statistics.json','quality_metrics.json','quality_report.md','dataset_manifest.json','dedup_report.json','privacy_report.json','processing_actions.jsonl'):
            response = record('download '+name, client.get(f'/tasks/{tid}/files/{name}'))
            (run / name).write_bytes(response.content)
        import hashlib
        downloaded_manifest = json.loads((run / 'dataset_manifest.json').read_text(encoding='utf-8'))
        for name in ('statistics.json', 'dataset_manifest.json'):
            if re.search(r'(?<![A-Za-z0-9])[A-Za-z]:[\\/]', (run / name).read_text(encoding='utf-8').replace('\\\\', '\\')):
                raise RuntimeError('download leaked an internal path: ' + name)
        for name, details in downloaded_manifest['artifacts'].items():
            if (run / name).is_file() and hashlib.sha256((run / name).read_bytes()).hexdigest() != details['sha256']:
                raise RuntimeError('download hash mismatch: ' + name)
        record('release_blocked', client.post(f"/versions/{task['version_id']}/release-candidate"), 409)
        record('invalid_parameters', client.post('/tasks', json={'source_id':sid, 'near_duplicate_hamming_distance':99}), 400)
        record('missing_file', client.get(f'/tasks/{tid}/files/reviewed_manifest.json'), 404)
        def wait_task(task_id):
            for _ in range(160):
                value = client.get(f'/tasks/{task_id}').json()
                if value['status'] in ('completed', 'failed', 'cancelled'): return value
                time.sleep(.1)
            raise RuntimeError('task timeout')
        demo_completed = wait_task(demo_task['task_id'])
        if demo_completed['status'] != 'completed' or demo_completed['statistics']['raw_sample_count'] != 2:
            raise RuntimeError('TEST-ONLY demo processing did not complete')
        fixture = '\n'.join(json.dumps(x, ensure_ascii=False) for x in [
            {'sample_id':'fixture-a', 'instruction':'TEST-ONLY question', 'output':'first distinct answer'},
            {'sample_id':'fixture-b', 'instruction':'TEST-ONLY question', 'output':'another distinct answer'}]) + '\n'
        fixture_source = record('fixture_upload', client.post('/sources/upload', data=data, files={'file':('fixture.jsonl', fixture.encode('utf-8'), 'application/x-ndjson')}), 201).json()
        fixture_id = fixture_source['source_id']
        fixture_task = record('fixture_task', client.post('/tasks', json={'source_id':fixture_id,'version_name':'review-fixture'}), 202).json()['task']['task_id']
        if wait_task(fixture_task)['status'] != 'completed': raise RuntimeError('fixture failed')
        queue = record('fixture_review_queue', client.get(f'/tasks/{fixture_task}/review-items')).json()
        if not queue['items']: raise RuntimeError('fixture review queue is empty')
        sample_id = queue['items'][0]['sample_id']
        record('fixture_review_accept', client.post(f'/tasks/{fixture_task}/reviews', json={'sample_id':sample_id,'decision':'accept','expected_revision':queue['revision']}), 201)
        other_id = next(item['sample_id'] for item in queue['items'] if item['sample_id'] != sample_id)
        record('stale_review_conflict', client.post(f'/tasks/{fixture_task}/reviews', json={'sample_id':other_id,'decision':'edit','expected_revision':queue['revision'],'edited_content':{'instruction':'TEST-ONLY different question','output':'TEST-ONLY revised answer'}}), 409)
        reviewed = record('fixture_review_edit', client.post(f'/tasks/{fixture_task}/reviews', json={'sample_id':other_id,'decision':'edit','expected_revision':queue['revision']+1,'edited_content':{'instruction':'TEST-ONLY different question','output':'TEST-ONLY revised answer'}}), 201).json()
        reviewed_file = record('reviewed_file', client.get(f'/tasks/{fixture_task}/files/reviewed_processed.jsonl')).text
        revised_rows = [json.loads(line) for line in reviewed_file.splitlines() if line.strip()]
        if len(revised_rows) != 2 or not any(row['sample_id'] == other_id and row['instruction'] == 'TEST-ONLY different question' and row['processing_status'] == 'keep' for row in revised_rows): raise RuntimeError('edited sample was not rechecked and admitted')
        fixture_data = client.get(f'/tasks/{fixture_task}').json()
        comparison = record('version_comparison', client.get('/version-comparison', params={'left':fixture_data['version_id'], 'right':reviewed['version']['version_id']})).json()
        if comparison['changed_count'] != 1: raise RuntimeError('version comparison is incorrect')
        if comparison['status_changed_count'] != 2 or comparison['qualified_change'] != {'left':0, 'right':2} or not comparison['metrics']:
            raise RuntimeError('version quality or status comparison is incorrect')
        revised_samples = record('reviewed_sample_comparison', client.get(f'/tasks/{fixture_task}/samples')).json()
        if not any(item['sample_id'] == other_id and item['after']['instruction'] == 'TEST-ONLY different question' for item in revised_samples['items']):
            raise RuntimeError('sample comparison does not use the reviewed version')
        record('fixture_review_history', client.get(f'/tasks/{fixture_task}/reviews'))
        # Alter only the isolated fixture source to provoke the task's hash check, then restore it for retry.
        fixture_path = next((run / 'storage' / 'users').glob(f'*/sources/{fixture_id}/source.jsonl'))
        original = fixture_path.read_bytes()
        fixture_path.write_bytes(original + b'\n')
        failed_id = record('create_failure_fixture', client.post('/tasks', json={'source_id':fixture_id,'version_name':'failure-fixture'}), 202).json()['task']['task_id']
        failed = wait_task(failed_id)
        fixture_path.write_bytes(original)
        if failed['status'] != 'failed': raise RuntimeError('failure fixture did not fail')
        retry_id = record('retry_failed', client.post(f'/tasks/{failed_id}/retry'), 202).json()['task']['task_id']
        if wait_task(retry_id)['status'] != 'completed': raise RuntimeError('retry did not complete')
        cancel_id = record('create_cancel', client.post('/tasks', json={'source_id':sid,'version_name':'cancel-fixture'}), 202).json()['task']['task_id']
        record('cancel_request', client.post(f'/tasks/{cancel_id}/cancel'))
        cancelled = wait_task(cancel_id)
        if cancelled['status'] != 'cancelled': raise RuntimeError('cancel was not observed')
        summary = {'events':events, 'task_id':tid, 'status':task['status'], 'counts':result['statistics']['status_counts'], 'qualified':result['statistics']['final_retained_count'], 'files':result['files'], 'fixture_review_task':fixture_task, 'failure_task':failed_id, 'retry_task':retry_id, 'cancel_task':cancel_id}
        (run / 'http_results.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        (run.parent / 'http_results.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(summary, ensure_ascii=False))
finally:
    proc.terminate()
    try: proc.wait(timeout=10)
    except subprocess.TimeoutExpired: proc.kill(); proc.wait()
    log.close()
