# Ranking Web App

## Quick start (fixes `ModuleNotFoundError: No module named 'flask_sqlalchemy'`)

```bash
cd /workspace/nc-pod
./run_local.sh
```

The script will:
1. Create `.venv` if missing
2. Install dependencies from `requirements.txt`
3. Start app at `http://127.0.0.1:8080`

## Manual start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

If you still see the same error, ensure you're using the same Python interpreter as the one where packages were installed:

```bash
which python
python -m pip show Flask-SQLAlchemy
```
