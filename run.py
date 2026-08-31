# run.py
"""
Unified entrypoint. --cli or --web
"""
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cli', action='store_true')
    parser.add_argument('--web', action='store_true')
    args = parser.parse_args()
    if args.cli:
        from download_cli import interactive
        interactive()
    elif args.web:
        from web_api import run_web
        run_web()
    else:
        print('Use --cli or --web')
