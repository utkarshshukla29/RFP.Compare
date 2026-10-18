import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


def get_app_environment() -> str:
    environment = os.getenv("APP_ENV")
    if environment is None:
        try:
            environment = st.secrets.get("APP_ENV", "sandbox")
        except StreamlitSecretNotFoundError:
            environment = "sandbox"

    environment = environment.strip().lower()
    if environment not in {"sandbox", "production"}:
        raise ValueError("APP_ENV must be either 'sandbox' or 'production'.")
    return environment


APP_ENV = get_app_environment()

st.set_page_config(page_title="Streamlit Starter", page_icon="S", layout="wide")

st.title("Streamlit Starter")
st.caption(f"Running in **{APP_ENV}** environment")
st.divider()

st.subheader("Your application starts here")
st.write("Replace this page with the workflows for your project.")

with st.expander("Runtime configuration"):
    st.code(f"APP_ENV={APP_ENV}", language="text")