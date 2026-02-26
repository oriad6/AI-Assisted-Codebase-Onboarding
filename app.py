import streamlit as st
import google.generativeai as genai
from pathlib import Path
import requests
import hashlib
import json
import socket
import html as _html
from urllib.parse import quote_plus
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
import streamlit.components.v1 as components

try:
    from markdown import markdown as _md_to_html
except Exception:
    _md_to_html = None

# --- Configuration & Setup ---
st.set_page_config(
    page_title="Code Repository Onboarding",
    page_icon="🤖",
    layout="wide"
)

# --- Custom Icons & Styles ---
BOT_ICON = "🤖"  # Using emoji with styling for reliability
USER_ICON = "👤"

def render_bot_icon(size=40):
    # Use the native emoji directly to avoid grayscale/fallback rendering issues
    return f'<span style="font-size:{size}px; line-height:{size}px; display:inline-block;">{BOT_ICON}</span>'

def _safe_markdown_to_html(md_text: str) -> str:
    escaped = _html.escape(md_text or "")
    if _md_to_html is None:
        return escaped.replace("\n", "<br/>")
    return _md_to_html(
        escaped,
        extensions=[
            "fenced_code",
            "tables",
            "nl2br",
        ],
        output_format="html5",
    )

def _lottie_html(src_url: str, *, height_px: int = 180, caption=None) -> str:
    safe_src = _html.escape(src_url, quote=True)
    safe_caption = _html.escape(caption or "")
    caption_html = f'<div class="lottie-caption">{safe_caption}</div>' if caption else ""
    return f"""
    <div class="lottie-card">
      <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
      <lottie-player
        src="{safe_src}"
        background="transparent"
        speed="1"
        style="width: {height_px}px; height: {height_px}px;"
        loop
        autoplay
      ></lottie-player>
      {caption_html}
    </div>
    """

