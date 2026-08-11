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

        /* Chapter-based Learning Roadmap */
        .sip-roadmap-hero {{
            display: grid;
            grid-template-columns: minmax(0, 1.6fr) minmax(260px, 0.8fr);
            align-items: center;
            gap: 1.5rem;
            margin: 0.35rem 0 1.1rem 0;
            padding: 1.45rem 1.6rem;
            border-radius: 14px;
            background:
                radial-gradient(circle at 88% 18%, rgba(201, 162, 39, 0.28), transparent 32%),
                linear-gradient(135deg, #16324f 0%, #244f79 100%);
            color: white;
            box-shadow: 0 10px 28px rgba(30, 58, 95, 0.15);
        }}
        .sip-roadmap-eyebrow {{
            margin-bottom: 0.4rem;
            color: #f6d77b;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.1em;
        }}
        .sip-roadmap-hero-title {{
            max-width: 720px;
            font-size: 1.55rem;
            font-weight: 760;
            line-height: 1.2;
        }}
        .sip-roadmap-hero-text {{
            max-width: 720px;
            margin-top: 0.55rem;
            color: #dbe7f3;
            font-size: 0.94rem;
            line-height: 1.55;
        }}
        .sip-roadmap-hero-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.55rem;
        }}
        .sip-roadmap-hero-stats > div {{
            min-width: 0;
            padding: 0.7rem 0.45rem;
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.09);
            text-align: center;
        }}
        .sip-roadmap-hero-stats strong {{
            display: block;
            color: #f6d77b;
            font-size: 1.45rem;
            line-height: 1;
        }}
        .sip-roadmap-hero-stats span {{
            display: block;
            margin-top: 0.32rem;
            color: #e8eef5;
            font-size: 0.68rem;
            line-height: 1.2;
            text-transform: uppercase;
        }}
        .sip-roadmap-track {{
            display: grid;
            grid-template-columns: repeat(7, minmax(100px, 1fr));
            gap: 0.45rem;
            overflow-x: auto;
            margin: 0 0 1rem 0;
            padding: 0.2rem 0 0.65rem 0;
        }}
        .sip-roadmap-track-stop {{
            position: relative;
            min-width: 100px;
            padding-top: 2.15rem;
            color: {colors['text_muted']};
            font-size: 0.68rem;
            line-height: 1.25;
            text-align: center;
        }}
        .sip-roadmap-track-stop::before {{
            content: "";
            position: absolute;
            top: 0.93rem;
            left: -50%;
            width: 100%;
            height: 2px;
            background: {colors['card_border']};
        }}
        .sip-roadmap-track-stop:first-child::before {{
            display: none;
        }}
        .sip-roadmap-track-stop span {{
            position: absolute;
            z-index: 1;
            top: 0;
            left: 50%;
            width: 1.9rem;
            height: 1.9rem;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid {colors['accent']};
            border-radius: 50%;
            background: {colors['background']};
            color: {colors['primary']};
            font-size: 0.7rem;
            font-weight: 800;
        }}
        .sip-roadmap-track-stop small {{
            display: block;
            font-size: inherit;
        }}
        .sip-roadmap-chapter-head {{
            display: grid;
            grid-template-columns: 72px 1fr;
            align-items: center;
            gap: 1rem;
            margin-bottom: 0.9rem;
        }}
        .sip-roadmap-chapter-number {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 68px;
            height: 68px;
            border-radius: 14px;
            background: #1e3a5f;
            color: #f6d77b;
            font-size: 1.55rem;
            font-weight: 800;
        }}
        .sip-roadmap-chapter-label,
        .sip-roadmap-mini-label {{
            color: {colors['accent']};
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.08em;
        }}
        .sip-roadmap-chapter-title {{
            margin: 0.16rem 0 0.25rem 0;
            color: {colors['primary']};
            font-size: 1.35rem;
            font-weight: 760;
            line-height: 1.2;
        }}
        .sip-roadmap-chapter-summary {{
            color: {colors['text_muted']};
            font-size: 0.92rem;
            line-height: 1.45;
        }}
        .sip-roadmap-goal {{
            display: grid;
            gap: 0.22rem;
            margin: 0 0 1rem 0;
            padding: 0.85rem 1rem;
            border-left: 5px solid {colors['accent']};
            border-radius: 0 9px 9px 0;
            background: rgba(201, 162, 39, 0.1);
        }}
        .sip-roadmap-goal span,
        .sip-roadmap-checkpoint span {{
            color: {colors['accent']};
            font-size: 0.67rem;
            font-weight: 800;
            letter-spacing: 0.08em;
        }}
        .sip-roadmap-goal strong {{
            color: {colors['primary']};
            font-size: 0.98rem;
            line-height: 1.45;
        }}
        .sip-roadmap-objective-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.7rem;
            margin: 0.2rem 0 1.1rem 0;
        }}
        .sip-roadmap-objective {{
            min-height: 145px;
            padding: 0.9rem;
            border: 1px solid {colors['card_border']};
            border-radius: 11px;
            background: {colors['background']};
        }}
        .sip-roadmap-objective-number {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 2rem;
            height: 2rem;
            border-radius: 8px;
            background: #dbeafe;
            color: #1e3a5f;
            font-size: 0.72rem;
            font-weight: 800;
        }}
        .sip-roadmap-objective p {{
            margin: 0.65rem 0 0 0;
            color: inherit;
            font-size: 0.9rem;
            line-height: 1.48;
        }}
        .sip-roadmap-lesson-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.55rem;
            margin: 0.2rem 0 1rem 0;
        }}
        .sip-roadmap-lesson-step {{
            display: grid;
            grid-template-columns: 34px 1fr;
            align-items: center;
            gap: 0.65rem;
            padding: 0.62rem 0.7rem;
            border: 1px solid {colors['card_border']};
            border-radius: 9px;
        }}
        .sip-roadmap-lesson-dot {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            background: #1e3a5f;
            color: white;
            font-size: 0.72rem;
            font-weight: 800;
        }}
        .sip-roadmap-lesson-step small {{
            display: block;
            color: {colors['text_muted']};
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 0.05em;
        }}
        .sip-roadmap-lesson-step strong {{
            display: block;
            margin-top: 0.08rem;
            color: {colors['primary']};
            font-size: 0.85rem;
            line-height: 1.3;
        }}
        .sip-roadmap-connections {{
            margin: 0.4rem 0 1rem 0;
            padding: 0.85rem;
            border-radius: 10px;
            background: rgba(45, 106, 159, 0.07);
        }}
        .sip-roadmap-connection-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.55rem;
            margin-top: 0.55rem;
        }}
        .sip-roadmap-connection {{
            padding: 0.65rem;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.65);
            color: #334155;
            font-size: 0.8rem;
            line-height: 1.4;
        }}
        .sip-roadmap-checkpoint {{
            display: grid;
            grid-template-columns: 42px 1fr;
            gap: 0.75rem;
            align-items: start;
            margin: 0.5rem 0 0.85rem 0;
            padding: 0.9rem;
            border: 1px solid rgba(26, 127, 78, 0.3);
            border-radius: 11px;
            background: rgba(26, 127, 78, 0.07);
        }}
        .sip-roadmap-checkpoint-icon {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background: {colors['positive']};
            color: white;
            font-weight: 800;
        }}
        .sip-roadmap-checkpoint strong {{
            display: block;
            margin-top: 0.18rem;
            color: inherit;
            font-size: 0.91rem;
            line-height: 1.45;
        }}
        .sip-roadmap-tools {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.38rem;
            margin-top: 0.55rem;
        }}
        .sip-roadmap-tool {{
            display: inline-block;
            padding: 0.18rem 0.48rem;
            border: 1px solid {colors['card_border']};
            border-radius: 999px;
            background: {colors['background']};
            color: {colors['text_muted']};
            font-size: 0.68rem;
            font-weight: 700;
        }}

        /* Paced Lesson Library player */
        .sip-lesson-player-header {{
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1rem;
            margin: 0.15rem 0 0.45rem 0;
        }}
        .sip-lesson-player-pill {{
            display: inline-block;
            padding: 0.18rem 0.55rem;
            border: 1px solid {colors['accent']};
            border-radius: 999px;
            color: {colors['primary']};
            background: {colors['background']};
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }}
        .sip-lesson-player-count {{
            margin-top: 0.35rem;
            color: {colors['primary']};
            font-weight: 700;
            font-size: 1rem;
        }}
        .sip-lesson-player-progress-label {{
            color: #4b5563;
            font-size: 0.82rem;
            font-weight: 600;
        }}
        .sip-lesson-player-progress {{
            width: 100%;
            height: 0.55rem;
            overflow: hidden;
            border-radius: 999px;
            background: #e5e7eb;
            margin-bottom: 1rem;
        }}
        .sip-lesson-player-progress > div {{
            height: 100%;
            border-radius: inherit;
            background: {colors['accent']};
            transition: width 180ms ease-out;
        }}
        .sip-lesson-player-status {{
            min-height: 2.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #4b5563;
            font-size: 0.85rem;
            font-weight: 600;
            text-align: center;
        }}
        .sip-lesson-objective-note {{
            margin: -0.2rem 0 0.75rem 1.5rem;
            padding-left: 0.75rem;
            border-left: 3px solid {colors['card_border']};
            color: {colors['text_muted']};
            font-size: 0.9rem;
            line-height: 1.45;
        }}
        .sip-lesson-story {{
            display: grid;
            grid-template-columns: minmax(180px, 0.9fr) minmax(240px, 1.35fr);
            align-items: center;
            gap: 1.15rem;
            min-height: 165px;
            padding: 0.9rem 1rem;
            margin-bottom: 1rem;
            border: 1px solid {colors['card_border']};
            border-radius: 12px;
            background: {colors['background']};
        }}
        .sip-lesson-story-art {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 138px;
            border-radius: 9px;
            background: #f2f6fa;
        }}
        .sip-lesson-story-art svg {{
            width: 100%;
            max-width: 235px;
            height: 140px;
        }}
        .sip-lesson-story-kicker {{
            color: {colors['accent']};
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 0.08em;
        }}
        .sip-lesson-story-title {{
            margin: 0.3rem 0 0.45rem 0;
            color: {colors['primary']};
            font-size: 1.18rem;
            font-weight: 750;
            line-height: 1.25;
        }}
        .sip-lesson-story-takeaway {{
            color: #4b5563;
            font-size: 0.91rem;
            line-height: 1.5;
        }}
        .sip-story-card {{
            fill: #ffffff;
            stroke: {colors['primary']};
            stroke-width: 2;
        }}
        .sip-story-soft {{
            fill: #dbeafe;
            stroke: #93c5fd;
            stroke-width: 1.5;
        }}
        .sip-story-line {{
            fill: none;
            stroke: {colors['primary']};
            stroke-width: 4;
            stroke-linecap: round;
            stroke-linejoin: round;
        }}
        .sip-story-thin {{
            fill: none;
            stroke: {colors['primary']};
            stroke-width: 2.5;
            stroke-linecap: round;
        }}
        .sip-story-primary {{
            fill: {colors['primary']};
        }}
        .sip-story-accent {{
            fill: {colors['accent']};
        }}
        .sip-story-positive {{
            fill: {colors['positive']};
        }}
        .sip-story-person {{
            fill: #f6c7a5;
            stroke: {colors['primary']};
            stroke-width: 2;
        }}
        .sip-story-person-line {{
            fill: none;
            stroke: {colors['primary']};
            stroke-width: 4;
            stroke-linecap: round;
            stroke-linejoin: round;
        }}
        .sip-story-boundary {{
            fill: none;
            stroke: #94a3b8;
            stroke-width: 2;
            stroke-dasharray: 6 5;
        }}
        .sip-story-shield {{
            fill: #dbeafe;
            stroke: {colors['primary']};
            stroke-width: 3;
        }}
        .sip-story-check {{
            fill: none;
            stroke: {colors['positive']};
            stroke-width: 6;
            stroke-linecap: round;
            stroke-linejoin: round;
        }}
        .sip-story-down {{
            fill: none;
            stroke: {colors['negative']};
            stroke-width: 4;
            stroke-linecap: round;
        }}
        .sip-story-event {{
            fill: #fff4bf;
            stroke: #e4b100;
            stroke-width: 2;
        }}
        .sip-story-event-line {{
            fill: none;
            stroke: #e4b100;
            stroke-width: 2;
            stroke-dasharray: 5 4;
        }}
        .sip-story-cloud {{
            fill: #dbeafe;
            stroke: #64748b;
            stroke-width: 2;
        }}
        .sip-story-flow {{
            fill: none;
            stroke: {colors['accent']};
            stroke-width: 4;
            stroke-linecap: round;
            stroke-linejoin: round;
        }}

        @media (max-width: 780px) {{
            .sip-roadmap-hero {{
                grid-template-columns: 1fr;
            }}
            .sip-roadmap-objective-grid,
            .sip-roadmap-connection-grid {{
                grid-template-columns: 1fr;
            }}
            .sip-roadmap-lesson-grid {{
                grid-template-columns: 1fr;
            }}
            .sip-lesson-story {{
                grid-template-columns: 1fr;
            }}
            .sip-lesson-story-art {{
                min-height: 120px;
            }}
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
