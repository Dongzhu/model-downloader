# download_worker.py
"""
Worker process that downloads a single task item.
Supports:
- detect Accept-Ranges
- multi-range parallel download per file
- resume via existing .part files
- pause/cancel via control_flags (multiprocessing.Manager().dict)
- SHA256 verification
- writes progress to state file (atomic)
"""
import os
import math
import tempfile
import threading
import hashlib
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any
from pathlib import Path
import json
import time

CHUNK_SIZE = 1024 * 1024
PART_DIR = ".parts"


def atomic_write(path: str, data: Any):
    tmp = path + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def sha256_of_file(path: str):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(1024 * 1024)
            if not b: break
            h.update(b)
    return h.hexdigest()


def http_head(url, headers=None, timeout=15):
    try:
        r = requests.head(url, headers=headers or {}, allow_redirects=True, timeout=timeout)
        if r.status_code >= 400 or r.status_code == 405:
            r = requests.get(url, headers={**(headers or {}), 'Range': 'bytes=0-0'}, stream=True, timeout=timeout)
        return r
    except Exception:
        return None


def download_range(url, headers, start, end, out_path, control_flags, task_id, part_index, timeout=30, max_retries=3):
    # resume if partial exists
    headers = dict(headers or {})
    headers['Range'] = f'bytes={start}-{end}'
    attempt = 0
    while attempt <= max_retries:
        if control_flags.get(task_id, {}).get('cancel'):
            return False
        if control_flags.get(task_id, {}).get('pause'):
            # pause politely by returning; manager will restart
            return False
        try:
            with requests.get(url, headers=headers, stream=True, timeout=timeout) as r:
                if r.status_code not in (200, 206):
                    attempt += 1
                    time.sleep(1 + attempt)
                    continue
                with open(out_path, 'ab') as f:
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            # flush to disk occasionally
                return True
        except Exception:
            attempt += 1
            time.sleep(1 + attempt)
    return False


def combine_parts(dest_path, parts):
    # atomic combine
    tmp = dest_path + '.tmp'
    with open(tmp, 'wb') as out:
        for p in parts:
            with open(p, 'rb') as r:
                while True:
                    b = r.read(1024 * 1024)
                    if not b: break
                    out.write(b)
    os.replace(tmp, dest_path)


def worker_main(task: Dict[str, Any], control_flags, state_file: str):
    """Download a single task. task is dict with url, filename, id, sha256(optional), headers(optional)"""
    task_id = task.get('id')
    url = task.get('url')
    filename = task.get('filename') or os.path.basename(url.split('?',1)[0])
    outdir = task.get('outdir') or 'models'
    os.makedirs(outdir, exist_ok=True)
    dest_path = os.path.join(outdir, filename)
    temp_dir = os.path.join(outdir, PART_DIR, task_id)
    os.makedirs(temp_dir, exist_ok=True)
    headers = task.get('headers') or {}
    expected_sha = task.get('sha256')
    per_file_workers = int(task.get('parts', 8))

    # get head
    r = http_head(url, headers=headers)
    accept_ranges = False
    total_size = None
    if r is not None:
        if 'Accept-Ranges' in r.headers and 'bytes' in r.headers.get('Accept-Ranges',''):
            accept_ranges = True
        if 'Content-Range' in r.headers:
            try:
                total_size = int(r.headers['Content-Range'].split('/')[-1])
            except Exception:
                total_size = None
        elif 'Content-Length' in r.headers:
            try:
                total_size = int(r.headers['Content-Length'])
            except Exception:
                total_size = None

    # fallback to single-stream
    if not accept_ranges or total_size is None:
        # use simple resume append
        existing = 0
        if os.path.exists(dest_path):
            existing = os.path.getsize(dest_path)
        headers2 = dict(headers)
        if existing > 0:
            headers2['Range'] = f'bytes={existing}-'
        try:
            with requests.get(url, headers=headers2, stream=True) as resp:
                mode = 'ab' if existing else 'wb'
                with open(dest_path + '.part', mode) as f:
                    for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                        if control_flags.get(task_id, {}).get('cancel'):
                            return
                        if control_flags.get(task_id, {}).get('pause'):
                            # write state and exit
                            task['status'] = 'paused'
                            save_state(state_file, task_id, task)
                            return
                        if chunk:
                            f.write(chunk)
            os.replace(dest_path + '.part', dest_path)
            if expected_sha:
                if sha256_of_file(dest_path) != expected_sha.lower():
                    task['status'] = 'failed'
                else:
                    task['status'] = 'completed'
            else:
                task['status'] = 'completed'
            save_state(state_file, task_id, task)
            return
        except Exception as e:
            task['status'] = 'failed'
            save_state(state_file, task_id, task)
            return

    # multi-range strategy
    part_size = math.ceil(total_size / per_file_workers)
    parts = []
    futures = []
    with ThreadPoolExecutor(max_workers=per_file_workers) as ex:
        for i in range(per_file_workers):
            start = i * part_size
            end = min((i + 1) * part_size - 1, total_size - 1)
            part_path = os.path.join(temp_dir, f'part-{i}.part')
            parts.append(part_path)
            # if existing part size equals expected, skip
            # submit download
            futures.append(ex.submit(download_range, url, headers, start, end, part_path, control_flags, task_id, i))
        # wait
        for f in as_completed(futures):
            ok = f.result()
            if not ok:
                task['status'] = 'failed'
                save_state(state_file, task_id, task)
                return
            if control_flags.get(task_id, {}).get('pause'):
                task['status'] = 'paused'
                save_state(state_file, task_id, task)
                return
            if control_flags.get(task_id, {}).get('cancel'):
                task['status'] = 'cancelled'
                save_state(state_file, task_id, task)
                # optionally cleanup parts
                return

    # combine
    combine_parts(dest_path, parts)
    # cleanup parts
    for p in parts:
        try:
            os.remove(p)
        except Exception:
            pass
    # verify
    if expected_sha:
        got = sha256_of_file(dest_path)
        if got.lower() != expected_sha.lower():
            task['status'] = 'failed'
            save_state(state_file, task_id, task)
            return
    task['status'] = 'completed'
    task['progress'] = 100
    save_state(state_file, task_id, task)


def save_state(state_file, task_id, task):
    try:
        data = {}
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        data.setdefault('tasks', {})[task_id] = task
        atomic_write(state_file, data)
    except Exception as e:
        print('Failed to save state', e)