def _inject_theme_css(*, variant: str, light_mode: bool) -> None:
    # Two dark palettes ("Deep Sea" and "Cyberpunk") + a light mode toggle that flips surface/text while keeping accent vibe.
    variant = variant.strip().lower()
    if variant not in {"deep sea", "cyberpunk"}:
        variant = "deep sea"

    if variant == "cyberpunk":
        accent = "#ff3df2"
        accent_2 = "#33f6ff"
        glow = "rgba(255, 61, 242, 0.28)"
        glow_2 = "rgba(51, 246, 255, 0.22)"
    else:
        accent = "#19f1c2"
        accent_2 = "#2d7dff"
        glow = "rgba(25, 241, 194, 0.22)"
        glow_2 = "rgba(45, 125, 255, 0.20)"

    if light_mode:
        bg0 = "#f7fbff"
        bg1 = "#eef5ff"
        surface = "rgba(255, 255, 255, 0.72)"
        surface_2 = "rgba(255, 255, 255, 0.58)"
        border = "rgba(10, 20, 30, 0.12)"
        text = "rgba(12, 18, 24, 0.92)"
        text_muted = "rgba(12, 18, 24, 0.62)"
        shadow = "0 18px 44px rgba(2, 10, 18, 0.14)"
        tab_bg = "rgba(255, 255, 255, 0.55)"
    else:
        bg0 = "#060816"
        bg1 = "#050b18"
        surface = "rgba(255, 255, 255, 0.06)"
        surface_2 = "rgba(255, 255, 255, 0.035)"
        border = "rgba(255, 255, 255, 0.10)"
        text = "rgba(242, 248, 255, 0.96)"
        text_muted = "rgba(242, 248, 255, 0.80)"
        shadow = "0 22px 60px rgba(0, 0, 0, 0.55)"
        tab_bg = "rgba(255, 255, 255, 0.04)"

    css = f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&family=Space+Grotesk:wght@400;600&display=swap');

      :root {{
        --bg0: {bg0};
        --bg1: {bg1};
        --surface: {surface};
        --surface2: {surface_2};
        --border: {border};
        --text: {text};
        --muted: {text_muted};
        --accent: {accent};
        --accent2: {accent_2};
        --glow: {glow};
        --glow2: {glow_2};
        --shadow: {shadow};
        --tabbg: {tab_bg};
        --r-xl: 22px;
        --r-lg: 16px;
        --r-md: 12px;
      }}

      html, body, [data-testid="stAppViewContainer"] {{
        background:
          radial-gradient(1200px 600px at 12% 8%, var(--glow), transparent 60%),
          radial-gradient(900px 520px at 86% 18%, var(--glow2), transparent 62%),
          linear-gradient(180deg, var(--bg0), var(--bg1));
        color: var(--text);
        font-family: "Space Grotesk", system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      }}
      /* Remove default white header bar but keep icons */
      [data-testid="stHeader"] {{
        background: transparent !important;
        box-shadow: none !important;
      }}
      [data-testid="stHeader"] > div {{
        background: transparent !important;
      }}

      /* Subtle animated scanline / shimmer */
      [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background:
          linear-gradient(to bottom, rgba(255,255,255,0.03), rgba(255,255,255,0.00) 18%, rgba(255,255,255,0.02) 40%, rgba(255,255,255,0.00)),
          repeating-linear-gradient(to bottom, rgba(255,255,255,0.03) 0px, rgba(255,255,255,0.03) 1px, transparent 2px, transparent 6px);
        opacity: {0.16 if not light_mode else 0.06};
        mix-blend-mode: overlay;
        transform: translateZ(0);
        animation: scan 9s linear infinite;
      }}
      @keyframes scan {{
        0% {{ transform: translateY(-6%); }}
        100% {{ transform: translateY(6%); }}
      }}

      /* Header typography */
      h1, h2, h3, [data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3 {{
        font-family: "Orbitron", "Space Grotesk", system-ui, sans-serif !important;
        letter-spacing: 0.6px;
      }}

      /* Sidebar: glass + consistent spacing */
      [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
        border-right: 1px solid var(--border);
        backdrop-filter: blur(14px);
      }}
      [data-testid="stSidebar"] * {{
        color: var(--text) !important;
      }}

      /* Buttons */
      .stButton > button {{
        border-radius: 999px !important;
        border: 1px solid var(--border) !important;
        background: linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04)) !important;
        color: var(--text) !important;
        box-shadow: 0 10px 28px rgba(0,0,0,0.22);
        transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease, filter 160ms ease;
      }}
      .stButton > button:hover {{
        transform: translateY(-1px);
        border-color: color-mix(in srgb, var(--accent) 45%, var(--border)) !important;
        box-shadow: 0 18px 44px rgba(0,0,0,0.30);
        filter: saturate(1.08);
      }}
      .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 80%, #000 20%), color-mix(in srgb, var(--accent2) 75%, #000 25%)) !important;
        border: 1px solid color-mix(in srgb, var(--accent) 45%, var(--border)) !important;
        color: white !important;
        box-shadow: 0 18px 46px color-mix(in srgb, var(--accent) 22%, rgba(0,0,0,0.60));
      }}

      /* Inputs */
      /* Clear standard Streamlit wrapper backgrounds to fix white text on white background in dark mode */
      [data-baseweb="base-input"],
      [data-baseweb="input"] {{
        background-color: transparent !important;
        border: none !important;
      }}
      .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] > div {{
        border-radius: 14px !important;
        border: 1px solid var(--border) !important;
        background-color: {"var(--surface2)" if light_mode else "#0b101a"} !important;
        color: {"var(--text)" if light_mode else "#ffffff"} !important;
        backdrop-filter: blur(10px);
      }}
      .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
        color: var(--muted) !important;
      }}
      .stTextInput label, .stTextArea label, .stSelectbox label {{
        color: var(--text) !important;
      }}
      /* Make sure sidebar auth/API inputs are always readable, especially in dark mode */
      [data-testid="stSidebar"] input[type="text"],
      [data-testid="stSidebar"] input[type="password"] {{
        background-color: {"var(--surface2)" if light_mode else "#0b101a"} !important;
        color: {"#0c1218" if light_mode else "#ffffff"} !important;
      }}
      [data-testid="stSidebar"] input[type="text"]::placeholder,
      [data-testid="stSidebar"] input[type="password"]::placeholder {{
        color: {"rgba(12,18,24,0.65)" if light_mode else "rgba(255,255,255,0.78)"} !important;
      }}
      .stTextInput input:focus, .stTextArea textarea:focus {{
        outline: none !important;
        border-color: color-mix(in srgb, var(--accent) 55%, var(--border)) !important;
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 22%, transparent) !important;
      }}
      /* Fallback for any other plain inputs/textareas (inside tabs, expanders, etc.) */
      input, textarea {{
        color: var(--text) !important;
      }}
      input::placeholder, textarea::placeholder {{
        color: var(--muted) !important;
      }}

      /* Fix for browser autofill making background white while text remains white */
      input:-webkit-autofill,
      input:-webkit-autofill:hover, 
      input:-webkit-autofill:focus, 
      input:-webkit-autofill:active {{
        -webkit-text-fill-color: #000000 !important;
        -webkit-box-shadow: 0 0 0px 1000px #ffffff inset !important;
      }}
      /* Force black text on any pure-white background blocks so content is always readable */
      [style*="background-color: rgb(255, 255, 255"] ,
      [style*="background-color: #ffffff"],
      [style*="background: #ffffff"],
      [style*="background: rgb(255, 255, 255"] {{
        color: #000000 !important;
      }}
      [style*="background-color: rgb(255, 255, 255"] input,
      [style*="background-color: #ffffff"] input,
      [style*="background: #ffffff"] input,
      [style*="background: rgb(255, 255, 255"] input,
      [style*="background-color: rgb(255, 255, 255"] textarea,
      [style*="background-color: #ffffff"] textarea,
      [style*="background: #ffffff"] textarea,
      [style*="background: rgb(255, 255, 255"] textarea {{
        color: #000000 !important;
      }}

      /* Tabs: smooth, animated */
      [data-testid="stTabs"] [data-baseweb="tab-list"] {{
        background: var(--tabbg);
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 6px;
        backdrop-filter: blur(12px);
        box-shadow: var(--shadow);
      }}
      [data-testid="stTabs"] button[role="tab"] {{
        border-radius: 999px !important;
        color: var(--muted) !important;
        transition: background 180ms ease, color 180ms ease, transform 180ms ease;
      }}
      [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
        background: linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.05));
        color: var(--text) !important;
        transform: translateY(-1px);
        border: 1px solid color-mix(in srgb, var(--accent) 35%, var(--border));
        box-shadow: 0 14px 38px rgba(0,0,0,0.25);
      }}
      [data-testid="stTabs"] [data-baseweb="tab-panel"] {{
        animation: fadeInUp 240ms ease both;
      }}
      @keyframes fadeInUp {{
        from {{ opacity: 0; transform: translateY(8px); }}
        to {{ opacity: 1; transform: translateY(0); }}
      }}

      /* Glass cards (use border containers) */
      [data-testid="stVerticalBlockBorderWrapper"] {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-xl);
        backdrop-filter: blur(14px);
        box-shadow: var(--shadow);
        transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
      }}
      [data-testid="stVerticalBlockBorderWrapper"]:hover {{
        transform: translateY(-2px);
        border-color: color-mix(in srgb, var(--accent) 35%, var(--border));
        box-shadow: 0 26px 74px rgba(0,0,0,0.42);
      }}

      /* Metric polish */
      [data-testid="stMetric"] {{
        background: transparent;
      }}

      /* AI badge for title icon */
      .ai-badge {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 10px;
        border-radius: 999px;
        background: linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04));
        border: 1px solid color-mix(in srgb, var(--accent) 28%, var(--border));
        box-shadow: 0 18px 52px color-mix(in srgb, var(--accent) 18%, rgba(0,0,0,0.6));
        backdrop-filter: blur(10px);
      }}

      /* Lottie block */
      .lottie-card {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 10px 6px 4px;
      }}
      .lottie-caption {{
        margin-top: 6px;
        font-size: 13px;
        color: var(--muted);
        letter-spacing: 0.2px;
      }}

      /* Chat bubbles (custom HTML renderer) */
      .chat-row {{
        display: flex;
        width: 100%;
        margin: 10px 0;
        align-items: flex-end;
      }}
      .bubble {{
        max-width: min(720px, 86%);
        padding: 12px 14px;
        border-radius: 18px;
        border: 1px solid var(--border);
        backdrop-filter: blur(14px);
        box-shadow: 0 18px 50px rgba(0,0,0,0.26);
        line-height: 1.45;
      }}
      .bubble.user {{
        background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 40%, transparent), rgba(255,255,255,0.06));
        border-color: color-mix(in srgb, var(--accent) 35%, var(--border));
      }}
      .bubble.assistant {{
        background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
      }}
      .bubble pre, .bubble code {{
        background: rgba(0,0,0,0.18);
        border-radius: 12px;
        padding: 2px 6px;
      }}
      .bubble table {{
        width: 100%;
        border-collapse: collapse;
      }}
      .bubble table, .bubble th, .bubble td {{
        border: 1px solid var(--border);
      }}
      .bubble th, .bubble td {{
        padding: 6px 8px;
      }}
      .chat-icon {{
        width: 32px;
        height: 32px;
        border-radius: 999px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 8px;
        font-size: 18px;
        background: linear-gradient(135deg, rgba(255,255,255,0.14), rgba(255,255,255,0.03));
        border: 1px solid color-mix(in srgb, var(--accent) 20%, var(--border));
        box-shadow: 0 10px 26px rgba(0,0,0,0.35);
      }}
      .chat-row.user {{
        justify-content: flex-end;
      }}
      .chat-row.user .chat-icon {{
        order: 2;
        margin-right: 0;
      }}
      .chat-row.user .bubble {{
        order: 1;
      }}
      .chat-row.assistant {{
        justify-content: flex-start;
      }}
      .chat-row.assistant .chat-icon {{
        order: 1;
        margin-left: 0;
      }}
      .chat-row.assistant .bubble {{
        order: 2;
      }}

      /* Make expanders feel more premium and fix white backgrounds in dark mode */
      details {{
        border-radius: 14px;
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
      }}
      details > summary {{
        background: transparent !important;
        color: var(--text) !important;
      }}
      details [data-testid="stExpanderDetails"] {{
        background: transparent !important;
      }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# --- Database Setup (SQLAlchemy) ---
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    projects = relationship("Project", back_populates="user")

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    name = Column(String, nullable=False)
    source_type = Column(String) # 'github' or 'upload'
    repo_url = Column(String)
    code_context = Column(Text)
    analysis_module = Column(Text)
    analysis_risk = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="projects")

