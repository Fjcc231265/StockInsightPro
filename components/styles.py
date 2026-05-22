"""Global CSS styling for executive dashboard appearance."""

from utils.constants import COLORS


def get_custom_css() -> str:
    """Return injected CSS for professional financial UI."""
    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}

        .main .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }}

        /* App header (section title only — wordmark is in sidebar) */
        .sip-header {{
            background: linear-gradient(135deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
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
            border: 1px solid {COLORS['card_border']};
            border-radius: 8px;
            padding: 1rem 1.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            height: 100%;
        }}
        .sip-metric-card .label {{
            color: {COLORS['text_muted']};
            font-size: 0.8rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .sip-metric-card .value {{
            color: {COLORS['primary']};
            font-size: 1.5rem;
            font-weight: 700;
            margin-top: 0.25rem;
        }}
        .sip-metric-card .delta.positive {{ color: {COLORS['positive']}; }}
        .sip-metric-card .delta.negative {{ color: {COLORS['negative']}; }}
        .sip-metric-card .delta.neutral {{ color: {COLORS['neutral']}; }}

        /* Section panels */
        .sip-panel {{
            background: white;
            border: 1px solid {COLORS['card_border']};
            border-radius: 8px;
            padding: 1.25rem;
            margin-bottom: 1rem;
        }}
        .sip-panel-title {{
            color: {COLORS['primary']};
            font-weight: 600;
            font-size: 1.1rem;
            border-bottom: 2px solid {COLORS['accent']};
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
        }}

        /* Info / TODO callouts */
        .sip-todo {{
            background: #fff8e6;
            border-left: 4px solid {COLORS['accent']};
            padding: 0.75rem 1rem;
            border-radius: 0 6px 6px 0;
            font-size: 0.9rem;
            color: #5c4a1a;
            margin: 0.75rem 0;
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
            gap: 0.65rem;
            margin-bottom: 0.25rem;
        }}
        .sip-sidebar-logo {{
            width: 36px;
            height: 36px;
            object-fit: contain;
            border-radius: 8px;
        }}
        [data-testid="stSidebar"] .sip-sidebar-brand {{
            font-weight: 700;
            color: {COLORS['primary']};
            font-size: 1.05rem;
            line-height: 1.2;
        }}
    </style>
    """
