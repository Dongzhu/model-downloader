# download_cli.py
"""
A simple CLI using prompt_toolkit for interaction.
Provides menus to add tasks, list, start, pause, resume, cancel, and launch web server.
"""
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from download_core import TaskManager
import json

mgr = TaskManager()

menu = WordCompleter(['add','list','start','pause','resume','cancel','web','exit'], ignore_case=True)


def cmd_add():
    p = prompt('Manifest path to add: ')
    try:
        mgr.add_task(json.load(open(p,'r',encoding='utf-8')))
    except Exception as e:
        print('Failed to add', e)


def cmd_list():
    for t in mgr.list_tasks():
        print(json.dumps(t, ensure_ascii=False))


def interactive():
    print('Model Downloader CLI')
    while True:
        try:
            c = prompt('> ', completer=menu)
        except KeyboardInterrupt:
            break
        if not c: continue
        if c == 'add':
            cmd_add()
        elif c == 'list':
            cmd_list()
        elif c == 'start':
            tid = prompt('task id: ')
            mgr.start_task(tid)
        elif c == 'pause':
            tid = prompt('task id: ')
            mgr.pause_task(tid)
        elif c == 'resume':
            tid = prompt('task id: ')
            mgr.resume_task(tid)
        elif c == 'cancel':
            tid = prompt('task id: ')
            mgr.cancel_task(tid)
        elif c == 'web':
            from web_api import run_web
            run_web()
        elif c == 'exit':
            mgr.shutdown()
            break
        else:
            print('unknown')


if __name__ == '__main__':
    interactive()
