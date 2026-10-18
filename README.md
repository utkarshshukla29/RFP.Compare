# Streamlit Starter

A minimal Streamlit application with a local sandbox workflow and a production deployment path using Streamlit Community Cloud.

## Local sandbox

Requirements: Python 3.9 or newer and the Python launcher (`py`) on Windows.

From PowerShell at the project root:

```powershell
.\scripts\setup.ps1
.\scripts\run-sandbox.ps1
```

Open [http://localhost:8501](http://localhost:8501). The setup script creates `.venv` in the project and installs dependencies from the single `requirements.txt` file. The run script sets `APP_ENV=sandbox` and binds Streamlit to `127.0.0.1`.

To install or refresh dependencies manually:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Production deployment

1. Push this project to a GitHub repository. Do not commit `.venv` or secrets.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app connected to that repository and select `app.py` as the entrypoint.
3. In the app's **Settings > Secrets**, set:

   ```toml
   APP_ENV = "production"
   ```

4. Deploy. Community Cloud installs the app dependencies from `requirements.txt` and provides the hosted Streamlit URL.

The `.streamlit/secrets.toml.example` file shows the expected format. For local testing of a production configuration, copy it to `.streamlit/secrets.toml`; that local secrets file is ignored by Git. The `APP_ENV` process environment variable takes precedence over Streamlit secrets.

## Project files

- `app.py`: Streamlit entrypoint and environment selection.
- `requirements.txt`: Python dependencies for both local and hosted deployments.
- `.venv/`: local virtual environment created by the setup script; intentionally not committed.
- `scripts/`: Windows PowerShell setup and sandbox launch commands.
- `.streamlit/`: shared Streamlit settings and a safe-to-commit secrets example.