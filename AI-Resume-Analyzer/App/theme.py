"""
theme.py — Presentation layer for the AI Resume Analyzer.

This module is purely front-end: CSS design tokens, the top navigation bar,
the hero section, the loading animations, the MORE menu and the admin data
tables. It does not touch any backend/data logic — App.py still owns all
parsing, scoring, database and auth code. Import and call these helpers
from App.py.
"""

import base64
import contextlib
import html as _html
import io
import os
import textwrap
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Root-cause fix for HTML showing up as visible raw text in the app.
#
# Markdown's spec treats any line indented 4+ spaces as a preformatted code
# block. Every HTML string built in this file lives inside indented Python
# functions, so a triple-quoted f-string like:
#
#     st.markdown(f"""
#         <div class="ara-hero">
#             ...
#         </div>
#         """, unsafe_allow_html=True)
#
# carries that 8-12 spaces of *literal* leading whitespace from the source
# code straight into the string Streamlit receives. Markdown then renders
# those lines as a literal code block instead of parsing them as HTML — the
# exact bug where `</div>`, `<video>` etc. showed up as visible page text.
#
# Rather than hand-fix the ~40 call sites across theme.py and App.py (all of
# which have this same latent issue, whether or not it has visibly
# triggered yet), this wraps st.markdown itself: any call passing
# unsafe_allow_html=True has its body run through textwrap.dedent() first,
# then has any blank (or whitespace-only) line removed.
#
# The blank-line step matters for a second, related reason: CommonMark
# treats a line containing only spaces/tabs as "blank", and a blank line
# inside a raw-HTML block ends that block early — Markdown parsing then
# resumes fresh on whatever comes after, re-applying the same 4-space rule
# to it. This bites specifically when an f-string interpolates a
# conditionally-empty variable (e.g. `{stat_html}` evaluating to `""`): the
# line becomes pure indentation with nothing else on it — still "blank" by
# the spec even though it isn't literally empty — silently splitting one
# HTML block into two and reintroducing the exact same visible-raw-tags bug
# for everything after the split, even though the very first line of the
# whole string still starts safely at column 0.
#
# dedent() only strips whitespace common to every line, and dropping blank
# lines can't damage intentional structure either — none of this file's
# injected HTML relies on blank lines or whitespace-sensitive content (no
# <pre> text blocks), so both are safe, general-purpose transformations.
# Since `streamlit` is a single shared module, patching st.markdown here
# (theme.py is imported before App.py does any rendering) fixes every call
# site in both files, present and future, from one place.
_original_st_markdown = st.markdown


def _dedented_markdown(body, *args, **kwargs):
    if kwargs.get('unsafe_allow_html') and isinstance(body, str) and '\n' in body:
        body = textwrap.dedent(body)
        body = '\n'.join(line for line in body.split('\n') if line.strip() != '')
    return _original_st_markdown(body, *args, **kwargs)


st.markdown = _dedented_markdown

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
LOADER_VIDEO_PATH = os.path.join(ASSETS_DIR, 'loader.mp4')

NAV_ITEMS = ["User", "Feedback", "Admin", "About"]

# Minimum time the "AI is analyzing your resume" overlay stays on screen, even
# if the parser finishes sooner. If the parser takes longer, the overlay simply
# stays up until it is done — no artificial delay is added on top.
MIN_ANALYSIS_SECONDS = 0

# The loading video is inlined as base64 once per process instead of on every
# rerun (the file is ~95 KB, so this keeps reruns cheap).
_VIDEO_B64 = None


def _loader_video_b64():
    global _VIDEO_B64
    if _VIDEO_B64 is None:
        if os.path.exists(LOADER_VIDEO_PATH):
            with open(LOADER_VIDEO_PATH, 'rb') as f:
                _VIDEO_B64 = base64.b64encode(f.read()).decode('utf-8')
        else:
            _VIDEO_B64 = ''
    return _VIDEO_B64


def _loader_media(css_class):
    """Video element for the loaders, with a CSS-only orb fallback."""
    b64 = _loader_video_b64()
    if b64:
        return (
            f'<video class="{css_class}" autoplay muted playsinline loop>'
            f'<source src="data:video/mp4;base64,{b64}" type="video/mp4"></video>'
        )
    return f'<div class="{css_class} ara-orb"></div>'


# ---------------------------------------------------------------------------
# Design tokens / global CSS
# ---------------------------------------------------------------------------

