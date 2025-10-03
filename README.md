# vibeout
This repository contains the python and streamlit code generated for the Springfield Devs vibe coding shootout Oct 1 2025.

## Prerequisites
- **python 3.12**
- **poetry** - see https://python-poetry.org/docs/ for installation
- **mariadb/MySQL**

## Setup
- run `poetry install --no-root`
- update database credentials in
    - **server/quip_download.py** - lines 50 - 53
    - **server/main.py** - update `DATABASE_URL` on line 26 with correct credentials
        - DATABASE_URL = "mysql+pymysql://username:password@host/db_name", e.g., "mysql+pymysql://daniel:password@localhost/vibeout"

## Run
- **server**
    - `cd server`
    - `uvicorn main:app --host 0.0.0.0 --port 8002`
    - open 'http://localhost:8002/docs' in a browser
- **front ent**
    - `cd streamlit_front`
    - `streamlit run app.py --server.port 8003`
    - open 'http://localhost:8003' in a browser
    
