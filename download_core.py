# model-downloader: MVP core entry -- download_core.py
"""
Core task manager for model-downloader.
- Manages task lifecycle
- Persists state to JSON (atomic)
- Spawns worker processes for downloads
- Controls pause/resume/cancel via shared dict
"""
import os
import json
import time
import uuid
import signal
from multiprocessing import Process, Manager
from typing import Dict, Any, Optional
from pathlib import Path
from download_worker import worker_main

STATE_FILE = "data/state.json"
STATE_BACKUP = "data/state.bak.json"


def atomic_write(path: str, data: Any):
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class TaskManager:
    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file
        self.manager = Manager()
        # control_flags: {task_id: {"pause": False, "cancel": False}}
        self.control_flags = self.manager.dict()
        # processes: local mapping task_id -> Process
        self.processes: Dict[str, Process] = {}
        self.state = {"tasks": {}}
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.state = json.load(f)
            except Exception:
                print("Warning: failed to load state, starting fresh")
                self.state = {"tasks": {}}
        else:
            os.makedirs(os.path.dirname(self.state_file) or '.', exist_ok=True)
            atomic_write(self.state_file, self.state)

    def _save_state(self):
        # backup
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    old = f.read()
                with open(STATE_BACKUP, 'w', encoding='utf-8') as b:
                    b.write(old)
        except Exception:
            pass
        atomic_write(self.state_file, self.state)

    def add_task(self, item: Dict[str, Any]) -> str:
        tid = item.get('id') or str(uuid.uuid4())
        item['id'] = tid
        item.setdefault('status', 'idle')
        item.setdefault('progress', 0)
        self.state['tasks'][tid] = item
        self._save_state()
        print(f"Added task {tid}")
        return tid

    def start_task(self, task_id: str):
        if task_id in self.processes and self.processes[task_id].is_alive():
            print(f"Task {task_id} already running")
            return
        task = self.state['tasks'].get(task_id)
        if not task:
            print('No such task')
            return
        self.control_flags[task_id] = {"pause": False, "cancel": False}
        p = Process(target=worker_main, args=(task, self.control_flags, self.state_file))
        p.start()
        self.processes[task_id] = p
        task['status'] = 'downloading'
        self._save_state()
        print(f"Started task {task_id} pid={p.pid}")

    def pause_task(self, task_id: str):
        if task_id in self.control_flags:
            self.control_flags[task_id]['pause'] = True
            self.state['tasks'][task_id]['status'] = 'pausing'
            self._save_state()
            print(f"Pausing {task_id}")
        else:
            print('Task not running')

    def resume_task(self, task_id: str):
        # Clear flag and spawn new process if needed
        flags = self.control_flags.get(task_id)
        if flags:
            flags['pause'] = False
            # if process not alive spawn new
            p = self.processes.get(task_id)
            if not p or not p.is_alive():
                self.start_task(task_id)
            self.state['tasks'][task_id]['status'] = 'downloading'
            self._save_state()
            print(f"Resumed {task_id}")
        else:
            # may be paused state but no running flags; spawn
            if self.state['tasks'].get(task_id):
                self.start_task(task_id)

    def cancel_task(self, task_id: str):
        if task_id in self.control_flags:
            self.control_flags[task_id]['cancel'] = True
            self.state['tasks'][task_id]['status'] = 'cancelling'
            self._save_state()
            print(f"Cancelling {task_id}")
        else:
            # mark cancelled in state
            t = self.state['tasks'].get(task_id)
            if t:
                t['status'] = 'cancelled'
                self._save_state()

    def list_tasks(self):
        return list(self.state['tasks'].values())

    def shutdown(self):
        print('Shutting down manager, signalling workers to cancel...')
        for tid, flags in list(self.control_flags.items()):
            flags['cancel'] = True
        for tid, p in list(self.processes.items()):
            if p.is_alive():
                p.join(timeout=5)
        self._save_state()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--add', help='path to manifest json to add (single item or array)')
    parser.add_argument('--start', help='start task id')
    parser.add_argument('--pause', help='pause task id')
    parser.add_argument('--resume', help='resume task id')
    parser.add_argument('--cancel', help='cancel task id')
    parser.add_argument('--list', action='store_true')
    args = parser.parse_args()

    mgr = TaskManager()
    if args.add:
        with open(args.add, 'r', encoding='utf-8') as f:
            j = json.load(f)
            if isinstance(j, list):
                for item in j:
                    mgr.add_task(item)
            else:
                mgr.add_task(j)
    elif args.start:
        mgr.start_task(args.start)
    elif args.pause:
        mgr.pause_task(args.pause)
    elif args.resume:
        mgr.resume_task(args.resume)
    elif args.cancel:
        mgr.cancel_task(args.cancel)
    elif args.list:
        for t in mgr.list_tasks():
            print(json.dumps(t, ensure_ascii=False))
    else:
        print('No action, use --help')


if __name__ == '__main__':
    main()