def inject_theme():
    """Inject the global stylesheet. Call once, right after set_page_config."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

        :root{
            --bg:#F5F3EF;
            --surface:#FFFFFF;
            --surface-2:#FAF8F5;
            --ink:#141414;
            --ink-muted:#6B6B6B;
            --accent:#8C78BD;
            --accent-dark:#715B9D;
            --line:#E7E3DC;
            --radius:14px;
            --radius-sm:10px;
            --shadow:0 8px 24px rgba(20,20,20,0.06);
            --shadow-lg:0 16px 40px rgba(20,20,20,0.10);
            --success:#2F7A4F;
            --warn:#B4530A;
            --overlay:rgba(245,243,239,0.94);
        }

        /* ---- Dark palette. Applied by the MORE menu, which sets
           data-ara-theme="light|dark|system" on <html> and persists it in
           localStorage. "system" follows the OS via prefers-color-scheme. ---- */
        html[data-ara-theme="dark"]{
            --bg:#111113;
            --surface:#1A1A1D;
            --surface-2:#202024;
            --ink:#F2F0ED;
            --ink-muted:#A5A29C;
            --accent:#BCA8E8;
            --accent-dark:#D0BEF4;
            --line:#2E2E33;
            --shadow:0 8px 24px rgba(0,0,0,0.45);
            --shadow-lg:0 16px 40px rgba(0,0,0,0.55);
            --success:#5FBF8B;
            --warn:#E5903F;
            --overlay:rgba(17,17,19,0.94);
        }
        @media (prefers-color-scheme: dark){
            html[data-ara-theme="system"]{
                --bg:#111113;
                --surface:#1A1A1D;
                --surface-2:#202024;
                --ink:#F2F0ED;
                --ink-muted:#A5A29C;
                --accent:#BCA8E8;
                --accent-dark:#D0BEF4;
                --line:#2E2E33;
                --shadow:0 8px 24px rgba(0,0,0,0.45);
                --shadow-lg:0 16px 40px rgba(0,0,0,0.55);
                --success:#5FBF8B;
                --warn:#E5903F;
                --overlay:rgba(17,17,19,0.94);
            }
        }

        html, body, [class*="css"]{
            font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;
        }
        .stApp{
            background:var(--bg);
            color:var(--ink);
            transition:background .25s ease, color .25s ease;
        }

        h1,h2,h3,h4,h5,h6{
            font-family:'Space Grotesk','Inter',sans-serif !important;
            color:var(--ink) !important;
            letter-spacing:-0.02em;
        }

        /* Text that uses Streamlit's own colour has to follow the token when
           the dark palette is active. */
        html[data-ara-theme="dark"] [data-testid="stMarkdownContainer"],
        html[data-ara-theme="dark"] [data-testid="stMarkdownContainer"] p,
        html[data-ara-theme="dark"] [data-testid="stMarkdownContainer"] li,
        html[data-ara-theme="dark"] [data-testid="stWidgetLabel"] p,
        html[data-ara-theme="dark"] [data-testid="stFileUploaderDropzone"] span,
        html[data-ara-theme="dark"] [data-testid="stFileUploaderDropzone"] small{
            color:var(--ink) !important;
        }
        html[data-ara-theme="dark"] .stTextInput input,
        html[data-ara-theme="dark"] .stTextArea textarea{
            color:var(--ink) !important;
            background:var(--surface) !important;
        }
        html[data-ara-theme="dark"] [data-testid="stAlert"]{
            background:var(--surface-2) !important;
        }
        html[data-ara-theme="dark"] [data-testid="stAlert"] *{
            color:var(--ink) !important;
        }
        html[data-ara-theme="dark"] [data-testid="stText"],
        html[data-ara-theme="dark"] [data-testid="stText"] *{
            color:var(--ink) !important;
        }
        /* Button labels are internally rendered through the same
           stMarkdownContainer/<p> pipeline as regular text, so the rule
           above also (incorrectly) matched them, force-setting every
           button's label to var(--ink) regardless of that button's own
           background — invisible on any button whose own background is
           ALSO var(--ink) (our active nav pill, Analyze/Login, etc., since
           .stButton>button and the active nav state both correctly set
           color:var(--bg) for exactly that reason). This targets the label
           text itself (required — color is only inherited from the button
           otherwise, and inherited values lose to any rule that matches
           the element directly) and hands color back to whatever the
           button's own (already theme-correct) styling specifies. */
        html[data-ara-theme="dark"] button [data-testid="stMarkdownContainer"],
        html[data-ara-theme="dark"] button [data-testid="stMarkdownContainer"] p,
        html[data-ara-theme="dark"] button [data-testid="stMarkdownContainer"] li{
            color:inherit !important;
        }
        @media (prefers-color-scheme: dark){
            html[data-ara-theme="system"] [data-testid="stMarkdownContainer"],
            html[data-ara-theme="system"] [data-testid="stMarkdownContainer"] p,
            html[data-ara-theme="system"] [data-testid="stMarkdownContainer"] li,
            html[data-ara-theme="system"] [data-testid="stWidgetLabel"] p,
            html[data-ara-theme="system"] [data-testid="stFileUploaderDropzone"] span,
            html[data-ara-theme="system"] [data-testid="stFileUploaderDropzone"] small{
                color:var(--ink) !important;
            }
            html[data-ara-theme="system"] .stTextInput input,
            html[data-ara-theme="system"] .stTextArea textarea{
                color:var(--ink) !important;
                background:var(--surface) !important;
            }
            html[data-ara-theme="system"] [data-testid="stAlert"]{
                background:var(--surface-2) !important;
            }
            html[data-ara-theme="system"] [data-testid="stAlert"] *{
                color:var(--ink) !important;
            }
            html[data-ara-theme="system"] [data-testid="stText"],
            html[data-ara-theme="system"] [data-testid="stText"] *{
                color:var(--ink) !important;
            }
            html[data-ara-theme="system"] button [data-testid="stMarkdownContainer"],
            html[data-ara-theme="system"] button [data-testid="stMarkdownContainer"] p,
            html[data-ara-theme="system"] button [data-testid="stMarkdownContainer"] li{
                color:inherit !important;
            }
        }

        /* ---- Hide Streamlit dev/deploy chrome (not part of the product UI) ---- */
        #MainMenu{visibility:hidden;}
        footer{visibility:hidden;}
        [data-testid="stToolbar"]{visibility:hidden;height:0;position:fixed;}
        [data-testid="stDecoration"]{display:none;}
        [data-testid="stStatusWidget"]{visibility:hidden;}
        .stDeployButton{display:none;}

        /* ---- Layout ----
           padding-top nudges the page (and with it the top nav) a little
           further down from the browser chrome. */
        .block-container{
            padding-top:2.75rem;
            max-width:1180px;
        }

        /* ---- Buttons ---- */
        .stButton>button, .stFormSubmitButton>button{
            background:var(--ink);
            color:var(--bg);
            border:none;
            border-radius:999px;
            padding:0.6rem 1.4rem;
            font-weight:600;
            font-family:'Space Grotesk',sans-serif;
            transition:transform .15s ease, background .15s ease, box-shadow .15s ease;
            box-shadow:var(--shadow);
        }
        .stButton>button:hover, .stFormSubmitButton>button:hover{
            background:var(--accent);
            color:#fff;
            transform:translateY(-2px);
            box-shadow:var(--shadow-lg);
        }

        /* ---- Inputs ---- */
        .stTextInput>div>div>input,
        .stTextArea textarea,
        [data-testid="stFileUploaderDropzone"]{
            border-radius:var(--radius-sm) !important;
            border:1.5px solid var(--line) !important;
            background:var(--surface) !important;
        }
        .stTextInput>div>div>input:focus{
            border-color:var(--accent) !important;
            box-shadow:0 0 0 3px rgba(140,120,189,0.15) !important;
        }

        [data-testid="stFileUploaderDropzone"]{
            padding:1.4rem !important;
        }
        [data-testid="stFileUploaderDropzone"] button{
            background:var(--accent) !important;
            color:#fff !important;
            border-radius:999px !important;
        }

        /* ---- Alerts as cards ---- */
        [data-testid="stAlert"]{
            border-radius:var(--radius-sm);
            border:1px solid var(--line);
            box-shadow:var(--shadow);
        }

        /* ---- Progress bar ---- */
        .stProgress > div > div > div > div{
            background-color:var(--accent) !important;
            border-radius:999px;
        }
        .stProgress > div > div > div{
            background-color:var(--line) !important;
            border-radius:999px;
        }

        /* ---- Section cards ---- */
        .ara-card{
            background:var(--surface);
            border:1px solid var(--line);
            border-radius:var(--radius);
            padding:1.5rem 1.75rem;
            box-shadow:var(--shadow);
            margin-bottom:1.25rem;
        }

        /* ---- Top navigation ----
           Streamlit's st.container(key=...) renders as a real wrapper div
           with class "st-key-<key>", so (unlike a bare st.markdown div) this
           selector genuinely contains the nav buttons rendered inside it. */
        .st-key-ara_navbar{
            position:relative;
            display:flex;
            align-items:center;
            justify-content:space-between;
            padding:0.6rem 1.2rem;
            background:var(--surface);
            border:1px solid var(--line);
            border-radius:999px;
            box-shadow:var(--shadow);
            margin-top:0.5rem;
            margin-bottom:1.75rem;
        }
        .st-key-ara_navbar [data-testid="stHorizontalBlock"]{
            align-items:center;
        }
        .ara-brand{
            font-family:'Space Grotesk',sans-serif;
            font-weight:700;
            font-size:1.1rem;
            color:var(--ink);
            display:flex;
            align-items:center;
            gap:.5rem;
            white-space:nowrap;
        }
        .ara-brand .dot{color:var(--accent);}
        .st-key-ara_navbar button{
            background:transparent;
            color:var(--ink);
            box-shadow:none;
            font-weight:600;
            padding:0.45rem 0.9rem;
            border:1px solid transparent;
        }
        .st-key-ara_navbar button:hover{
            background:var(--bg);
            color:var(--accent);
            transform:none;
        }
        /* Active nav item: rendered with type="primary" so it gets a distinct kind */
        .st-key-ara_navbar button[kind="primary"],
        .st-key-ara_navbar button[data-testid="baseButton-primary"]{
            background:var(--ink) !important;
            color:var(--bg) !important;
            box-shadow:var(--shadow) !important;
        }
        .st-key-ara_navbar button[kind="primary"]:hover,
        .st-key-ara_navbar button[data-testid="baseButton-primary"]:hover{
            background:var(--accent) !important;
            color:#fff !important;
        }
        /* MORE hamburger — round icon button rather than a text pill */
        .st-key-nav_more{max-width:44px; margin-left:auto;}
        .st-key-nav_more button{
            font-size:1.05rem;
            padding:0.5rem 0;
            border-radius:999px;
            width:40px;
            height:40px;
            display:flex;
            align-items:center;
            justify-content:center;
        }

        /* ---- MORE dropdown host ----
           The panel itself lives in a component iframe so it can talk to the
           browser (theme, print, screen capture). The host is taken out of
           flow and anchored under the MORE button so the panel overlays the
           page instead of pushing content down. */
        .st-key-ara_more_host{
            position:absolute;
            top:calc(100% + 10px);
            right:6px;
            width:306px;
            z-index:9999;
        }
        .st-key-ara_more_host iframe{
            width:306px !important;
            border:none !important;
            background:transparent !important;
            color-scheme:normal;
        }
        .st-key-ara_more_host [data-testid="stElementContainer"],
        .st-key-ara_more_host [data-testid="stVerticalBlock"]{
            gap:0 !important;
        }
        /* Off-screen relays: the panel's JS clicks these so Rerun / Clear cache
           run through normal Streamlit reruns instead of a page reload. */
        .st-key-ara_relays{
            position:fixed;
            left:-10000px;
            top:0;
            width:1px;
            height:1px;
            overflow:hidden;
        }

        /* ---- Hero ---- */
        .ara-hero{
            padding:3.2rem 2.5rem;
            background:linear-gradient(180deg, var(--surface) 0%, var(--bg) 100%);
            border:1px solid var(--line);
            border-radius:24px;
            box-shadow:var(--shadow);
            margin-bottom:2rem;
        }
        .ara-hero-grid{
            display:flex;
            align-items:center;
            gap:2.5rem;
        }
        .ara-hero-copy{flex:1 1 55%; min-width:0;}
        .ara-hero-media{
            flex:0 0 auto;
            width:min(300px, 34vw);
        }
        .ara-hero-media .ara-hero-video{
            width:100%;
            aspect-ratio:1/1;
            object-fit:cover;
            border-radius:22px;
            box-shadow:var(--shadow-lg);
            display:block;
        }
        .ara-eyebrow{
            display:inline-block;
            font-family:'Space Grotesk',sans-serif;
            font-weight:600;
            font-size:0.78rem;
            letter-spacing:0.12em;
            text-transform:uppercase;
            color:var(--accent-dark);
            background:rgba(140,120,189,0.10);
            padding:0.3rem 0.8rem;
            border-radius:999px;
            margin-bottom:1rem;
        }
        .ara-hero h1{
            font-size:clamp(2.1rem, 5vw, 3.6rem);
            line-height:1.02;
            margin:0 0 1rem 0;
        }
        .ara-hero h1 .accent{color:var(--accent);}
        .ara-hero p{
            color:var(--ink-muted);
            font-size:1.05rem;
            max-width:560px;
            margin-bottom:1.6rem;
        }
        .ara-hero-stats{
            display:flex;
            gap:2.5rem;
            margin-top:2rem;
            flex-wrap:wrap;
        }
        .ara-hero-stats div{min-width:120px;}
        .ara-hero-stats .num{
            font-family:'Space Grotesk',sans-serif;
            font-weight:700;
            font-size:1.6rem;
            color:var(--ink);
        }
        .ara-hero-stats .lbl{
            color:var(--ink-muted);
            font-size:0.85rem;
        }

        /* ---- Data tables (admin) ----
           One shared shell for "User's Data" and "User's Feedback Data" so the
           two sections share container, spacing, typography and radius. */
        .ara-table-card{
            background:var(--surface);
            border:1px solid var(--line);
            border-radius:var(--radius);
            box-shadow:var(--shadow);
            margin:0 0 1.75rem 0;
            overflow:hidden;
        }

        /* ---- Interactive admin table cards ----
           render_admin_table() gives each table its own key (ara_admin_user_data,
           ara_admin_feedback, ...), so match on the shared prefix rather than a
           single fixed class. */
        div[class*="st-key-ara_admin_"]{
            background:var(--surface);
            border:1px solid var(--line);
            border-radius:var(--radius);
            box-shadow:var(--shadow);
            padding:1.2rem 1.35rem 1.4rem 1.35rem;
            margin:0 0 1.75rem 0;
        }
        .ara-admin-title{
            font-family:'Space Grotesk',sans-serif;
            font-weight:700;
            font-size:1rem;
            letter-spacing:0.07em;
            text-transform:uppercase;
            color:var(--ink);
            padding-top:0.3rem;
        }
        .ara-count-right{text-align:right; padding-top:0.35rem;}

        /* ---- Analytics: KPI cards, stat strip, missing-section chips ---- */
        .ara-kpi{
            background:var(--surface);
            border:1px solid var(--line);
            border-radius:var(--radius-sm);
            box-shadow:var(--shadow);
            padding:1rem 1.1rem;
            text-align:left;
        }
        .ara-kpi-value{
            font-family:'Space Grotesk',sans-serif;
            font-weight:700;
            font-size:1.5rem;
            color:var(--ink);
            line-height:1.1;
        }
        .ara-kpi-label{
            margin-top:0.3rem;
            font-size:0.78rem;
            color:var(--ink-muted);
            letter-spacing:0.03em;
        }
        .ara-stat{
            text-align:center;
            padding:0.6rem 0.4rem;
            border-right:1px solid var(--line);
        }
        .ara-stat:last-child{border-right:none;}
        .ara-stat-value{
            display:block;
            font-family:'Space Grotesk',sans-serif;
            font-weight:700;
            font-size:1.2rem;
            color:var(--ink);
        }
        .ara-stat-label{
            display:block;
            font-size:0.74rem;
            color:var(--ink-muted);
            margin-top:0.15rem;
        }

        /* ---- Single-value result card (Experience Level, Predicted Job
           Field on the User page — one real data point, not a chart) ---- */
        .ara-value-card{
            background:var(--surface);
            border:1px solid var(--line);
            border-radius:var(--radius);
            box-shadow:var(--shadow);
            padding:1.4rem 1.5rem;
            text-align:center;
            display:flex;
            flex-direction:column;
            align-items:center;
            justify-content:center;
            height:100%;
            min-height:220px;
        }
        .ara-value-card-label{
            font-family:'Space Grotesk',sans-serif;
            font-size:0.78rem;
            font-weight:600;
            letter-spacing:0.08em;
            text-transform:uppercase;
            color:var(--ink-muted);
            margin-bottom:0.7rem;
        }
        .ara-value-card-value{
            font-family:'Space Grotesk',sans-serif;
            font-weight:700;
            font-size:1.6rem;
            color:var(--ink);
            line-height:1.25;
        }
        .ara-value-card-icon{
            display:block;
            font-size:2.4rem;
            margin-bottom:0.5rem;
        }
        .ara-value-card-sub{
            margin-top:0.6rem;
            font-size:0.85rem;
            color:var(--ink-muted);
        }

        /* ---- Feedback-received animation (replaces st.balloons()) ---- */
        .ara-feedback-received{
            position:relative;
            display:flex;
            flex-direction:column;
            align-items:center;
            justify-content:center;
            padding:2rem 1rem 1.6rem 1rem;
            text-align:center;
        }
        .ara-feedback-check{
            width:64px;
            height:64px;
            border-radius:50%;
            background:var(--success);
            display:flex;
            align-items:center;
            justify-content:center;
            box-shadow:0 0 0 0 rgba(47,122,79,0.35);
            animation:ara-check-pop .45s cubic-bezier(.2,.9,.3,1.3) both,
                      ara-check-pulse 1.8s ease-out .45s 2;
        }
        .ara-feedback-check svg{width:30px; height:30px;}
        .ara-feedback-check path{
            stroke:#fff; stroke-width:3.5; fill:none;
            stroke-linecap:round; stroke-linejoin:round;
            stroke-dasharray:24; stroke-dashoffset:24;
            animation:ara-check-draw .35s ease .35s forwards;
        }
        @keyframes ara-check-pop{
            0%{transform:scale(0.4); opacity:0;}
            100%{transform:scale(1); opacity:1;}
        }
        @keyframes ara-check-draw{ to{stroke-dashoffset:0;} }
        @keyframes ara-check-pulse{
            0%{box-shadow:0 0 0 0 rgba(47,122,79,0.35);}
            100%{box-shadow:0 0 0 18px rgba(47,122,79,0);}
        }
        .ara-feedback-title{
            margin-top:1rem;
            font-family:'Space Grotesk',sans-serif;
            font-weight:700;
            font-size:1.15rem;
            color:var(--ink);
        }
        .ara-feedback-sub{
            margin-top:0.3rem;
            font-size:0.88rem;
            color:var(--ink-muted);
        }
        .ara-feedback-stars{
            margin-top:0.9rem;
            display:flex;
            gap:0.35rem;
            font-size:1.3rem;
        }
        .ara-feedback-stars span{
            display:inline-block;
            color:#F5A623;
            opacity:0;
            transform:translateY(6px) scale(0.6);
            animation:ara-star-in .4s ease forwards;
        }
        .ara-feedback-stars span:nth-child(1){animation-delay:.55s;}
        .ara-feedback-stars span:nth-child(2){animation-delay:.65s;}
        .ara-feedback-stars span:nth-child(3){animation-delay:.75s;}
        .ara-feedback-stars span:nth-child(4){animation-delay:.85s;}
        .ara-feedback-stars span:nth-child(5){animation-delay:.95s;}
        @keyframes ara-star-in{
            to{opacity:1; transform:translateY(0) scale(1);}
        }
        @media (prefers-reduced-motion: reduce){
            .ara-feedback-check, .ara-feedback-check path, .ara-feedback-stars span{
                animation:none !important;
                opacity:1 !important;
                transform:none !important;
                stroke-dashoffset:0 !important;
            }
        }
        .ara-chip-row{
            display:flex;
            flex-wrap:wrap;
            gap:0.5rem;
        }
        .ara-chip{
            display:inline-block;
            padding:0.4rem 0.85rem;
            border-radius:999px;
            background:rgba(180,83,10,0.10);
            border:1px solid rgba(180,83,10,0.26);
            color:var(--warn);
            font-size:0.85rem;
            font-weight:600;
            font-family:'Space Grotesk',sans-serif;
        }
        .ara-analytics-heading{
            font-family:'Space Grotesk',sans-serif;
            font-weight:700;
            font-size:1.3rem;
            letter-spacing:-0.01em;
            color:var(--ink);
            margin:1.6rem 0 0.9rem 0;
        }
        div[class*="st-key-ara_admin_"] [data-testid="stElementToolbar"]{
            /* keep the built-in dataframe toolbar (search/download icons)
               from fighting with our own action bar underneath */
            opacity:0.85;
        }
        .ara-table-head{
            display:flex;
            align-items:baseline;
            justify-content:space-between;
            gap:1rem;
            flex-wrap:wrap;
            padding:1.15rem 1.35rem 0.9rem 1.35rem;
            border-bottom:1px solid var(--line);
        }
        .ara-table-head h4{
            margin:0;
            font-size:1rem;
            letter-spacing:0.08em;
            text-transform:uppercase;
        }
        .ara-table-head .ara-count{
            font-size:0.82rem;
            color:var(--ink-muted);
            font-family:'Space Grotesk',sans-serif;
            font-weight:600;
        }
        .ara-table-scroll{overflow-x:auto;}
        table.ara-table{
            width:100%;
            border-collapse:collapse;
            font-size:0.88rem;
        }
        table.ara-table th{
            text-align:left;
            font-family:'Space Grotesk',sans-serif;
            font-weight:600;
            font-size:0.74rem;
            letter-spacing:0.09em;
            text-transform:uppercase;
            color:var(--ink-muted);
            background:var(--surface-2);
            padding:0.7rem 1rem;
            white-space:nowrap;
            border-bottom:1px solid var(--line);
        }
        table.ara-table td{
            padding:0.75rem 1rem;
            border-bottom:1px solid var(--line);
            color:var(--ink);
            vertical-align:top;
        }
        table.ara-table tbody tr:last-child td{border-bottom:none;}
        table.ara-table tbody tr:hover td{background:var(--surface-2);}
        table.ara-table .ara-primary{
            font-weight:600;
            font-family:'Space Grotesk',sans-serif;
            white-space:nowrap;
        }
        table.ara-table .ara-sub{
            display:block;
            color:var(--ink-muted);
            font-size:0.78rem;
            margin-top:2px;
        }
        table.ara-table .ara-num{
            font-variant-numeric:tabular-nums;
            white-space:nowrap;
        }
        .ara-badge{
            display:inline-block;
            padding:0.18rem 0.6rem;
            border-radius:999px;
            font-size:0.74rem;
            font-weight:600;
            font-family:'Space Grotesk',sans-serif;
            white-space:nowrap;
            border:1px solid var(--line);
            background:var(--surface-2);
            color:var(--ink-muted);
        }
        .ara-badge.is-accent{
            background:rgba(140,120,189,0.12);
            border-color:rgba(140,120,189,0.28);
            color:var(--accent-dark);
        }
        .ara-badge.is-good{
            background:rgba(47,122,79,0.12);
            border-color:rgba(47,122,79,0.26);
            color:var(--success);
        }
        .ara-badge.is-warn{
            background:rgba(180,83,10,0.12);
            border-color:rgba(180,83,10,0.26);
            color:var(--warn);
        }
        /* Row-level "More" disclosure — native <details>, so no extra rerun. */
        details.ara-more-row{display:inline-block;}
        details.ara-more-row > summary{
            list-style:none;
            cursor:pointer;
            display:inline-block;
            padding:0.28rem 0.75rem;
            border:1px solid var(--line);
            border-radius:999px;
            font-family:'Space Grotesk',sans-serif;
            font-weight:600;
            font-size:0.76rem;
            color:var(--ink);
            background:var(--surface);
            white-space:nowrap;
            transition:background .15s ease, color .15s ease, border-color .15s ease;
        }
        details.ara-more-row > summary::-webkit-details-marker{display:none;}
        details.ara-more-row > summary:hover{
            background:var(--accent);
            border-color:var(--accent);
            color:#fff;
        }
        details.ara-more-row[open] > summary{
            background:var(--ink);
            border-color:var(--ink);
            color:var(--bg);
        }
        .ara-more-body{
            margin-top:0.6rem;
            padding:0.75rem 0.9rem;
            border:1px solid var(--line);
            border-radius:var(--radius-sm);
            background:var(--surface-2);
            min-width:260px;
            max-width:520px;
        }
        .ara-more-body dl{margin:0;}
        .ara-more-body dt{
            font-family:'Space Grotesk',sans-serif;
            font-size:0.68rem;
            letter-spacing:0.08em;
            text-transform:uppercase;
            color:var(--ink-muted);
            margin-top:0.55rem;
        }
        .ara-more-body dt:first-child{margin-top:0;}
        .ara-more-body dd{
            margin:0.15rem 0 0 0;
            font-size:0.82rem;
            color:var(--ink);
            word-break:break-word;
        }
        .ara-empty{
            padding:1.6rem 1.35rem;
            color:var(--ink-muted);
            font-size:0.9rem;
        }
        .ara-table-foot{
            padding:0.85rem 1.35rem;
            border-top:1px solid var(--line);
            background:var(--surface-2);
            font-size:0.84rem;
        }
        .ara-table-foot a{
            color:var(--accent-dark);
            font-weight:600;
            text-decoration:none;
            font-family:'Space Grotesk',sans-serif;
        }
        .ara-table-foot a:hover{text-decoration:underline;}

        /* ---- Clear Cache broom overlay ----
           Same overlay/blur treatment as the AI analysis overlay, shown
           briefly and unconditionally after a Clear Cache action. */
        .ara-broom-overlay{
            position:fixed;
            inset:0;
            z-index:999997;
            display:flex;
            align-items:center;
            justify-content:center;
            flex-direction:column;
            background:var(--overlay);
            -webkit-backdrop-filter:blur(8px);
            backdrop-filter:blur(8px);
            animation:ara-fade-in .25s ease both;
            padding:1.5rem;
            text-align:center;
        }
        .ara-broom-stage{
            position:relative;
            width:clamp(160px, 32vmin, 260px);
            height:clamp(160px, 32vmin, 260px);
            display:flex;
            align-items:center;
            justify-content:center;
        }
        .ara-broom-emoji{
            font-size:clamp(84px, 18vmin, 150px);
            animation:ara-broom-sweep 1.1s ease-in-out infinite;
            filter:drop-shadow(0 12px 18px rgba(0,0,0,0.18));
        }
        @keyframes ara-broom-sweep{
            0%{transform:rotate(-14deg) translateX(-8%);}
            50%{transform:rotate(10deg) translateX(8%);}
            100%{transform:rotate(-14deg) translateX(-8%);}
        }
        .ara-broom-dust{
            position:absolute;
            bottom:18%;
            width:10px;
            height:10px;
            border-radius:50%;
            background:var(--ink-muted);
            opacity:0;
            animation:ara-dust 1.1s ease-in-out infinite;
        }
        .ara-broom-dust.d1{left:20%; animation-delay:0s;}
        .ara-broom-dust.d2{left:38%; width:7px; height:7px; animation-delay:.2s;}
        .ara-broom-dust.d3{left:55%; width:5px; height:5px; animation-delay:.4s;}
        @keyframes ara-dust{
            0%{opacity:0; transform:translate(0,0) scale(1);}
            25%{opacity:.6;}
            100%{opacity:0; transform:translate(26px,-22px) scale(0.4);}
        }
        .ara-broom-title{
            margin-top:1.8rem;
            font-family:'Space Grotesk',sans-serif;
            font-weight:700;
            font-size:clamp(1.1rem, 2.4vw, 1.6rem);
            color:var(--ink);
        }
        .ara-broom-sub{
            margin-top:0.4rem;
            color:var(--ink-muted);
            font-size:0.9rem;
            max-width:min(420px, 84vw);
        }

        /* ---- AI analysis overlay ----
           Stays up for as long as the parser is actually working. */
        .ara-analysis-overlay{
            position:fixed;
            inset:0;
            z-index:999998;
            display:flex;
            align-items:center;
            justify-content:center;
            flex-direction:column;
            background:var(--overlay);
            -webkit-backdrop-filter:blur(8px);
            backdrop-filter:blur(8px);
            animation:ara-fade-in .3s ease both;
            padding:1.5rem;
            text-align:center;
        }
        @keyframes ara-fade-in{from{opacity:0;}to{opacity:1;}}
        .ara-stage{
            position:relative;
            display:flex;
            align-items:center;
            justify-content:center;
            width:clamp(220px, 48vmin, 460px);
            height:clamp(220px, 48vmin, 460px);
        }
        .ara-stage .ara-analysis-media{
            width:100%;
            height:100%;
            object-fit:cover;
            border-radius:32px;
            box-shadow:var(--shadow-lg);
            position:relative;
            z-index:2;
        }
        .ara-orb{
            background:conic-gradient(from 0deg, var(--accent), #FFC46B, var(--accent-dark), var(--accent));
            animation:ara-spin 3.6s linear infinite;
        }
        @keyframes ara-spin{to{transform:rotate(360deg);}}
        .ara-ring{
            position:absolute;
            inset:-6%;
            border-radius:38px;
            border:2px solid var(--accent);
            opacity:0;
            z-index:1;
            animation:ara-ring 2.8s ease-out infinite;
        }
        .ara-ring.r2{animation-delay:.9s;}
        .ara-ring.r3{animation-delay:1.8s;}
        @keyframes ara-ring{
            0%{transform:scale(0.92); opacity:.55;}
            100%{transform:scale(1.25); opacity:0;}
        }
        .ara-scan{
            position:absolute;
            left:4%;
            right:4%;
            height:3px;
            border-radius:999px;
            background:linear-gradient(90deg, transparent, var(--accent), transparent);
            box-shadow:0 0 18px 3px rgba(140,120,189,0.45);
            z-index:3;
            animation:ara-scan 2.2s ease-in-out infinite;
        }
        @keyframes ara-scan{
            0%{top:8%;} 50%{top:88%;} 100%{top:8%;}
        }
        .ara-analysis-title{
            margin-top:2rem;
            font-family:'Space Grotesk',sans-serif;
            font-weight:700;
            font-size:clamp(1.15rem, 2.6vw, 1.75rem);
            color:var(--ink);
            letter-spacing:-0.01em;
        }
        .ara-analysis-title .ara-dots::after{
            content:'';
            animation:ara-dots 1.4s steps(4,end) infinite;
        }
        @keyframes ara-dots{
            0%{content:'';} 25%{content:'.';} 50%{content:'..';} 75%{content:'...';}
        }
        .ara-steps{
            position:relative;
            height:1.4rem;
            margin-top:0.6rem;
            width:min(420px, 82vw);
        }
        .ara-steps span{
            position:absolute;
            inset:0;
            opacity:0;
            color:var(--ink-muted);
            font-size:clamp(0.82rem, 1.6vw, 0.95rem);
            animation:ara-steps 8s linear infinite;
        }
        .ara-steps span:nth-child(1){animation-delay:0s;}
        .ara-steps span:nth-child(2){animation-delay:2s;}
        .ara-steps span:nth-child(3){animation-delay:4s;}
        .ara-steps span:nth-child(4){animation-delay:6s;}
        @keyframes ara-steps{
            0%{opacity:0; transform:translateY(6px);}
            4%{opacity:1; transform:translateY(0);}
            22%{opacity:1; transform:translateY(0);}
            26%{opacity:0; transform:translateY(-6px);}
            100%{opacity:0;}
        }
        .ara-track{
            margin-top:1.4rem;
            width:min(360px, 74vw);
            height:5px;
            border-radius:999px;
            background:var(--line);
            overflow:hidden;
        }
        .ara-track i{
            display:block;
            height:100%;
            width:38%;
            border-radius:999px;
            background:var(--accent);
            animation:ara-track 1.6s ease-in-out infinite;
        }
        @keyframes ara-track{
            0%{transform:translateX(-100%);}
            100%{transform:translateX(320%);}
        }

        /* ---- Print ---- */
        @media print{
            .stApp{background:#fff !important;}
            .st-key-ara_navbar,
            .st-key-ara_more_host,
            .st-key-ara_relays,
            [data-testid="stToolbar"],
            [data-testid="stSidebar"],
            [data-testid="stFileUploader"],
            .stButton,
            .stFormSubmitButton,
            .ara-broom-overlay,
            .ara-analysis-overlay,
            iframe{
                display:none !important;
            }
            .ara-table-card, .ara-card, .ara-hero{
                box-shadow:none !important;
                break-inside:avoid;
            }
            details.ara-more-row > summary{display:none !important;}
            details.ara-more-row .ara-more-body{display:block !important;}
        }

        [data-testid="stDownloadButton"] button{min-height:44px;}
        .ara-card, [data-testid="stVerticalBlockBorderWrapper"]{box-shadow:0 3px 14px rgba(0,0,0,.07);}
        .ara-chip, .ara-card, [data-testid="stMetricValue"]{overflow-wrap:anywhere;}
        @media (max-width:1024px){
            .st-key-ara_navbar [data-testid="stHorizontalBlock"]{display:grid!important; grid-template-columns:repeat(5,minmax(0,1fr))!important;grid-template-rows:36px 44px!important;gap:6px!important;}
            .st-key-ara_navbar [data-testid="stColumn"]{width:100%!important;min-width:0!important;}
            .st-key-ara_navbar [data-testid="stColumn"]:first-child{grid-column:1/-1;}
            .st-key-ara_navbar button p{font-size:12px!important;white-space:normal!important;}
            .st-key-ara_navbar button{padding:6px 3px!important;min-height:44px!important;font-size:12px!important;}
            .st-key-ara_navbar{padding:10px!important;min-height:0!important;}
            .ara-brand{text-align:left!important;font-size:20px!important;}
            .ara-hero-media{max-height:180px;overflow:hidden;}
            .block-container{max-width:100%;}
            iframe, video, img{max-width:100%;}
        }
        /* ---- Responsive breakpoints ---- */
        @media (max-width: 1024px){
            .ara-hero{padding:2.4rem 1.8rem;}
            .ara-hero-grid{gap:1.6rem;}
            .ara-hero-media{width:min(220px, 30vw);}
        }
        @media (max-width: 768px){
            .block-container{padding-left:0.8rem; padding-right:0.8rem; padding-top:2.25rem;}
            .st-key-ara_navbar{
                flex-wrap:wrap;
                border-radius:22px;
                padding:0.8rem;
                margin-bottom:1.5rem;
            }
            .st-key-ara_more_host{
                right:8px;
                left:auto;
                width:min(290px, calc(100vw - 32px));
            }
            .st-key-ara_more_host iframe{width:100% !important;}
            .ara-hero{padding:2rem 1.3rem; border-radius:18px;}
            .ara-hero-grid{flex-direction:column;}
            .ara-hero-media{width:min(240px, 62vw); order:-1; margin:0 auto;}
            .ara-hero-stats{gap:1.4rem;}
            table.ara-table{font-size:0.82rem;}
            .ara-more-body{min-width:200px;}
        }
        @media (max-width: 430px){
            .block-container{padding-top:2rem;}
            .ara-hero h1{font-size:1.7rem;}
            .ara-hero p{font-size:0.95rem;}
            .ara-card{padding:1.1rem 1.2rem;}
            .ara-kpi{padding:0.8rem 0.9rem;}
            .ara-kpi-value{font-size:1.2rem;}
            .stButton>button, .stFormSubmitButton>button{
                width:100%;
            }
        }
        @media (prefers-reduced-motion: reduce){
            .ara-ring, .ara-scan, .ara-track i, .ara-steps span, .ara-orb,
            .ara-broom-emoji, .ara-broom-dust{
                animation:none !important;
            }
            .ara-steps span:nth-child(1){opacity:1;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Clear Cache — broom animation
# ---------------------------------------------------------------------------

def show_broom_overlay(seconds=1.3):
    """
    Large centered broom-sweep animation shown right after Clear Cache runs.
    Blocking by design (like analysis_loader) so it always finishes before
    the rest of the page renders — never left on screen indefinitely.
    """
    slot = st.empty()
    slot.markdown(
        """
        <div class="ara-broom-overlay" role="status" aria-live="polite">
            <div class="ara-broom-stage">
                <div class="ara-broom-emoji">🧹</div>
                <div class="ara-broom-dust d1"></div>
                <div class="ara-broom-dust d2"></div>
                <div class="ara-broom-dust d3"></div>
            </div>
            <div class="ara-broom-title">Cleaning up…</div>
            <div class="ara-broom-sub">Clearing application cache · Removing temporary data · Refreshing state</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    time.sleep(seconds)
    slot.empty()
    st.toast('Cache cleared successfully', icon='🧹')