def get_db_session():
    try:
        if "postgres" in st.secrets:
            secrets = st.secrets["postgres"]
            user = quote_plus(secrets["user"])
            password = quote_plus(secrets["password"])
            host = secrets["host"]
            port = secrets["port"]
            dbname = secrets["dbname"]
            db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        elif "database" in st.secrets and "url" in st.secrets["database"]:
            db_url = st.secrets["database"]["url"]
        else: return None
        # pool_pre_ping ensures we don't use stale connections, solving a common 2-click delay
        engine = create_engine(db_url, pool_pre_ping=True)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None

# --- Session State & Persistence ---
if 'user_info' not in st.session_state: st.session_state['user_info'] = None
if 'analysis_module' not in st.session_state: st.session_state['analysis_module'] = ""
if 'analysis_risk' not in st.session_state: st.session_state['analysis_risk'] = ""
if 'full_code_context' not in st.session_state: st.session_state['full_code_context'] = ""
if 'uploaded_files_data' not in st.session_state: st.session_state['uploaded_files_data'] = []
if 'messages' not in st.session_state: st.session_state['messages'] = []
if 'project_source' not in st.session_state: st.session_state['project_source'] = None
if 'current_repo_url' not in st.session_state: st.session_state['current_repo_url'] = ""
if 'show_import_screen' not in st.session_state: st.session_state['show_import_screen'] = False
if 'is_loaded_from_db' not in st.session_state: st.session_state['is_loaded_from_db'] = False
if "ui_theme_variant" not in st.session_state: st.session_state["ui_theme_variant"] = "Deep Sea"
if "ui_light_mode" not in st.session_state: st.session_state["ui_light_mode"] = False

