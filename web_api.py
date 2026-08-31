# web_api.py
"""
Minimal Flask web API for phase A. Uses Redis if available (optional).
Endpoints:
 - /api/status GET
 - /api/tasks/add POST
 - /api/tasks/start POST
 - /api/tasks/pause POST
 - /api/tasks/resume POST
 - /api/tasks/cancel POST
"""
from flask import Flask, jsonify, request
from download_core import TaskManager
import os

app = Flask(__name__)
manager = TaskManager()

@app.route('/api/status')
def status():
    return jsonify({'tasks': manager.list_tasks()})

@app.route('/api/tasks/add', methods=['POST'])
def add_task():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'no json'}), 400
    if isinstance(data, list):
        ids = []
        for item in data:
            ids.append(manager.add_task(item))
        return jsonify({'added': ids})
    else:
        tid = manager.add_task(data)
        return jsonify({'added': tid})

@app.route('/api/tasks/start', methods=['POST'])
def start_all():
    # start all idle
    for t in manager.list_tasks():
        if t.get('status') in ('idle','failed','paused'):
            manager.start_task(t['id'])
    return jsonify({'ok': True})

@app.route('/api/tasks/pause', methods=['POST'])
def pause():
    data = request.get_json() or {}
    tid = data.get('task_id') or data.get('model_name')
    if not tid: return jsonify({'error': 'missing task_id'}), 400
    manager.pause_task(tid)
    return jsonify({'ok': True})

@app.route('/api/tasks/resume', methods=['POST'])
def resume():
    data = request.get_json() or {}
    tid = data.get('task_id') or data.get('model_name')
    if not tid: return jsonify({'error': 'missing task_id'}), 400
    manager.resume_task(tid)
    return jsonify({'ok': True})

@app.route('/api/tasks/cancel', methods=['POST'])
def cancel():
    data = request.get_json() or {}
    tid = data.get('task_id') or data.get('model_name')
    if not tid: return jsonify({'error': 'missing task_id'}), 400
    manager.cancel_task(tid)
    return jsonify({'ok': True})


def run_web(host='0.0.0.0', port=5000):
    app.run(host=host, port=port)

if __name__ == '__main__':
    run_web()