# ---------------------------------------------------------------------------
# AI analysis overlay
# ---------------------------------------------------------------------------

def _analysis_overlay_html():
    return f"""
    <div class="ara-analysis-overlay" role="status" aria-live="polite">
        <div class="ara-stage">
            <div class="ara-ring"></div>
            <div class="ara-ring r2"></div>
            <div class="ara-ring r3"></div>
            {_loader_media('ara-analysis-media')}
            <div class="ara-scan"></div>
        </div>
        <div class="ara-analysis-title">AI is analyzing your resume<span class="ara-dots"></span></div>
        <div class="ara-steps">
            <span>Reading the document and extracting raw text…</span>
            <span>Identifying your skills, education and experience…</span>
            <span>Matching your profile against career tracks…</span>
            <span>Scoring your resume and picking recommendations…</span>
        </div>
        <div class="ara-track"><i></i></div>
    </div>
    """


@contextlib.contextmanager
def analysis_loader(min_seconds=MIN_ANALYSIS_SECONDS):
    """
    Context manager that shows the large, centered AI-analysis animation while
    the wrapped work runs:

        with analysis_loader():
            resume_data = ResumeParser(path).get_extracted_data()

    The overlay comes down only once the real work has finished. `min_seconds`
    is a floor, not a fixed delay — if parsing takes longer, nothing extra is
    added on top of it.
    """
    slot = st.empty()
    slot.markdown(_analysis_overlay_html(), unsafe_allow_html=True)
    started = time.time()
    try:
        yield slot
        remaining = min_seconds - (time.time() - started)
        if remaining > 0:
            time.sleep(remaining)
    finally:
        slot.empty()


