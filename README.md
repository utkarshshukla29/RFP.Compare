# Streamlit Starter

A minimal Streamlit application that runs locally and can be deployed to Streamlit Community Cloud.

## Run locally

Requirements: Python 3.9 or newer and the Python launcher (`py`) on Windows.

From PowerShell at the project root:

```powershell
.\scripts\setup.ps1
.\scripts\run-local.ps1
```

Open [http://localhost:8501](http://localhost:8501). The setup script creates `.venv` in the project and installs dependencies from the single `requirements.txt` file. The run script binds Streamlit to `127.0.0.1`.

To install or refresh dependencies manually:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Deploy to Streamlit Community Cloud

1. Push this project to a GitHub repository. Do not commit `.venv` or secrets.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app connected to that repository and select `app.py` as the entrypoint.
3. Deploy. Community Cloud installs the app dependencies from `requirements.txt` and provides the hosted Streamlit URL.

## Project files

- `app.py`: Streamlit entrypoint.
- `requirements.txt`: Python dependencies for both local and hosted deployments.
- `.venv/`: local virtual environment created by the setup script; intentionally not committed.
- `scripts/`: Windows PowerShell setup and local launch commands.
- `.streamlit/`: shared Streamlit settings.