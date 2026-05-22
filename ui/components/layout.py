"""Page layout helpers and app chrome."""

from __future__ import annotations

from typing import Optional

import streamlit as st

from utils.constants import APP_NAME, APP_TAGLINE


def render_app_header(page_title: Optional[str] = None) -> None:
    """
    Render page header bar (section title only).

    Brand wordmark lives in the sidebar only — not duplicated here.
    """
    title = page_title or APP_NAME
    show_section_title = title != APP_NAME
    subtitle = APP_TAGLINE if not show_section_title else f"{APP_TAGLINE} · {title}"

    title_html = f"<h1>{title}</h1>" if show_section_title else f"<h1>{APP_NAME}</h1>"

    st.markdown(
        f"""
        <div class="sip-header">
            <div class="sip-header-inner">
                <div class="sip-header-copy">
                    {title_html}
                    <p>{subtitle}</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_panel(title: str, content_fn) -> None:
    """Wrap content in a styled panel container."""
    st.markdown(f'<div class="sip-panel"><div class="sip-panel-title">{title}</div>', unsafe_allow_html=True)
    content_fn()
    st.markdown("</div>", unsafe_allow_html=True)