# ---------------------------------------------------------------------------
# MORE menu
# ---------------------------------------------------------------------------

_MORE_PANEL_HEIGHT = 372

_MORE_PANEL_MARKUP = """
<div class="panel" id="panel" role="menu" aria-label="More">
  <div class="seg" role="group" aria-label="Theme">
    <button class="seg-btn" data-theme="system" role="menuitemradio">
      <span class="ico">◐</span><span>System</span>
    </button>
    <button class="seg-btn" data-theme="light" role="menuitemradio">
      <span class="ico">☀</span><span>Light</span>
    </button>
    <button class="seg-btn" data-theme="dark" role="menuitemradio">
      <span class="ico">☾</span><span>Dark</span>
    </button>
  </div>
  <div class="sep"></div>
  <button class="row" data-act="rerun" role="menuitem">
    <span>Rerun</span><kbd>R</kbd>
  </button>
  <button class="row" data-act="autorerun" role="menuitemcheckbox" aria-checked="false">
    <span>Autorerun</span><span class="switch" id="autoSwitch"><i></i></span>
  </button>
  <div class="sep"></div>
  <button class="row" data-act="clearcache" role="menuitem">
    <span>Clear Cache</span><kbd>C</kbd>
  </button>
  <button class="row" data-act="print" role="menuitem"><span>Print</span></button>
  <button class="row" data-act="record" role="menuitem">
    <span id="recLabel">Record Screen</span><span class="rec-dot" id="recDot"></span>
  </button>
  <div class="foot" id="foot">CareerViz</div>
</div>
"""