session = get_db_session()

# Persistent Login Check
if not st.session_state['user_info'] and "user_token" in st.query_params:
    token = st.query_params["user_token"]
    if session:
        user = session.query(User).filter(User.password_hash == token).first()
        if user:
            st.session_state['user_info'] = {'id': user.id, 'username': user.username}

# --- Auth Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(session, username, password):
    try:
        pw_hash = hash_password(password)
        user = session.query(User).filter_by(username=username, password_hash=pw_hash).first()
        if user:
            st.query_params["user_token"] = pw_hash
        return user
    except: return None

def register_user(session, username, password):
    try:
        if session.query(User).filter_by(username=username).first():
            return False, "Username already exists"
        new_user = User(username=username, password_hash=hash_password(password))
        session.add(new_user)
        session.commit()
        return True, "Registration successful! Please login."
    except Exception as e:
        session.rollback()
        return False, str(e)

# --- AI Helper Functions ---
def generate_content_with_fallback(prompt, api_key, generation_config=None):
    try:
        genai.configure(api_key=api_key)
        try:
            models = genai.list_models()
            available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        except: available_models = ["gemini-1.5-pro", "gemini-1.5-flash"]
        priority_order = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]
        sorted_models = sorted(available_models, key=lambda m: next((i for i, p in enumerate(priority_order) if p in m), len(priority_order)))
        errors = []
        for model_name in sorted_models:
            if "embedding" in model_name: continue
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config=generation_config)
                return response.text, model_name
            except Exception as e: errors.append(f"{model_name}: {str(e)}")
        return f"All models failed. {'; '.join(errors)}", "Error"
    except Exception as e: return f"Unexpected Error: {str(e)}", "Error"

