"""Create a source review package without local data, credentials or installed dependencies."""
from __future__ import annotations
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'deliverables' / 'data-platform-preproject-review-v2.zip'
EVIDENCE = ROOT / 'data/preproject/processed/educhat-200-round9-v4'
BLOCKED_DIRS = {'.git', '.idea', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache', 'dist', 'data', 'tmp', 'saved_models', '.pnpm-store', '.husky'}
BLOCKED_SUFFIXES = {'.pyc', '.pyo', '.db', '.sqlite', '.sqlite3', '.pem', '.key', '.log', '.pt', '.pth', '.bin', '.safetensors', '.onnx'}
SECRET_RE = re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{20,}|\bgh[pousr]_[A-Za-z0-9]{20,}')

def sanitize_text(text: str) -> str:
    text = re.sub(r'[A-Za-z]:\\Users\\[^\\]+\\\.conda\\envs\\[^\\]+\\python\.exe', 'python', text, flags=re.I)
    text = re.sub(r'[A-Za-z]:\\[^\\\s]+\\clean', '<project-root>', text, flags=re.I)
    text = re.sub(r'[A-Za-z]:/[^/\s]+/clean', '<project-root>', text, flags=re.I)
    return text

def scrub(value):
    if isinstance(value, dict): return {k: scrub(v) for k, v in value.items()}
    if isinstance(value, list): return [scrub(v) for v in value]
    if isinstance(value, str) and re.match(r'^[A-Za-z]:[\\/]', value): return '<local-path-redacted>/' + re.split(r'[\\/]', value)[-1]
    return sanitize_text(value) if isinstance(value, str) else value

def eligible(path: Path) -> bool:
    name = path.name.lower()
    if name in {'.env', '.env.local', '.env.production', 'credentials', 'credentials.json'} or name.endswith(('.pem', '.key')): return False
    if name.startswith('.env.') and name != '.env.example': return False
    return path.suffix.lower() not in BLOCKED_SUFFIXES and path.stat().st_size <= 5 * 1024 * 1024

def source_files():
    for folder in ('frontend', 'backend', 'data_pipeline', 'configs', 'scripts', 'docs', 'federated-learning'):
        base = ROOT / folder
        for current, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in BLOCKED_DIRS and not d.startswith('.pytest') and not d.startswith('.codex')]
            for name in files:
                path = Path(current) / name
                if eligible(path): yield path
    for name in ('README.md', 'CONTRIBUTING.md', 'main.py', 'demo-datasets/preproject-test-only.jsonl'):
        path = ROOT / name
        if path.is_file(): yield path

def main():
    if not EVIDENCE.is_dir(): raise SystemExit('Missing real-data evidence; run the documented CLI first.')
    DEST.parent.mkdir(parents=True, exist_ok=True)
    names = []
    with zipfile.ZipFile(DEST, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in source_files():
            name = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            if path.suffix.lower() == '.md': data = sanitize_text(data.decode('utf-8')).encode('utf-8')
            if SECRET_RE.search(data): raise SystemExit(f'Possible credential in {name}; package not completed.')
            archive.writestr(name, data)
            names.append(name)
        for name in ('statistics.json', 'quality_metrics.json', 'dataset_manifest.json', 'quality_report.md'):
            raw = (EVIDENCE / name).read_text(encoding='utf-8')
            content = json.dumps(scrub(json.loads(raw)), ensure_ascii=False, indent=2) + '\n' if name.endswith('.json') else sanitize_text(raw)
            archive.writestr('evidence/' + name, content.encode('utf-8'))
        http_file = ROOT / 'tmp/http-r9/http_results.json'
        if http_file.is_file(): archive.writestr('evidence/http_results.json', json.dumps(scrub(json.loads(http_file.read_text(encoding='utf-8'))), ensure_ascii=False, indent=2).encode('utf-8'))
        auth_file = ROOT / 'tmp/http-r9/auth_results.json'
        if auth_file.is_file(): archive.writestr('evidence/auth_results.json', json.dumps(scrub(json.loads(auth_file.read_text(encoding='utf-8'))), ensure_ascii=False, indent=2).encode('utf-8'))
        archive.writestr('evidence/environment.json', json.dumps({'python_cli':'3.13.0', 'node':'24.13.0', 'npm':'11.6.2', 'fastapi':'0.139.0', 'uvicorn':'0.50.0', 'sqlalchemy':'2.0.51', 'httpx':'0.28.1', 'frontend_tests':'61 passed', 'pipeline_tests':'13 passed', 'review_tests':'5 passed', 'browser':'not run'}, indent=2).encode('utf-8'))
        archive.writestr('evidence/test_summary.md', ('# 第九轮验证摘要\n\n- 前端 Vitest：61 项通过；预立项相关 15 项。\n- 数据流水线：13 项通过。\n- 后端复核、安全定向测试：5 项通过。\n- 真实 HTTP：200 条输入、200 条工程候选，来源及授权未核验，发布受阻。\n- 隔离正式认证模式：未登录下载返回 401。\n- 未进行浏览器视觉或交互验收。\n\n命令及限制见 docs/frontend_test_report.md 和 docs/real_data_test_report.md。\n').encode('utf-8'))
    required = ['frontend/package.json', 'frontend/package-lock.json', 'frontend/src/pages/PreprojectData/index.tsx', 'backend/requirements.txt', 'backend/app/api/preproject_data.py', 'data_pipeline/pipeline.py', 'configs/preproject_pipeline.json', 'scripts/start_demo.ps1', 'docs/review_package_readme.md', 'evidence/statistics.json']
    with zipfile.ZipFile(DEST) as archive:
        entries = archive.namelist()
        missing = [name for name in required if name not in entries]
        unsafe = [name for name in entries if any(part in BLOCKED_DIRS for part in Path(name).parts) or Path(name).suffix.lower() in BLOCKED_SUFFIXES or Path(name).name in {'.env', '.env.local'}]
        if missing or unsafe or archive.testzip(): raise SystemExit(f'Invalid package: missing={missing}, unsafe={unsafe}')
    digest = hashlib.sha256(DEST.read_bytes()).hexdigest()
    print(json.dumps({'file':str(DEST), 'bytes':DEST.stat().st_size, 'sha256':digest, 'entries':len(entries), 'required':required}, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