_MORE_PANEL_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');
  *{box-sizing:border-box;}
  html,body{margin:0;padding:0;background:transparent;}
  body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;}
  :root{
    --surface:#FFFFFF; --surface-2:#F2EFEA; --ink:#141414;
    --ink-muted:#6B6B6B; --accent:#8C78BD; --line:#E7E3DC;
    --shadow:0 16px 40px rgba(20,20,20,0.14);
  }
  body[data-theme="dark"]{
    --surface:#1A1A1D; --surface-2:#242429; --ink:#F2F0ED;
    --ink-muted:#A5A29C; --accent:#BCA8E8; --line:#2E2E33;
    --shadow:0 16px 40px rgba(0,0,0,0.55);
  }
  .panel{
    margin:3px;
    background:var(--surface);
    border:1px solid var(--line);
    border-radius:14px;
    box-shadow:var(--shadow);
    padding:8px;
    transform-origin:top right;
    animation:pop .16s cubic-bezier(.2,.9,.3,1.2) both;
    color:var(--ink);
  }
  @keyframes pop{from{opacity:0;transform:scale(.95) translateY(-6px);}to{opacity:1;transform:none;}}
  .seg{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;}
  .seg-btn{
    display:flex;flex-direction:column;align-items:center;gap:6px;
    padding:10px 4px;border:1px solid transparent;border-radius:10px;
    background:transparent;color:var(--ink);cursor:pointer;
    font-family:'Space Grotesk',sans-serif;font-size:12.5px;font-weight:600;
    transition:background .15s ease,border-color .15s ease,color .15s ease;
  }
  .seg-btn .ico{font-size:17px;line-height:1;}
  .seg-btn:hover{background:var(--surface-2);}
  .seg-btn[aria-checked="true"]{background:var(--surface-2);border-color:var(--line);}
  .seg-btn:focus-visible,.row:focus-visible{outline:2px solid var(--accent);outline-offset:1px;}
  .sep{height:1px;background:var(--line);margin:8px 2px;}
  .row{
    display:flex;align-items:center;justify-content:space-between;gap:10px;
    width:100%;padding:9px 10px;border:none;border-radius:9px;background:transparent;
    color:var(--ink);cursor:pointer;font-family:'Inter',sans-serif;font-size:13.5px;
    text-align:left;transition:background .15s ease,color .15s ease;
  }
  .row:hover{background:var(--surface-2);}
  .row:active{background:var(--line);}
  .row kbd{
    font-family:'Space Grotesk',sans-serif;font-size:11.5px;color:var(--ink-muted);
    background:transparent;border:none;
  }
  .switch{
    width:34px;height:19px;border-radius:999px;background:var(--line);
    position:relative;flex:none;transition:background .18s ease;
  }
  .switch i{
    position:absolute;top:2px;left:2px;width:15px;height:15px;border-radius:50%;
    background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.25);transition:transform .18s ease;
  }
  .switch.on{background:var(--accent);}
  .switch.on i{transform:translateX(15px);}
  .rec-dot{width:9px;height:9px;border-radius:50%;background:var(--line);flex:none;}
  .rec-dot.on{background:#E5484D;animation:blink 1.1s ease-in-out infinite;}
  @keyframes blink{50%{opacity:.25;}}
  .foot{
    padding:8px 10px 3px 10px;color:var(--ink-muted);font-size:11.5px;
    font-family:'Space Grotesk',sans-serif;
  }
  .foot.note{color:var(--accent);}
</style>
"""


def _more_component(is_open):
    """
    Renders the MORE dropdown (when open) plus the always-on runtime that
    applies the stored theme, keeps the Autorerun timer alive and wires the
    keyboard shortcuts.

    Everything needing the browser (theme attribute, localStorage,
    window.print, getDisplayMedia) happens here; everything needing Python
    (Rerun, Clear Cache) is relayed by clicking the off-screen Streamlit
    buttons from `_render_relays()`, so there is no page reload and no
    duplicate API call.
    """
    # A bare <style> tag followed immediately by <script>, with nothing in
    # between, can leave this iframe's document.body genuinely null when
    # the script executes — the browser hasn't encountered anything that
    # forces it to create a <body> yet. That happens on every page load
    # (the panel starts closed, so `markup` is empty), and threw an
    # uncaught TypeError here, before this component finished its normal
    # render lifecycle. A hidden placeholder guarantees a body exists
    # regardless of open/closed state; the setAttribute call below is also
    # guarded directly, belt-and-suspenders.
    markup = _MORE_PANEL_MARKUP if is_open else '<div style="display:none"></div>'
    open_flag = 'true' if is_open else 'false'
    html_doc = f"""
    {_MORE_PANEL_CSS}
    {markup}
    <script>
    (function(){{
      var P, PD;
      try {{ P = window.parent; PD = P.document; }} catch (e) {{ return; }}

      var IS_OPEN = {open_flag};
      var K_THEME = 'ara-theme', K_AUTO = 'ara-autorerun';
      var AUTO_MS = 30000;               // never faster than 30s
      P.__araMoreOpen = IS_OPEN;

      function ls(){{ try {{ return P.localStorage; }} catch(e) {{ return null; }} }}
      function get(k, d){{
        var s = ls();
        try {{ var v = s && s.getItem(k); return (v === null || v === undefined) ? d : v; }}
        catch(e) {{ return d; }}
      }}
      function set(k, v){{ var s = ls(); try {{ s && s.setItem(k, v); }} catch(e) {{}} }}
      function relay(name){{
        var b = PD.querySelector('.st-key-ara_relay_' + name + ' button');
        if (b) {{ b.click(); return true; }}
        return false;
      }}
      function moreButton(){{ return PD.querySelector('.st-key-nav_more button'); }}
      function closePanel(){{ if (P.__araMoreOpen) {{ var b = moreButton(); if (b) b.click(); }} }}

      /* ---------- theme ---------- */
      function applyTheme(t, persist){{
        if (['system','light','dark'].indexOf(t) < 0) t = 'system';
        PD.documentElement.setAttribute('data-ara-theme', t);
        if (persist) set(K_THEME, t);
        var dark = t === 'dark' || (t === 'system' && P.matchMedia &&
                   P.matchMedia('(prefers-color-scheme: dark)').matches);
        document.body && document.body.setAttribute('data-theme', dark ? 'dark' : 'light');
        var segs = document.querySelectorAll('.seg-btn');
        for (var i = 0; i < segs.length; i++) {{
          segs[i].setAttribute('aria-checked', segs[i].getAttribute('data-theme') === t ? 'true' : 'false');
        }}
      }}
      applyTheme(get(K_THEME, 'system'), false);
      if (!P.__araMediaBound && P.matchMedia) {{
        P.__araMediaBound = true;
        try {{
          P.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(){{
            if (get(K_THEME, 'system') === 'system') {{
              PD.documentElement.setAttribute('data-ara-theme', 'system');
            }}
          }});
        }} catch(e) {{}}
      }}

      /* ---------- autorerun ---------- */
      function autoOn(){{ return get(K_AUTO, '0') === '1'; }}
      function armAuto(){{
        if (P.__araAutoId) {{ P.clearInterval(P.__araAutoId); P.__araAutoId = null; }}
        if (!autoOn()) return;
        P.__araAutoId = P.setInterval(function(){{
          if (PD.visibilityState !== 'visible') return;   // no background traffic
          if (P.__araBusy) return;                        // one in flight at a time
          if (P.__araRec) return;                         // don't interrupt a recording
          if (relay('rerun')) {{
            P.__araBusy = true;
            P.setTimeout(function(){{ P.__araBusy = false; }}, 5000);
          }}
        }}, AUTO_MS);
      }}
      armAuto();
      if (!P.__araAutoCleanup) {{
        P.__araAutoCleanup = true;
        P.addEventListener('pagehide', function(){{
          if (P.__araAutoId) {{ P.clearInterval(P.__araAutoId); P.__araAutoId = null; }}
        }});
      }}
      function note(msg){{
        var f = document.getElementById('foot');
        if (!f) return;
        f.textContent = msg || 'CareerViz';
        if (msg) {{ f.classList.add('note'); }} else {{ f.classList.remove('note'); }}
      }}
      function paintAuto(){{
        var sw = document.getElementById('autoSwitch');
        if (!sw) return;
        var on = autoOn();
        if (on) {{ sw.classList.add('on'); }} else {{ sw.classList.remove('on'); }}
        var row = sw.parentNode;
        if (row) row.setAttribute('aria-checked', on ? 'true' : 'false');
        note(on ? 'Autorerun is ON — refreshes every 30s' : '');
      }}

      /* ---------- clear cache ---------- */
      function clearBrowserCache(){{
        var keep = function(k){{
          if (!k) return false;
          if (k === K_THEME || k === K_AUTO) return true;
          return /auth|token|session|login|credential/i.test(k);
        }};
        [P.localStorage, P.sessionStorage].forEach(function(store){{
          try {{
            var doomed = [];
            for (var i = 0; i < store.length; i++) {{
              var k = store.key(i);
              if (!keep(k)) doomed.push(k);
            }}
            doomed.forEach(function(k){{ store.removeItem(k); }});
          }} catch(e) {{}}
        }});
        if (P.caches && P.caches.keys) {{
          try {{
            P.caches.keys().then(function(ks){{ ks.forEach(function(k){{ P.caches.delete(k); }}); }});
          }} catch(e) {{}}
        }}
      }}

      /* ---------- screen recording ---------- */
      function paintRecord(){{
        var dot = document.getElementById('recDot'), lbl = document.getElementById('recLabel');
        var live = !!(P.__araRec && P.__araRec.recorder && P.__araRec.recorder.state === 'recording');
        if (dot) {{ if (live) {{ dot.classList.add('on'); }} else {{ dot.classList.remove('on'); }} }}
        if (lbl) lbl.textContent = live ? 'Stop Recording' : 'Record Screen';
      }}
      function record(){{
        var cur = P.__araRec;
        if (cur && cur.recorder && cur.recorder.state === 'recording') {{ cur.recorder.stop(); return; }}
        var md = P.navigator && P.navigator.mediaDevices;
        if (!md || !md.getDisplayMedia || !P.MediaRecorder) {{
          note('Screen recording is not supported in this browser');
          return;
        }}
        /* Called straight from the click handler so the parent document still
           has transient activation — getDisplayMedia requires it, and it is
           never called on its own. */
        md.getDisplayMedia({{ video: {{ frameRate: 30 }}, audio: true }}).then(function(stream){{
          var mime = ['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm','video/mp4']
            .filter(function(m){{ try {{ return P.MediaRecorder.isTypeSupported(m); }} catch(e) {{ return false; }} }})[0];
          var rec = new P.MediaRecorder(stream, mime ? {{ mimeType: mime }} : undefined);
          var chunks = [];
          rec.ondataavailable = function(e){{ if (e.data && e.data.size) chunks.push(e.data); }};
          rec.onstop = function(){{
            try {{ stream.getTracks().forEach(function(t){{ t.stop(); }}); }} catch(e) {{}}
            var type = mime || 'video/webm';
            var blob = new P.Blob(chunks, {{ type: type }});
            var url = P.URL.createObjectURL(blob);
            var a = PD.createElement('a');
            a.href = url;
            a.download = 'ai-resume-analyzer-' + new Date().toISOString().replace(/[:.]/g, '-') +
                         (type.indexOf('mp4') > -1 ? '.mp4' : '.webm');
            PD.body.appendChild(a); a.click(); a.remove();
            P.setTimeout(function(){{ P.URL.revokeObjectURL(url); }}, 15000);
            P.__araRec = null;
            paintRecord(); note('Recording saved to your downloads');
          }};
          try {{
            stream.getVideoTracks()[0].addEventListener('ended', function(){{
              if (rec.state === 'recording') rec.stop();
            }});
          }} catch(e) {{}}
          rec.start(1000);
          P.__araRec = {{ recorder: rec }};
          paintRecord(); note('Recording… click again to stop');
        }}).catch(function(err){{
          note(err && err.name === 'NotAllowedError'
               ? 'Screen recording permission denied'
               : 'Could not start screen recording');
        }});
      }}

      /* ---------- panel wiring ---------- */
      if (IS_OPEN) {{
        paintAuto(); paintRecord();

        var segs = document.querySelectorAll('.seg-btn');
        for (var s = 0; s < segs.length; s++) {{
          (function(btn){{
            btn.addEventListener('click', function(){{
              applyTheme(btn.getAttribute('data-theme'), true);
              closePanel();
            }});
          }})(segs[s]);
        }}

        var rows = document.querySelectorAll('.row');
        for (var r = 0; r < rows.length; r++) {{
          (function(btn){{
            btn.addEventListener('click', function(){{
              var act = btn.getAttribute('data-act');
              if (act === 'rerun') {{
                if (!relay('rerun')) note('Nothing to rerun on this page');
                return;                      // the relay click also closes the panel
              }}
              if (act === 'autorerun') {{
                set(K_AUTO, autoOn() ? '0' : '1');
                armAuto(); paintAuto();
                return;                      // stay open so ON/OFF is visible
              }}
              if (act === 'clearcache') {{
                clearBrowserCache();
                if (!relay('clearcache')) note('Cache cleared successfully');
                return;
              }}
              if (act === 'print') {{
                closePanel();
                P.setTimeout(function(){{ try {{ P.focus(); P.print(); }} catch(e) {{}} }}, 250);
                return;
              }}
              if (act === 'record') {{ record(); return; }}
            }});
          }})(rows[r]);
        }}

        /* keyboard navigation inside the panel */
        var items = [];
        var all = document.querySelectorAll('.seg-btn,.row');
        for (var a = 0; a < all.length; a++) items.push(all[a]);
        if (items.length) items[0].focus();
        document.addEventListener('keydown', function(e){{
          var i = items.indexOf(document.activeElement);
          if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {{
            e.preventDefault(); items[(i + 1 + items.length) % items.length].focus();
          }} else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {{
            e.preventDefault(); items[(i - 1 + items.length) % items.length].focus();
          }} else if (e.key === 'Escape') {{
            e.preventDefault(); closePanel();
          }}
        }});
      }}

      /* ---------- outside click / escape / shortcuts (parent document) ---------- */
      if (!P.__araGlobalBound) {{
        P.__araGlobalBound = true;
        PD.addEventListener('mousedown', function(ev){{
          if (!P.__araMoreOpen) return;
          var t = ev.target;
          if (!t || !t.closest) return;
          /* the MORE button toggles itself, the panel handles its own clicks,
             and every nav button already clears the flag server-side */
          if (t.closest('.st-key-nav_more') || t.closest('.st-key-ara_more_host')) return;
          if (t.closest('.st-key-ara_navbar') && t.closest('button')) return;
          closePanel();
        }}, true);
        PD.addEventListener('keydown', function(ev){{
          var el = PD.activeElement;
          var typing = el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
          if (ev.key === 'Escape' && P.__araMoreOpen) {{ closePanel(); return; }}
          if (typing || ev.metaKey || ev.ctrlKey || ev.altKey) return;
          if (ev.key === 'r' || ev.key === 'R') {{ relay('rerun'); }}
          else if (ev.key === 'c' || ev.key === 'C') {{ relay('clearcache'); }}
        }});
      }}
    }})();
    </script>
    """
    height = _MORE_PANEL_HEIGHT if is_open else 1
    # st.iframe replaces components.html in recent Streamlit; fall back so this
    # keeps working on either version.
    if hasattr(st, 'iframe'):
        st.iframe(html_doc, height=height, width=306)
    else:
        components.html(html_doc, height=height, width=306)


def _render_relays():
    """
    Off-screen Streamlit buttons that the MORE panel clicks. Keeping Rerun and
    Clear Cache on this side means they go through a normal Streamlit rerun —
    session state, admin login and the uploaded file all survive — instead of
    a page reload.
    """
    with st.container(key='ara_relays'):
        with st.container(key='ara_relay_rerun'):
            rerun_clicked = st.button('rerun', key='ara_relay_rerun_btn')
        with st.container(key='ara_relay_clearcache'):
            clear_clicked = st.button('clearcache', key='ara_relay_clearcache_btn')

    if clear_clicked:
        try:
            st.cache_data.clear()
        except Exception:
            pass
        try:
            st.cache_resource.clear()
        except Exception:
            pass
        # Drop our own scratch state, but keep navigation, admin auth, any
        # cached resume analysis and pending admin-delete confirmations —
        # those are session, not cache, and clearing them would silently log
        # the admin out / drop an in-progress upload.
        protected = {
            '_ara_nav', '_ara_more_open', '_ara_admin_ok', '_ara_analysis',
            '_ara_analyzing', '_ara_admin_until', '_ara_training_in_progress',
        }
        for key in [k for k in list(st.session_state.keys())
                    if str(k).startswith('_ara_') and k not in protected
                    and not str(k).startswith('_ara_confirm_')
                    and not str(k).startswith('_ara_deleted_')]:
            del st.session_state[key]
        st.session_state.pop('_analysis_pdf_cache',None)
        st.session_state['_ara_more_open'] = False
        st.toast('Cache cleared successfully')

    if rerun_clicked:
        # The click itself already triggered this rerun, so the page is
        # re-running right now; just close the panel. No extra request.
        st.session_state['_ara_more_open'] = False


# ---------------------------------------------------------------------------
# Top navigation
# ---------------------------------------------------------------------------

def _nav_select(item):
    """
    on_click callback for a nav button. Streamlit runs on_click callbacks
    BEFORE the script re-executes top-to-bottom, so by the time this rerun
    draws the nav row, st.session_state['_ara_nav'] already reflects the
    click — the active pill lands on the very first click instead of only
    appearing after a second interaction.
    """
    st.session_state['_ara_nav'] = item
    st.session_state['_ara_more_open'] = False


def _nav_toggle_more():
    st.session_state['_ara_more_open'] = not st.session_state['_ara_more_open']


def render_navbar():
    """
    Renders the top nav (User / Feedback / Admin / About / MORE) using real
    Streamlit buttons (so state + reruns keep working), styled via CSS to
    look like a pill nav bar. Returns the active choice string, one of
    NAV_ITEMS, exactly like the old sidebar selectbox did.
    """
    if '_ara_nav' not in st.session_state:
        st.session_state['_ara_nav'] = 'User'
    if '_ara_more_open' not in st.session_state:
        st.session_state['_ara_more_open'] = False

    with st.container(key='ara_navbar'):
        cols = st.columns([2.2, 1, 1, 1, 1, 1])

        with cols[0]:
            st.markdown(
                '<div class="ara-brand">📄 Career<span class="dot">Viz</span></div>',
                unsafe_allow_html=True,
            )

        for i, item in enumerate(NAV_ITEMS):
            with cols[i + 1]:
                active = st.session_state['_ara_nav'] == item
                label = f'● {item}' if active else item
                st.button(
                    label, key=f'nav_{item}', width='stretch',
                    type='primary' if active else 'secondary',
                    on_click=_nav_select, args=(item,),
                )

        with cols[5]:
            # Hamburger icon — same glyph whether the panel is open or
            # closed, so it always "returns to the menu icon" once closed.
            st.button(
                '☰', key='nav_more', width='stretch',
                help='More', on_click=_nav_toggle_more,
            )

        # Anchored dropdown host — absolutely positioned under the MORE button
        # so the panel overlays the page instead of pushing content down.
        with st.container(key='ara_more_host'):
            _more_component(st.session_state['_ara_more_open'])

    _render_relays()

    return st.session_state['_ara_nav']


# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

def render_hero(total_users=None):
    from visual_refresh import render_hero as refreshed_hero
    refreshed_hero(total_users)


# ---------------------------------------------------------------------------
# Admin data tables
# ---------------------------------------------------------------------------

def _esc(value):
    if value is None:
        return ''
    text = str(value)
    if text.strip().lower() in ('nan', 'none', 'nat'):
        return ''
    return _html.escape(text)


def _dash(value):
    text = _esc(value)
    return text if text.strip() else '—'


def _split_date(value):
    """Timestamps are stored as 'YYYY-MM-DD_HH:MM:SS'."""
    text = _esc(value)
    if '_' in text:
        day, _sep, clock = text.partition('_')
        return day, clock
    return text, ''


def _details(rows):
    """Build the row-level More panel from (label, value) pairs."""
    items = ''.join(
        f'<dt>{_esc(label)}</dt><dd>{_dash(value)}</dd>'
        for label, value in rows
    )
    return (
        '<details class="ara-more-row"><summary>More</summary>'
        f'<div class="ara-more-body"><dl>{items}</dl></div></details>'
    )


def _table_card(title, count_label, headers, body_rows, footer_html=''):
    if body_rows:
        head = ''.join(f'<th>{_esc(h)}</th>' for h in headers)
        body = ''.join(body_rows)
        table = (
            '<div class="ara-table-scroll"><table class="ara-table">'
            f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody>'
            '</table></div>'
        )
    else:
        table = '<div class="ara-empty">No records yet.</div>'

    st.markdown(
        f'<div class="ara-table-card">'
        f'<div class="ara-table-head"><h4>{_esc(title)}</h4>'
        f'<span class="ara-count">{_esc(count_label)}</span></div>'
        f'{table}{footer_html}</div>',
        unsafe_allow_html=True,
    )


def _plural(n, word):
    return f'{n} {word}' + ('' if n == 1 else 's')


def render_user_data_table(df, download_link_html=''):
    """Deprecated — kept only so an old import doesn't hard-crash; use
    render_admin_table instead (search + selection + xlsx export + delete)."""
    return render_admin_table(
        'user_data', "User's Data", df, id_col='ID',
        search_cols=['Name', 'Mail', 'Predicted Field', 'File Name', 'Token', 'IP Address'],
    )


def render_feedback_table(df):
    """Deprecated — see render_user_data_table."""
    return render_admin_table(
        'feedback', "User's Feedback Data", df, id_col='ID',
        search_cols=['Name', 'Email', 'Comments'],
    )


def to_xlsx_bytes(df):
    """Real .xlsx bytes (via openpyxl) — never a renamed text/CSV file."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return buf.getvalue()