def fetch_github_repo(repo_url):
    try:
        clean_url = repo_url.rstrip("/")
        if not clean_url.startswith("https://github.com/"): return None, "Invalid GitHub URL."
        parts = clean_url.split("/")
        if len(parts) < 5: return None, "Invalid URL format."
        owner, repo = parts[3], parts[4]
        branches = ['main', 'master']
        tree_data = None
        used_branch = None
        for branch in branches:
            api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            resp = requests.get(api_url)
            if resp.status_code == 200:
                tree_data = resp.json().get('tree', [])
                used_branch = branch
                break
        if not tree_data: return None, "Repo not found or branch issue."
        files_data = []
        allowed_ext = {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.cpp', '.c', '.h', '.rs', '.php', '.rb', '.css', '.html', '.json', '.sql', '.yaml', '.yml', '.md'}
        count = 0
        for item in tree_data:
            if item['type'] == 'blob' and Path(item['path']).suffix in allowed_ext:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{used_branch}/{item['path']}"
                r = requests.get(raw_url)
                if r.status_code == 200:
                    files_data.append({"name": item['path'], "content": r.text, "size": len(r.content)})
                    count+=1
                    if count >= 60: break
        if not files_data: return None, "No code files found."
        return files_data, None
    except Exception as e: return None, str(e)

# --- Sidebar ---
with st.sidebar:
    st.subheader("🎨 Appearance")
    st.radio(
        "Theme",
        ["Deep Sea", "Cyberpunk"],
        key="ui_theme_variant",
        horizontal=True,
        help="Choose your vibe. Both are dark-first; use the toggle below for Light mode.",
    )
    st.toggle("🌗 Dark / Light mode", key="ui_light_mode")
    st.divider()

    st.title("🔐 Account")
    if st.session_state['user_info']:
        st.success(f"Hi, {st.session_state['user_info']['username']}")
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()
    else:
        tab_login, tab_reg = st.tabs(["Login", "Register"])
        with tab_login:
            l_user = st.text_input("Username", key="l_u")
            l_pass = st.text_input("Password", type="password", key="l_p")
            if st.button("Login", type="primary", use_container_width=True):
                if session:
                    user = login_user(session, l_user, l_pass)
                    if user:
                        st.session_state['user_info'] = {'id': user.id, 'username': user.username}
                        st.session_state['show_import_screen'] = False
                        st.rerun()
                    else: st.error("Invalid credentials")
                else: st.error("DB Connection Failed")
        with tab_reg:
            r_user = st.text_input("Username", key="r_u")
            r_pass = st.text_input("Password", type="password", key="r_p")
            if st.button("Register", use_container_width=True):
                if session:
                    ok, msg = register_user(session, r_user, r_pass)
                    if ok: st.success(msg)
                    else: st.error(msg)
                else: st.error("DB Connection Failed")

    st.divider()
    with st.expander("⚙️ API Settings", expanded=True):
        api_key_help = "Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey) 🔗"
        api_key = st.text_input("Google AI API Key 🔑", type="password", help=api_key_help)
        if api_key:
            if st.button("🔍 Test API Connection", use_container_width=True):
                with st.spinner("Testing..."):
                    try:
                        genai.configure(api_key=api_key)
                        models = genai.list_models()
                        model_names = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
                        if model_names: st.success(f"✅ Connection Successful! Found {len(model_names)} models.")
                        else: st.warning("⚠️ Connected, but no text models found.")
                    except Exception as e: st.error(f"❌ Connection Failed: {str(e)}")

    if st.session_state['user_info'] and (st.session_state['uploaded_files_data'] or st.session_state['full_code_context']):
        st.divider()
        if st.button("🏠 Project Selection", use_container_width=True):
            st.session_state['uploaded_files_data'] = []
            st.session_state['full_code_context'] = ""
            st.session_state['analysis_module'] = ""
            st.session_state['analysis_risk'] = ""
            st.session_state['is_loaded_from_db'] = False
            st.session_state['show_import_screen'] = False
            st.session_state['messages'] = []
            st.rerun()

# Apply theme after sidebar widgets set state (avoids 1-rerun lag).
_inject_theme_css(variant=st.session_state["ui_theme_variant"], light_mode=bool(st.session_state["ui_light_mode"]))

# Styled Main Title
st.markdown(f'<div style="display:flex; align-items:center; margin-bottom:20px;">{render_bot_icon(50)}<h1 style="margin-left:15px; margin-top:0;">Code Repository Onboarding</h1></div>', unsafe_allow_html=True)

if not st.session_state['user_info']:
    st.info("Welcome! Please login to start analyzing code repositories.")
    st.image("https://img.icons8.com/clouds/200/code.png")

elif not st.session_state['uploaded_files_data'] and not st.session_state['show_import_screen']:
    st.header("Projects History")
    col_new, _ = st.columns([1, 3])
    with col_new:
        if st.button("➕ Analyze New Project", type="primary", use_container_width=True):
            st.session_state['show_import_screen'] = True
            st.rerun()
    st.divider()
    if session:
        try:
            projects = session.query(Project).filter_by(user_id=st.session_state['user_info']['id']).order_by(Project.created_at.desc()).all()
            if projects:
                per_row = 3
                for i in range(0, len(projects), per_row):
                    cols = st.columns(per_row, gap="large")
                    for col, p in zip(cols, projects[i : i + per_row]):
                        with col:
                            with st.container(border=True):
                                display_name = p.name
                                if "github.com/" in str(p.repo_url or ""):
                                    display_name = (p.repo_url or "").split("/")[-1] or p.name
                                st.markdown(f"**{display_name}**")
                                st.caption(f"📅 {p.created_at.strftime('%Y-%m-%d %H:%M')}")

                                meta_bits = []
                                if p.source_type == "github":
                                    meta_bits.append("GitHub")
                                elif p.source_type == "upload":
                                    meta_bits.append("Upload")
                                if p.repo_url:
                                    meta_bits.append(str(p.repo_url))
                                if meta_bits:
                                    st.caption(" · ".join(meta_bits))

                                tags = []
                                if (p.analysis_module or "").strip():
                                    tags.append("Module analysis ✓")
                                if (p.analysis_risk or "").strip():
                                    tags.append("Risk map ✓")
                                if tags:
                                    st.caption(" | ".join(tags))

                                if st.button("📂 Open", key=f"load_{p.id}", use_container_width=True):
                                    # Base assignment
                                    mod_text = (p.analysis_module or "").strip()
                                    risk_text = (p.analysis_risk or "").strip()

                                    # Fix legacy saves where analysis was stored combined
                                    combined_blob = ""
                                    if risk_text and "<<<SEP>>>" in risk_text:
                                        combined_blob = risk_text
                                    elif mod_text and "<<<SEP>>>" in mod_text:
                                        combined_blob = mod_text
                                    elif mod_text and not risk_text and "RISK MAP" in mod_text.upper():
                                        combined_blob = mod_text
                                    elif risk_text and not mod_text and "MODULE ANALYSIS" in risk_text.upper():
                                        combined_blob = risk_text
                                        
                                    if combined_blob:
                                        if "<<<SEP>>>" in combined_blob:
                                            p1, p2 = combined_blob.split("<<<SEP>>>", 1)
                                            mod_text, risk_text = p1.strip(), p2.strip()
                                        else:
                                            # Fallback split if AI forgot the token
                                            import re
                                            split_match = re.split(r'(?:\n##\s*(?:(?:2\.)?\s*RISK MAP).*|\n#\s*(?:(?:2\.)?\s*RISK MAP).*)', combined_blob, 1, flags=re.IGNORECASE)
                                            if len(split_match) == 2:
                                                mod_text = split_match[0].strip()
                                                # Re-add the header since split consumes it
                                                risk_text = "## RISK MAP\n" + split_match[1].strip()
                                        
                                        # Save back the split versions
                                        try:
                                            p.analysis_module = mod_text
                                            p.analysis_risk = risk_text
                                            session.add(p)
                                            session.commit()
                                        except Exception:
                                            pass
                                            
                                    st.session_state['full_code_context'] = p.code_context
                                    st.session_state['analysis_module'] = mod_text
                                    st.session_state['analysis_risk'] = risk_text
                                    st.session_state['uploaded_files_data'] = [{"name": display_name, "content": "Project Data Loaded"}]
                                    st.session_state['project_source'] = p.source_type
                                    st.session_state['current_repo_url'] = p.repo_url
                                    st.session_state['is_loaded_from_db'] = True
                                    st.session_state['messages'] = []
                                    st.rerun()
            else: st.info("No saved projects found.")
        except Exception as e: 
            st.error(f"Error loading history: {e}")

elif st.session_state['show_import_screen'] and not st.session_state['uploaded_files_data']:
    if st.button("🔙 Back to History"):
        st.session_state['show_import_screen'] = False
        st.rerun()
    st.info("Choose a source to import your code:")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("GitHub Repository")
        repo_url = st.text_input("Enter Link", placeholder="https://github.com/...")
        if st.button("Fetch GitHub Code", type="primary", use_container_width=True):
            with st.spinner("Fetching..."):
                files, err = fetch_github_repo(repo_url)
                if files:
                    st.session_state['uploaded_files_data'] = files
                    st.session_state['full_code_context'] = "".join([f"\n--- {f['name']} ---\n{f['content']}" for f in files])
                    st.session_state['project_source'] = "github"
                    st.session_state['current_repo_url'] = repo_url
                    st.session_state['show_import_screen'] = False
                    st.session_state['is_loaded_from_db'] = False
                    st.session_state['messages'] = []
                    st.rerun()
                else: st.error(err)
    with col2:
        st.subheader("File Upload")
        uploaded = st.file_uploader("Select Files", accept_multiple_files=True)
        if uploaded:
            if st.button("Process Files", type="primary", use_container_width=True):
                files_out = []
                for f in uploaded:
                    try: 
                        txt = f.getvalue().decode('utf-8')
                        files_out.append({"name": f.name, "content": txt, "size": len(txt)})
                    except: pass
                if files_out:
                    st.session_state['uploaded_files_data'] = files_out
                    st.session_state['full_code_context'] = "".join([f"\n--- {f['name']} ---\n{f['content']}" for f in files_out])
                    st.session_state['project_source'] = "upload"
                    st.session_state['current_repo_url'] = "Local Upload"
                    st.session_state['show_import_screen'] = False
                    st.session_state['is_loaded_from_db'] = False
                    st.session_state['messages'] = []
                    st.rerun()
                else: st.error("No valid text files.")

else:
    t1, t2, t3, t4 = st.tabs(["📊 Structure", "🔍 Module Analysis", "🗺️ Risk Map", "💬 Ask Your Code"])
    with t1:
        top_a, top_b, top_c, top_d = st.columns(4, gap="large")
        with top_a:
            with st.container(border=True):
                st.metric("Total Files", len(st.session_state["uploaded_files_data"]))
        with top_b:
            with st.container(border=True):
                st.metric("Source", st.session_state.get("project_source") or "—")
        with top_c:
            with st.container(border=True):
                st.metric("Context Loaded", "Yes" if bool(st.session_state.get("full_code_context")) else "No")
        with top_d:
            with st.container(border=True):
                st.metric("From History", "Yes" if st.session_state.get("is_loaded_from_db") else "No")

        st.markdown("### System Structure")
        files = st.session_state["uploaded_files_data"]
        per_row = 3
        for i in range(0, len(files), per_row):
            cols = st.columns(per_row, gap="large")
            for col, f in zip(cols, files[i : i + per_row]):
                with col:
                    with st.container(border=True):
                        name = f.get("name", "Unknown")
                        p = Path(name)
                        st.markdown(f"**{p.name}**")
                        st.caption(str(name))
                        sz = f.get("size")
                        if sz is not None:
                            st.caption(f"{sz:,} bytes")
                        if not st.session_state["is_loaded_from_db"] and "content" in f:
                            with st.expander("Preview"):
                                lang = p.suffix.lstrip(".") if p.suffix else "text"
                                st.code((f.get("content") or "")[:800], language=lang)
                        else:
                            st.caption("AI context available. Reprocess to view full files here.")
                    
    with t2:
        if st.session_state['user_info']:
            c_save1, c_save2 = st.columns([3, 1])
            save_name_val = st.session_state['current_repo_url'].split("/")[-1] if "/" in st.session_state['current_repo_url'] else "My Project"
            save_name = c_save1.text_input("Project Name", value=save_name_val, label_visibility="collapsed", placeholder="Project Name")
            if c_save2.button("💾 Save Project", use_container_width=True):
                if session:
                    try:
                        # CRITICAL: Ensure we save the LATEST analysis state
                        new_p = Project(
                            user_id=st.session_state['user_info']['id'], 
                            name=save_name, 
                            source_type=st.session_state['project_source'], 
                            repo_url=st.session_state['current_repo_url'], 
                            code_context=st.session_state['full_code_context'], 
                            analysis_module=st.session_state['analysis_module'], 
                            analysis_risk=st.session_state['analysis_risk']
                        )
                        session.add(new_p)
                        session.commit()
                        st.success("Project saved successfully!")
                    except Exception as e: st.error(f"Save failed: {e}")
                else: st.error("DB Connection Failed")
        
        if st.button("🚀 Start AI Analysis", type="primary"):
            if not api_key: st.error("Please provide an API Key in settings.")
            else:
                lottie = st.empty()
                lottie.markdown(
                    _lottie_html(
                        "https://raw.githubusercontent.com/logoanim/lottie/main/rings-1.json",
                        height_px=170,
                        caption="Analyzing architecture… mapping modules & risks",
                    ),
                    unsafe_allow_html=True,
                )
                with st.spinner("Analyzing architecture..."):
                    prompt = "Analyze this code. Provide two clear sections: 1. MODULE ANALYSIS (Architecture overview) and 2. RISK MAP (Potential vulnerabilities/risks). Separate them strictly with the token '<<<SEP>>>'.\n" + st.session_state['full_code_context'][:25000]
                    res, m = generate_content_with_fallback(prompt, api_key)
                    if m == "Error": st.error(res)
                    else:
                        mod_text = res
                        risk_text = ""
                        if "<<<SEP>>>" in res:
                            p1, p2 = res.split("<<<SEP>>>", 1)
                            mod_text, risk_text = p1.strip(), p2.strip()
                        else:
                            # Fallback split if AI forgot the token
                            import re
                            split_match = re.split(r'(?:\n##\s*(?:(?:2\.)?\s*RISK MAP).*|\n#\s*(?:(?:2\.)?\s*RISK MAP).*)', res, 1, flags=re.IGNORECASE)
                            if len(split_match) == 2:
                                mod_text = split_match[0].strip()
                                risk_text = "## RISK MAP\n" + split_match[1].strip()
                                
                        st.session_state['analysis_module'] = mod_text
                        st.session_state['analysis_risk'] = risk_text
                lottie.empty()

        if st.session_state["analysis_module"]:
            with st.container(border=True):
                st.markdown("### Module Analysis")
                st.markdown(
                    _safe_markdown_to_html(st.session_state["analysis_module"]),
                    unsafe_allow_html=True,
                )
        
    with t3:
        if st.session_state["analysis_risk"]:
            with st.container(border=True):
                st.markdown("### Risk Map")
                st.markdown(
                    _safe_markdown_to_html(st.session_state["analysis_risk"]),
                    unsafe_allow_html=True,
                )
        else:
            st.info("Run module analysis first.")
        
    with t4:
        # Subtle Styling for Delete Buttons
        st.markdown("""
            <style>
            .stButton>button[key^="chat_del_"] {
                color: #cccccc !important;
                background-color: transparent !important;
                border: none !important;
                padding: 0px !important;
                width: 20px !important;
                height: 20px !important;
                font-size: 12px !important;
            }
            .stButton>button[key^="chat_del_"]:hover {
                color: #ff4b4b !important;
                background-color: #ffeeee !important;
            }
            </style>
        """, unsafe_allow_html=True)

        col_c1, col_c2 = st.columns([4, 2])
        if col_c2.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state['messages'] = []
            st.rerun()
            
        # Fixed height message container
        chat_container = st.container()
        with chat_container:
            for idx, m in enumerate(st.session_state['messages']):
                c_chat1, c_chat2 = st.columns([0.94, 0.06])
                with c_chat1:
                    role = m.get("role", "assistant")
                    content_html = _safe_markdown_to_html(m.get("content", ""))
                    st.markdown(
                        f"""
                        <div class="chat-row {role}">
                          <div class="chat-icon {role}">{_html.escape(USER_ICON if role == 'user' else BOT_ICON)}</div>
                          <div class="bubble {role}">
                            {content_html}
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with c_chat2:
                    # The key handles the styling via CSS selector above
                    if st.button("✕", key=f"chat_del_{idx}"):
                        st.session_state['messages'].pop(idx)
                        st.rerun()

        if q := st.chat_input("Ask about the code..."):
            st.session_state['messages'].append({"role": "user", "content": q})
            st.rerun()
            
        if st.session_state['messages'] and st.session_state['messages'][-1]['role'] == 'user':
            thinking = st.empty()
            thinking.markdown(
                _lottie_html(
                    "https://raw.githubusercontent.com/logoanim/lottie/main/Loadeder_01.json",
                    height_px=120,
                    caption="Thinking…",
                ),
                unsafe_allow_html=True,
            )
            with st.spinner("Thinking..."):
                try:
                    if not api_key:
                        st.error("API Key missing")
                    else:
                        ctx = st.session_state['full_code_context'][:20000] + "\nQ: " + st.session_state['messages'][-1]['content']
                        ans, m = generate_content_with_fallback(ctx, api_key)
                        if m == "Error":
                            st.error(ans)
                        else:
                            st.session_state['messages'].append({"role": "assistant", "content": ans})
                            st.rerun()
                finally:
                    thinking.empty()

if session: session.close()


# Close session at end of script run if using scoped session management in a real app, 
# but Streamlit runs top-down. session.close() is handled by context managers or left to pool in simple scripts.
# For this simple script, we leave it to SQLAlchemy connection pool to handle.
