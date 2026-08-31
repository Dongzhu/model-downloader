# README.md
# Model Downloader (MVP)

This repository contains an MVP implementation of a multi-process, resume-capable, multi-range downloader with CLI and Web API.

See the `mvp-feature` branch for the current work-in-progress.

Quick start:

1. Clone repo
2. Run `./install.sh` (Unix) or `install.bat` (Windows)
3. Activate venv and run `python run.py --cli`

For web API: `python run.py --web` (starts Flask on :5000)

Docker Redis:
`docker compose up -d` (will start Redis on 6379)