# Only one st.dialog can be open per script run — across the WHOLE app, not
# just within one table. Two admin tables (User's Data and Feedback) each
# have their own confirm/editing flags, so it's possible for one table's
# dialog to be left "open" in session_state (e.g. dismissed via the native
# X button or an outside click, which the in-dialog Cancel/Save buttons
# never see) while a different action opens a second dialog elsewhere —
# Streamlit raises StreamlitInvalidLayoutContextError the moment a second
# dialog-decorated function is called in the same run. This single token
# is the one source of truth for "which dialog, if any, owns this run";
# opening any dialog always claims it, and every dialog is wired with
# on_dismiss so closing it any way — button, X, outside click, Escape —
# reliably releases it and clears the table-specific flag.
_DIALOG_OWNER_KEY = '_ara_dialog_owner'


def _release_dialog(key, flag_key):
    st.session_state.pop(flag_key, None)
    if st.session_state.get(_DIALOG_OWNER_KEY) == key:
        st.session_state.pop(_DIALOG_OWNER_KEY, None)


def _make_confirm_delete_dialog(key, title, confirm_key, done_key):
    owner = f'confirm:{key}'

    def _on_dismiss():
        _release_dialog(owner, confirm_key)

    @st.dialog('Delete records?', on_dismiss=_on_dismiss)
    def _dialog():
        ids = st.session_state.get(confirm_key, [])
        st.markdown(
            f"You are about to permanently delete **{len(ids)}** "
            f"{title.lower()} record(s). This cannot be undone."
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button('Cancel', key=f'{key}_cancel_del', width='stretch'):
                _release_dialog(owner, confirm_key)
                st.rerun()
        with c2:
            if st.button('Delete', key=f'{key}_confirm_del', type='primary', width='stretch'):
                st.session_state[done_key] = list(ids)
                _release_dialog(owner, confirm_key)
                st.rerun()

    return _dialog


def _make_edit_row_dialog(key, row, edit_fields, editing_key, saved_key):
    """
    edit_fields: list of (display_label, db_column, kind, options) tuples.
    kind is 'text' or 'select' (options is a list, used only for 'select').
    Only fields explicitly listed here are editable — auto-generated /
    analysis-output columns (score, skills, timestamps, tokens, etc.) are
    intentionally left out, matching "modify only appropriate fields".
    """
    owner = f'edit:{key}'
    row_id = row.get('ID')

    def _on_dismiss():
        _release_dialog(owner, editing_key)

    @st.dialog('Edit record', on_dismiss=_on_dismiss)
    def _dialog():
        st.markdown(f'Editing record **#{row_id}**')
        updated = {}
        for label, db_col, kind, options in edit_fields:
            cur_val = row.get(label, '')
            cur_val = '' if cur_val is None else str(cur_val)
            if kind == 'select':
                idx = options.index(cur_val) if cur_val in options else 0
                updated[db_col] = st.selectbox(label, options, index=idx, key=f'{key}_edit_{db_col}')
            else:
                updated[db_col] = st.text_input(label, value=cur_val, key=f'{key}_edit_{db_col}')

        c1, c2 = st.columns(2)
        with c1:
            if st.button('Cancel', key=f'{key}_edit_cancel', width='stretch'):
                _release_dialog(owner, editing_key)
                st.rerun()
        with c2:
            if st.button('Save Changes', key=f'{key}_edit_save', type='primary', width='stretch'):
                st.session_state[saved_key] = {'id': row_id, 'fields': updated}
                _release_dialog(owner, editing_key)
                st.rerun()

    return _dialog


def render_admin_table(key, title, df, id_col='ID', search_cols=None, edit_fields=None):
    """
    Interactive admin data card: native multi-row selection (real
    checkboxes, via st.dataframe's selection UI — its toolbar also has its
    own built-in search icon, so this function doesn't render a second
    one), bulk .xlsx export of the selection or of everything, bulk delete
    behind a confirmation dialog, and — when exactly one row is selected
    and `edit_fields` is given — an Edit button that opens a form dialog
    for that record.

    This function only reads/selects — it never touches the database. It
    returns {'selected_ids': [...], 'delete_ids': [...] | None,
    'edit': {'id':..., 'fields': {db_col: new_value}} | None}. `delete_ids`
    / `edit` are populated exactly once, on the run where the admin
    confirms. The caller (App.py, which already owns the DB connection) is
    responsible for actually writing those changes and calling st.rerun()
    so every dependent count/chart recomputes from the fresh data — no
    stale numbers left on screen.

    `edit_fields`: list of (display_label, db_column, kind, options)
    tuples — see _edit_row_dialog. Pass None (default) to omit the Edit
    button entirely for tables that shouldn't support it.

    Note: Streamlit's interactive dataframe grid renders through its own
    internal theme rather than this file's CSS variables, so unlike the
    rest of the page it won't flip to the dark palette from the MORE menu.

    `search_cols` is accepted but unused — kept so existing callers don't
    need updating; the grid's own toolbar search covers this now.
    """
    result = {'selected_ids': [], 'delete_ids': None, 'edit': None}
    confirm_key = f'_ara_confirm_{key}'
    done_key = f'_ara_deleted_{key}'
    editing_key = f'_ara_editing_{key}'
    saved_key = f'_ara_saved_{key}'

    with st.container(key=f'ara_admin_{key}'):
        head = st.columns([2.4, 1.4])
        with head[0]:
            st.markdown(f'<div class="ara-admin-title">{_esc(title)}</div>', unsafe_allow_html=True)
        with head[1]:
            st.markdown(
                f'<div class="ara-count ara-count-right">{_plural(len(df), "record")}</div>',
                unsafe_allow_html=True,
            )

        # No custom search box here — st.dataframe's own toolbar already
        # provides a search icon (top-right, on hover) that filters this
        # same grid, so a second full-width text input above it was
        # redundant (two search bars doing the same job). search_cols is
        # kept as a parameter for compatibility but no longer used.
        filtered = df

        selected_ids = []
        if filtered.empty:
            st.markdown('<div class="ara-empty">No records yet.</div>', unsafe_allow_html=True)
        else:
            event = st.dataframe(
                filtered,
                hide_index=True,
                width='stretch',
                on_select='rerun',
                selection_mode='multi-row',
                key=f'{key}_grid',
                height=min(74 + 36 * len(filtered), 460),
            )
            sel = getattr(event, 'selection', None)
            rows = []
            if sel is not None:
                try:
                    rows = sel['rows']
                except Exception:
                    rows = getattr(sel, 'rows', None) or []
                # a selection recorded against a previous, longer version of
                # this dataframe (e.g. before a delete elsewhere on the page
                # shrank it) can carry indices past the current end — drop
                # anything out of range rather than crash on it
                rows = [r for r in rows if 0 <= r < len(filtered)]
            if rows and id_col in filtered.columns:
                selected_ids = filtered.iloc[rows][id_col].tolist()
        result['selected_ids'] = selected_ids

        ### Action bar — only show bulk actions once something is selected;
        ### Download All is available whenever there are records at all.
        n_sel = len(selected_ids)
        bar = st.columns([1.7, 1.3, 1.5, 1.7, 2.8])
        with bar[0]:
            if n_sel:
                sel_df = filtered[filtered[id_col].isin(selected_ids)] if id_col in filtered.columns else filtered
                st.download_button(
                    f'⬇ Selected ({n_sel})',
                    data=to_xlsx_bytes(sel_df),
                    file_name=f'{key}_selected.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    key=f'{key}_dl_sel',
                )
        with bar[1]:
            if not df.empty:
                st.download_button(
                    '⬇ All',
                    data=to_xlsx_bytes(df),
                    file_name=f'{key}_all.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    key=f'{key}_dl_all',
                )
        with bar[2]:
            if edit_fields and n_sel == 1:
                if st.button('✎ Edit', key=f'{key}_edit_btn'):
                    st.session_state[editing_key] = True
                    st.session_state[_DIALOG_OWNER_KEY] = f'edit:{key}'
            elif edit_fields and n_sel > 1:
                st.caption('Select just one row to edit')
        with bar[3]:
            if n_sel:
                if st.button(f'🗑 Delete ({n_sel})', key=f'{key}_del_btn'):
                    st.session_state[confirm_key] = selected_ids
                    st.session_state[_DIALOG_OWNER_KEY] = f'confirm:{key}'

        owner = st.session_state.get(_DIALOG_OWNER_KEY)
        if owner == f'confirm:{key}':
            if st.session_state.get(confirm_key):
                _make_confirm_delete_dialog(key, title, confirm_key, done_key)()
            else:
                st.session_state.pop(_DIALOG_OWNER_KEY, None)
        elif owner == f'edit:{key}':
            if edit_fields and st.session_state.get(editing_key) and n_sel == 1:
                row = filtered[filtered[id_col] == selected_ids[0]].iloc[0].to_dict()
                _make_edit_row_dialog(key, row, edit_fields, editing_key, saved_key)()
            else:
                st.session_state.pop(editing_key, None)
                st.session_state.pop(_DIALOG_OWNER_KEY, None)

        if done_key in st.session_state:
            result['delete_ids'] = st.session_state.pop(done_key)
        if saved_key in st.session_state:
            result['edit'] = st.session_state.pop(saved_key)

    return result


def render_comments_table(pairs):
    """Feedback page comment history, in the same card shell."""
    rows = [
        '<tr>'
        f'<td><span class="ara-primary">{_dash(name)}</span></td>'
        f'<td>{_dash(comment)}</td>'
        '</tr>'
        for name, comment in pairs
    ]
    _table_card(
        "User Comments",
        _plural(len(rows), 'comment'),
        ['User', 'Comment'],
        rows,
    )


# ---------------------------------------------------------------------------
# Analytics — KPI cards + varied chart types
#
# Replaces the old "one pie chart per metric" admin analytics with chart
# types that actually fit each data shape (bar/histogram/donut/gauge), and
# adds a post-analysis "Resume Analytics" section for the User page.
#
# Every function here is a pure rendering helper: it takes data the caller
# already computed (pandas Series/dicts/plain numbers) and draws it. None of
# these query the database, run the resume parser, or change any scoring —
# that logic stays in App.py exactly as it was; these just chart the result.
#
# Note on theming: unlike the rest of this file, Plotly figures render into
# their own canvas and don't pick up this file's CSS variables or the MORE
# menu's dark-mode toggle (the same limitation already noted for the admin
# data-selection grid). Colors below are hardcoded to match the light-theme
# tokens (accent #8C78BD, ink #141414, line #E7E3DC, muted #6B6B6B) so they
# sit visually consistent with the rest of the page.
# ---------------------------------------------------------------------------

_CHART_ACCENT = '#8C78BD'
_CHART_ACCENT_SOFT = '#E2D9EF'
_CHART_INK = '#302C43'
_CHART_MUTED = '#817B92'
_CHART_LINE = '#E8E4EF'
_CHART_GOOD = '#80ABA1'
_CHART_GOOD_SOFT = '#DCEBE5'
_CHART_WARN = '#C6A477'
_CHART_PALETTE = ['#8C78BD', '#80ABA1', '#9BADD0', '#C6A477', '#C58EAB', '#ADC4A1', '#AB9BC3', '#B5C7D2']


def _style_fig(fig, title, height=340, show_legend=False):
    fig.update_layout(
        title=dict(text=title, font=dict(family='Space Grotesk, sans-serif', size=16, color=_CHART_INK)),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', size=12, color=_CHART_INK),
        margin=dict(l=10, r=24, t=48, b=10, autoexpand=True),
        height=height,
        showlegend=show_legend,
        legend=dict(font=dict(size=11), bgcolor='rgba(0,0,0,0)'),
        hoverlabel=dict(bgcolor='white', font_family='Inter, sans-serif', font_size=12),
    )
    # automargin lets Plotly expand the plot area to fit full axis labels
    # instead of clipping them — this is the actual fix for "skill/field
    # names getting cut off", not a bigger fixed margin guess.
    fig.update_xaxes(gridcolor=_CHART_LINE, zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor=_CHART_LINE, zeroline=False, automargin=True)
    return fig


def render_kpi_row(items):
    """items: list of (label, value_str) — a row of KPI cards."""
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        with col:
            st.markdown(
                f'<div class="ara-kpi"><div class="ara-kpi-value">{_esc(value)}</div>'
                f'<div class="ara-kpi-label">{_esc(label)}</div></div>',
                unsafe_allow_html=True,
            )


def chart_bar_counts(counts, title, orientation='v', x_title=None, y_title=None,
                      sort_desc=True, color=None, height=340, top_n=None,
                      hover_name='Category', hover_value='Count'):
    """
    Bar chart from a pandas value_counts()-style Series (index = category,
    values = count). Used for predicted field, city/state/country, IP
    usage, current-skills mentions, etc.

    Labels are never truncated — automargin (in _style_fig) expands the
    chart to fit them, and long lists are capped with `top_n` (showing the
    largest categories) rather than compressed to fit.
    """
    s = counts.copy()
    if sort_desc:
        s = s.sort_values(ascending=(orientation == 'h'))
    if top_n:
        # keep the largest `top_n` regardless of the display sort above
        s = s.sort_values(ascending=False).head(top_n)
        s = s.sort_values(ascending=(orientation == 'h'))
    labels = [str(i) for i in s.index]
    values = list(s.values)
    # a chart of many horizontal bars needs more vertical room per bar, or
    # labels/bars get cramped — grow the height instead of squeezing them
    if orientation == 'h':
        height = max(height, 70 + 34 * len(labels))
    fig = go.Figure(go.Bar(
        x=values if orientation == 'h' else labels,
        y=labels if orientation == 'h' else values,
        orientation=orientation,
        marker_color=color or _CHART_ACCENT,
        text=values,
        # 'outside' keeps the value label off the bar and past its end, so
        # it's never lost against the bar's own fill color, and never
        # overlaps a long category name sitting inside a short bar
        textposition='outside',
        cliponaxis=False,
        customdata=labels,
        hovertemplate=f'<b>%{{customdata}}</b><br>{hover_value}: %{{'
                       + ('x' if orientation == 'h' else 'y') + '}}<extra></extra>',
    ))
    fig.update_layout(
        xaxis_title=x_title or ('Count' if orientation == 'h' else None),
        yaxis_title=y_title,
    )
    return _style_fig(fig, title, height=height)


def chart_bar_highlight(categories, current, title, height=300):
    """
    Horizontal bar across a fixed small set of categories (e.g. experience
    level, predicted field) with the current/actual one highlighted in
    accent orange and the rest shown as muted reference bars — an honest way
    to show "you are here" without fabricating a distribution from one data
    point.
    """
    colors = [_CHART_ACCENT if c == current else _CHART_LINE for c in categories]
    values = [1 if c == current else 0.28 for c in categories]
    fig = go.Figure(go.Bar(
        x=values, y=categories, orientation='h',
        marker_color=colors,
        text=['Selected' if c == current else '' for c in categories],
        textposition='inside',
        hovertext=categories, hoverinfo='text',
    ))
    fig.update_layout(xaxis=dict(visible=False), yaxis_title=None)
    return _style_fig(fig, title, height=height)


def group_other(counts, top_n=6, other_label='Other'):
    """
    Collapse a long-tailed value_counts()-style Series down to its top_n
    categories plus a single 'Other' bucket for the rest — so a pie/donut
    never has to render dozens of unreadable slices. No data is dropped,
    just aggregated; if there's nothing left over, 'Other' is omitted.
    """
    s = counts.sort_values(ascending=False)
    if len(s) <= top_n:
        return s
    head = s.iloc[:top_n]
    tail_sum = int(s.iloc[top_n:].sum())
    if tail_sum > 0:
        head = pd.concat([head, pd.Series({other_label: tail_sum})])
    return head


def mask_ip(ip):
    """Partially mask an IPv4 address for display (192.168.1.xxx). Used
    only for chart/UI labels — never changes what's stored in the DB."""
    ip = str(ip)
    parts = ip.split('.')
    if len(parts) == 4:
        return f'{parts[0]}.{parts[1]}.{parts[2]}.xxx'
    return ip


def chart_donut(counts, title, height=340, hover_label='Category'):
    """
    Donut chart from a value_counts()-style Series — used where a real
    multi-item distribution exists (e.g. ratings, experience level or
    resume-score buckets across many records), not for a single record.
    Zero-count categories are fine to include (e.g. a rating nobody gave
    yet) — they show in the legend with 0 / 0%, never fabricated.
    """
    labels = [str(i) for i in counts.index]
    values = [int(v) for v in counts.values]
    total = sum(values) or 1
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=_CHART_PALETTE, line=dict(color='#FFFFFF', width=2)),
        textinfo='percent', textposition='inside',
        customdata=[[hover_label, v, round(v / total * 100, 1)] for v in values],
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>',
        sort=False,
    ))
    return _style_fig(fig, title, height=height, show_legend=True)


