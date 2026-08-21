"""Simple shared-password gate for browser access (Mac or Streamlit Cloud)."""

from __future__ import annotations

import streamlit as st

from utils.config import get_app_password
from utils.constants import APP_NAME


def require_app_login() -> bool:
    """Show a password screen when APP_PASSWORD is configured.

    Returns True when the visitor may use the app.
    Returns False when the page should stop after showing the login form.
    """
    expected = get_app_password()
    if not expected:
        # No password configured → open access (typical on your Mac with only .env API key).
        return True

    if st.session_state.get("app_authenticated") is True:
        with st.sidebar:
            st.caption("Signed in")
            if st.button("Sign out", key="app_sign_out"):
                st.session_state.app_authenticated = False
                st.rerun()
        return True

    st.markdown(f"### {APP_NAME}")
    st.write("Enter the family password to open the app.")
    with st.form("app_login_form", clear_on_submit=False):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Open app", type="primary")

    if submitted:
        if password == expected:
            st.session_state.app_authenticated = True
            st.rerun()
        st.error("Incorrect password. Try again.")

    st.caption(
        "This password protects the website. It is separate from the Alpha Vantage data key, "
        "which stays hidden on the server."
    )
    return False
