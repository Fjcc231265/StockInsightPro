"""Global CSS styling for executive dashboard appearance."""

from __future__ import annotations

from utils.constants import COLORS


def get_custom_css(theme_id: str | None = None) -> str:
    """Return injected CSS for professional financial UI."""
    if theme_id is None:
        try:
            from services.settings_service import get_user_settings

            theme_id = get_user_settings().get("theme_id", "executive_blue")
        except Exception:  # noqa: BLE001
            theme_id = "executive_blue"
    try:
        from services.settings_service import get_theme_colors

        colors = get_theme_colors(theme_id)
    except Exception:  # noqa: BLE001 - fallback when settings unavailable at import
        colors = COLORS
    compact = False
    try:
        from services.settings_service import get_user_settings

        compact = bool(get_user_settings().get("compact_layout", False))
    except Exception:  # noqa: BLE001
        pass
    container_padding = "1rem 1.25rem" if compact else "1.5rem 2rem"
    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}

        .main .block-container {{
            padding-top: {container_padding.split()[0]};
            padding-bottom: 2rem;
            max-width: 1400px;
        }}

        /* App header (section title only — wordmark is in sidebar) */
        .sip-header {{
            background: linear-gradient(135deg, {colors['primary']} 0%, {colors['secondary']} 100%);
            color: white;
            padding: 1.15rem 1.5rem;
            border-radius: 10px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 14px rgba(30, 58, 95, 0.25);
        }}
        .sip-header-inner {{
            display: flex;
            align-items: center;
        }}
        .sip-header-copy {{
            flex: 1;
            min-width: 0;
        }}
        .sip-header h1 {{
            margin: 0;
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }}
        .sip-header p {{
            margin: 0.35rem 0 0 0;
            opacity: 0.9;
            font-size: 0.95rem;
        }}

        /* Metric cards */
        .sip-metric-card {{
            background: white;
            border: 1px solid {colors['card_border']};
            border-radius: 8px;
            padding: 0.85rem 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            height: 100%;
        }}
        .sip-metric-card .label {{
            color: {colors['text_muted']};
            font-size: 0.8rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .sip-metric-card .value {{
            color: {colors['primary']};
            font-size: 1.25rem;
            font-weight: 700;
            margin-top: 0.25rem;
            white-space: nowrap;
        }}
        .sip-metric-card .delta {{
            font-size: 0.85rem;
            white-space: nowrap;
        }}
        .sip-metric-card .delta.positive {{ color: {colors['positive']}; }}
        .sip-metric-card .delta.negative {{ color: {colors['negative']}; }}
        .sip-metric-card .delta.neutral {{ color: {colors['neutral']}; }}

        /* Compact native Streamlit metrics used inside panels */
        [data-testid="stMetricValue"] {{
            font-size: 1.2rem !important;
            white-space: nowrap;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 0.8rem !important;
        }}
        [data-testid="stMetricDelta"] {{
            font-size: 0.85rem !important;
        }}

        /* Section panels */
        .sip-panel {{
            background: white;
            border: 1px solid {colors['card_border']};
            border-radius: 8px;
            padding: 1.25rem;
            margin-bottom: 1rem;
        }}
        .sip-panel-title {{
            color: {colors['primary']};
            font-weight: 600;
            font-size: 1.1rem;
            border-bottom: 2px solid {colors['accent']};
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
        }}

        /* Regime lesson product highlights */
        .sip-regime-product {{
            color: {colors['primary']};
            font-weight: 700;
        }}
        .sip-lesson-body {{
            color: inherit;
            font-size: 1rem;
            line-height: 1.6;
            margin-bottom: 0.75rem;
        }}
        .sip-regime-caption {{
            color: #4b5563;
            font-size: 0.875rem;
            line-height: 1.45;
            margin-bottom: 0.5rem;
        }}
        .sip-education-anchor {{
            display: block;
            height: 0;
            margin: 0;
            padding: 0;
        }}
        .sip-education-page-title {{
            margin: 0 0 0.75rem 0;
            padding-top: 0;
            font-size: 1.35rem;
            font-weight: 600;
            line-height: 1.3;
            scroll-margin-top: 4.5rem;
        }}
        .sip-education-section-title {{
            margin: 1rem 0 0.5rem 0;
            padding-top: 0;
            font-size: 1.05rem;
            font-weight: 600;
            line-height: 1.35;
            scroll-margin-top: 4.5rem;
        }}

        /* Sidebar branding */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
        }}
        .sip-sidebar-wordmark-wrap {{
            margin-bottom: 0.5rem;
            padding: 6px 0;
        }}
        .sip-sidebar-wordmark {{
            width: 100%;
            max-width: 100%;
            height: auto;
            min-height: 52px;
            object-fit: contain;
            display: block;
        }}
        .sip-sidebar-brand-row {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.4rem;
            padding: 0.45rem 0 0.35rem 0;
        }}
        .sip-sidebar-logo {{
            width: 58px;
            height: 58px;
            object-fit: contain;
            border-radius: 10px;
            flex-shrink: 0;
        }}
        [data-testid="stSidebar"] .sip-sidebar-brand {{
            font-weight: 700;
            color: {colors['primary']};
            font-size: 1.35rem;
            line-height: 1.05;
            letter-spacing: -0.03em;
        }}
    </style>
    """