def chart_score_donut(scores, title='Resume Score Distribution',
                       bins=((0, 20), (21, 40), (41, 60), (61, 80), (81, 100)), height=340):
    """
    Same fixed score-range buckets as chart_score_histogram, shown as a
    donut instead of bars, per an explicit ask to visualize the *bucketed*
    distribution as a pie/donut — never a pie built directly from raw
    continuous scores. Returns (figure, stats_dict) just like the
    histogram version, so a caller can show both the chart and the
    average/highest/lowest/total stat row.
    """
    s = pd.Series(scores).dropna().astype(float)
    edges = [b[0] for b in bins] + [bins[-1][1] + 1]
    labels = [f'{lo}\u2013{hi}' for lo, hi in bins]
    counts = pd.cut(s, bins=edges, labels=labels, right=False, include_lowest=True).value_counts().reindex(labels, fill_value=0)
    stats = {
        'average': round(s.mean(), 1) if len(s) else 0,
        'highest': int(s.max()) if len(s) else 0,
        'lowest': int(s.min()) if len(s) else 0,
        'total': int(len(s)),
    }
    return chart_donut(counts, title, height=height, hover_label='Score range'), stats


def render_value_card(label, value, subtitle=None, icon=None):
    """
    Clean single-value display for a result that is genuinely one
    category/measurement, not a distribution — e.g. one resume's detected
    experience level or predicted job field. Forcing a single data point
    into a multi-slice pie/bar would mean inventing percentages for
    categories that were never measured; a card states the one real fact
    plainly instead.
    """
    icon_html = f'<span class="ara-value-card-icon">{_esc(icon)}</span>' if icon else ''
    sub_html = f'<div class="ara-value-card-sub">{_esc(subtitle)}</div>' if subtitle else ''
    st.markdown(
        f'<div class="ara-value-card">'
        f'<div class="ara-value-card-label">{_esc(label)}</div>'
        f'<div class="ara-value-card-value">{icon_html}{_esc(value)}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def chart_score_histogram(scores, title, bins=((0, 20), (21, 40), (41, 60), (61, 80), (81, 100)), height=340):
    """
    Buckets a list/Series of 0-100 resume scores into fixed ranges and
    returns (figure, stats_dict) — never a pie chart of individual scores.
    """
    s = pd.Series(scores).dropna().astype(float)
    edges = [b[0] for b in bins] + [bins[-1][1] + 1]
    labels = [f'{lo}\u2013{hi}' for lo, hi in bins]
    counts = pd.cut(s, bins=edges, labels=labels, right=False, include_lowest=True).value_counts().reindex(labels, fill_value=0)
    fig = go.Figure(go.Bar(
        x=labels, y=list(counts.values), marker_color=_CHART_ACCENT,
        text=list(counts.values), textposition='auto',
    ))
    fig.update_layout(xaxis_title='Score range', yaxis_title='Number of resumes')
    stats = {
        'average': round(s.mean(), 1) if len(s) else 0,
        'highest': int(s.max()) if len(s) else 0,
        'lowest': int(s.min()) if len(s) else 0,
        'total': int(len(s)),
    }
    return _style_fig(fig, title, height=height), stats


def chart_gauge(score, title='Resume Score', height=280):
    """0-100 gauge for a single resume's score."""
    fig = go.Figure(go.Indicator(
        mode='gauge+number',
        value=score,
        number={'suffix': ' / 100', 'font': {'family': 'Space Grotesk, sans-serif', 'size': 34}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': _CHART_MUTED},
            'bar': {'color': _CHART_ACCENT},
            'bgcolor': 'white',
            'borderwidth': 1,
            'bordercolor': _CHART_LINE,
            'steps': [
                {'range': [0, 40], 'color': '#FBEAE0'},
                {'range': [40, 70], 'color': '#FDE3D0'},
                {'range': [70, 100], 'color': '#E3F1E8'},
            ],
        },
    ))
    return _style_fig(fig, title, height=height)


def chart_line_over_time(counts_by_date, title='Resume Analysis Activity', height=320):
    """counts_by_date: a Series indexed by date (str, sorted) -> count."""
    s = counts_by_date.sort_index()
    fig = go.Figure(go.Scatter(
        x=list(s.index), y=list(s.values), mode='lines+markers',
        line=dict(color=_CHART_ACCENT, width=2.5),
        marker=dict(color=_CHART_ACCENT, size=6),
        fill='tozeroy', fillcolor='rgba(140,120,189,0.10)',
    ))
    fig.update_layout(xaxis_title='Date', yaxis_title='Resumes analyzed')
    return _style_fig(fig, title, height=height)


def render_stat_row(stats):
    """Small inline stat strip under a chart — e.g. average/highest/lowest/total."""
    cols = st.columns(len(stats))
    for col, (label, value) in zip(cols, stats):
        with col:
            st.markdown(
                f'<div class="ara-stat"><span class="ara-stat-value">{_esc(value)}</span>'
                f'<span class="ara-stat-label">{_esc(label)}</span></div>',
                unsafe_allow_html=True,
            )


def chart_section_completeness(section_status, title='Resume Section Completeness', height=340):
    """section_status: dict of {section_name: bool}. Equal-length bars
    colored by Present/Missing — clearer than a 0-vs-1-length bar for a
    binary status."""
    names = list(section_status.keys())
    present = list(section_status.values())
    colors = [_CHART_GOOD if p else _CHART_LINE for p in present]
    text = ['Present' if p else 'Missing' for p in present]
    text_colors = ['white' if p else _CHART_MUTED for p in present]
    fig = go.Figure(go.Bar(
        x=[1] * len(names), y=names, orientation='h',
        marker_color=colors, text=text, textposition='inside',
        insidetextfont=dict(color=text_colors),
    ))
    fig.update_layout(xaxis=dict(visible=False), yaxis_title=None)
    return _style_fig(fig, title, height=height)


def chart_heatmap(matrix, labels, title, height=360, x_title='Predicted', y_title='Actual'):
    """
    Confusion-matrix style heatmap for the Model page. `matrix` is a list
    of lists (rows = actual class, cols = predicted class), `labels` the
    class names in the same order on both axes. Values are the real
    counts from the training run's evaluation — never invented.
    """
    z = matrix
    text = [[str(v) for v in row] for row in z]
    fig = go.Figure(go.Heatmap(
        z=z, x=labels, y=labels, text=text, texttemplate='%{text}',
        colorscale=[[0, '#FFF3EC'], [1, _CHART_ACCENT]],
        showscale=False,
        hovertemplate=f'{y_title}: %{{y}}<br>{x_title}: %{{x}}<br>Count: %{{z}}<extra></extra>',
    ))
    fig.update_layout(xaxis_title=x_title, yaxis_title=y_title)
    return _style_fig(fig, title, height=height)


def chart_training_metrics(metrics_dict, title='Model Metrics', height=320):
    """Simple bar chart of the headline validation metrics (accuracy,
    precision, recall, f1) for a single trained model version — all real
    numbers computed in trainer.py, never random/hardcoded."""
    names = list(metrics_dict.keys())
    values = [round(float(v) * 100, 1) for v in metrics_dict.values()]
    fig = go.Figure(go.Bar(
        x=names, y=values, marker_color=_CHART_ACCENT,
        text=[f'{v}%' for v in values], textposition='outside', cliponaxis=False,
    ))
    fig.update_layout(yaxis=dict(title='%', range=[0, 100]), xaxis_title=None)
    return _style_fig(fig, title, height=height)


def render_missing_chips(missing_items, empty_message='Every checked section is present — nice work.'):
    """Compact list of ONLY the sections the analyzer found missing, as
    actionable chips. Deliberately not another bar chart of the same data
    as the completeness chart — this is the "what to fix" view, not a
    repeat of the "what's present" view."""
    if not missing_items:
        st.markdown(f'<div class="ara-empty">{_esc(empty_message)}</div>', unsafe_allow_html=True)
        return
    chips = ''.join(f'<span class="ara-chip">Missing: {_esc(item)}</span>' for item in missing_items)
    st.markdown(f'<div class="ara-chip-row">{chips}</div>', unsafe_allow_html=True)


def render_feedback_received():
    """
    Replaces st.balloons() after a feedback submission with a small,
    feedback-specific animation: a checkmark draw-in plus five stars
    appearing in sequence. Pure CSS (no JS/canvas), so it's lightweight and
    respects prefers-reduced-motion (falls back to a static state).
    """
    st.markdown(
        '''
        <div class="ara-feedback-received">
            <div class="ara-feedback-check">
                <svg viewBox="0 0 24 24"><path d="M4 12.5 L9.5 18 L20 6"/></svg>
            </div>
            <div class="ara-feedback-title">Feedback received</div>
            <div class="ara-feedback-sub">Thanks for helping us improve the analyzer.</div>
            <div class="ara-feedback-stars">
                <span>\u2605</span><span>\u2605</span><span>\u2605</span><span>\u2605</span><span>\u2605</span>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def render_model_network_viz(feature_count=120, num_classes=5, sample_count=0, active_stage="Ready", is_training=False):
    """
    Renders an animated SVG architectural diagram representing real-time feature flow:
    Input Features (skills & metadata) -> Feature Transformer / Ensembles -> Multiclass Career Predictions.
    Dynamically highlights layers based on whether training is active or completed.
    """
    pulse_cls = "ara-node-pulse" if is_training else ""
    glow_stroke = "#8C78BD" if is_training else "#94a3b8"
    speed = "0.7s" if is_training else "2.5s"
    status_label = f"⚡ TRAINING ACTIVE: {active_stage}" if is_training else f"🟢 MODEL ARCHITECTURE: Ready ({sample_count} Samples Loaded)"

    st.markdown(
        f'''
        <style>
        .ara-net-container {{
            background: linear-gradient(135deg, rgba(255, 90, 31, 0.06) 0%, rgba(30, 41, 59, 0.03) 100%);
            border: 1px solid var(--ara-line, #e2e8f0);
            border-radius: 12px;
            padding: 16px 20px;
            margin: 12px 0 20px 0;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        }}
        .ara-flow-line {{
            stroke-dasharray: 6, 4;
            animation: flowDash {speed} linear infinite;
        }}
        @keyframes flowDash {{
            from {{ stroke-dashoffset: 20; }}
            to {{ stroke-dashoffset: 0; }}
        }}
        .ara-node-pulse {{
            animation: nodeGlow 0.8s infinite alternate ease-in-out;
        }}
        @keyframes nodeGlow {{
            0% {{ filter: drop-shadow(0 0 2px #8C78BD); transform: scale(0.97); opacity: 0.8; }}
            100% {{ filter: drop-shadow(0 0 10px #8C78BD); transform: scale(1.05); opacity: 1; }}
        }}
        .ara-net-caption {{
            font-size: 0.86rem;
            color: var(--ara-muted, #475569);
            margin-top: 10px;
            font-weight: 600;
        }}
        .ara-stage-badge {{
            display: inline-block;
            background: {'#FFEBE1' if is_training else '#E2E8F0'};
            color: {'#C2410C' if is_training else '#334155'};
            font-size: 0.78rem;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 999px;
            margin-bottom: 8px;
        }}
        </style>
        <div class="ara-net-container">
            <div class="ara-stage-badge">{status_label}</div>
            <svg viewBox="0 0 760 170" width="100%" height="165" style="max-width: 760px; margin: auto;">
                <!-- Animated Synaptic Connections -->
                <g stroke="{glow_stroke}" stroke-width="{1.6 if is_training else 1.1}" stroke-opacity="{0.55 if is_training else 0.25}" class="{'ara-flow-line' if is_training else ''}">
                    <!-- Inputs to Hidden -->
                    <line x1="85" y1="35" x2="250" y2="45" />
                    <line x1="85" y1="35" x2="250" y2="85" />
                    <line x1="85" y1="70" x2="250" y2="45" />
                    <line x1="85" y1="70" x2="250" y2="85" />
                    <line x1="85" y1="70" x2="250" y2="125" />
                    <line x1="85" y1="105" x2="250" y2="85" />
                    <line x1="85" y1="105" x2="250" y2="125" />
                    <line x1="85" y1="140" x2="250" y2="125" />

                    <!-- Hidden to Estimator -->
                    <line x1="250" y1="45" x2="470" y2="55" />
                    <line x1="250" y1="45" x2="470" y2="115" />
                    <line x1="250" y1="85" x2="470" y2="55" />
                    <line x1="250" y1="85" x2="470" y2="115" />
                    <line x1="250" y1="125" x2="470" y2="55" />
                    <line x1="250" y1="125" x2="470" y2="115" />

                    <!-- Estimator to Target Classes -->
                    <line x1="470" y1="55" x2="675" y2="40" />
                    <line x1="470" y1="55" x2="675" y2="85" />
                    <line x1="470" y1="55" x2="675" y2="130" />
                    <line x1="470" y1="115" x2="675" y2="40" />
                    <line x1="470" y1="115" x2="675" y2="85" />
                    <line x1="470" y1="115" x2="675" y2="130" />
                </g>

                <!-- Input Layer Nodes -->
                <g class="{pulse_cls}">
                    <circle cx="85" cy="35" r="9" fill="#8C78BD" />
                    <circle cx="85" cy="70" r="9" fill="#8C78BD" />
                    <circle cx="85" cy="105" r="9" fill="#8C78BD" />
                    <circle cx="85" cy="140" r="9" fill="#8C78BD" />
                </g>
                <text x="85" y="162" text-anchor="middle" font-size="11" font-weight="700" fill="#334155">Input Features ({feature_count})</text>

                <!-- Representation Layer -->
                <g class="{pulse_cls}">
                    <circle cx="250" cy="45" r="10" fill="#2563EB" />
                    <circle cx="250" cy="85" r="10" fill="#2563EB" />
                    <circle cx="250" cy="125" r="10" fill="#2563EB" />
                </g>
                <text x="250" y="162" text-anchor="middle" font-size="11" font-weight="700" fill="#334155">Feature Encoders (Dense/Sparse)</text>

                <!-- Classifier Ensemble Layer -->
                <g class="{pulse_cls}">
                    <circle cx="470" cy="55" r="11" fill="#7C3AED" />
                    <circle cx="470" cy="115" r="11" fill="#7C3AED" />
                </g>
                <text x="470" y="162" text-anchor="middle" font-size="11" font-weight="700" fill="#334155">Classifier / Calibration</text>

                <!-- Output Layer -->
                <g class="{pulse_cls}">
                    <circle cx="675" cy="40" r="10" fill="#059669" />
                    <circle cx="675" cy="85" r="10" fill="#059669" />
                    <circle cx="675" cy="130" r="10" fill="#059669" />
                </g>
                <text x="675" y="162" text-anchor="middle" font-size="11" font-weight="700" fill="#334155">Career Targets ({num_classes})</text>
            </svg>
            <div class="ara-net-caption">Real-Time Data Pipeline: {sample_count} Training Resumes ➔ Skill Indicators ➔ Estimator Fit ➔ Multiclass Output</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def render_model_comparison_card(prev_metrics, new_metrics, prev_ver, new_ver, promoted):
    """Show numeric metrics without ranking incomparable evaluation splits."""
    previous=prev_metrics or {}
    current=new_metrics or {}
    with st.container(border=True):
        st.subheader('Model evaluation comparison')
        rows=[]
        for title,key in [('Held-out accuracy','validation_accuracy'),('Held-out log loss','validation_loss'),('Weighted F1','f1'),('Precision','precision'),('Recall','recall'),('Training records','training_samples'),('Test records','validation_samples')]:
            rows.append({'Metric':title, str(prev_ver or 'No previous model'):previous.get(key),str(new_ver):current.get(key)})
        st.dataframe(pd.DataFrame(rows),hide_index=True)
        st.caption(current.get('validation_note','Evaluation split details unavailable.'))
        st.caption('Metrics from different datasets or splits are descriptive and cannot establish that one model is better. Inspect test composition and class balance before activation.')
        if promoted:st.success('This model was activated.')
        else:st.info('Saved as an inactive model. Review its evaluation and activate it explicitly when appropriate.')
