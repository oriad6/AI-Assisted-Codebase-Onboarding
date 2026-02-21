import streamlit as st
import google.generativeai as genai
from pathlib import Path
import requests
import hashlib
import json
import socket
from urllib.parse import quote_plus
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

# --- Configuration & Setup ---
st.set_page_config(
    page_title="Code Repository Onboarding",
    page_icon="🤖",
    layout="wide"
)

# --- Custom Icons & Styles ---
BOT_ICON = "🤖" # Using emoji with styling for reliability
USER_ICON = "👤"

def render_bot_icon(size=40):
    return f'<div style="display:inline-block; background-color:#f0f7ff; border-radius:50%; padding:8px; width:{size}px; height:{size}px; text-align:center; line-height:{size-16}px; font-size:{size-16}px; border: 1px solid #d1e3f8; box-shadow: 1px 1px 3px rgba(0,0,0,0.05);">{BOT_ICON}</div>'

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
            st.rerun()

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
                for p in projects:
                    c1, c2, c3 = st.columns([4, 2, 1])
                    display_name = p.name
                    if "github.com/" in str(p.repo_url):
                        display_name = p.repo_url.split("/")[-1] or p.name
                    c1.write(f"**{display_name}**")
                    c2.caption(f"📅 {p.created_at.strftime('%Y-%m-%d %H:%M')}")
                    if c3.button("📂 Load", key=f"load_{p.id}", use_container_width=True):
                        st.session_state['full_code_context'] = p.code_context
                        st.session_state['analysis_module'] = p.analysis_module
                        st.session_state['analysis_risk'] = p.analysis_risk
                        st.session_state['uploaded_files_data'] = [{"name": display_name, "content": "Project Data Loaded"}]
                        st.session_state['project_source'] = p.source_type
                        st.session_state['current_repo_url'] = p.repo_url
                        st.session_state['is_loaded_from_db'] = True
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
                    st.rerun()
                else: st.error("No valid text files.")

else:
    t1, t2, t3, t4 = st.tabs(["📊 Structure", "🔍 Module Analysis", "🗺️ Risk Map", "💬 Ask Your Code"])
    with t1:
        st.metric("Total Files", len(st.session_state['uploaded_files_data']))
        for f in st.session_state['uploaded_files_data']:
            # For history-loaded projects, we only show metadata if context is empty
            with st.expander(f.get('name', 'Unknown')):
                if not st.session_state['is_loaded_from_db'] and 'content' in f: 
                    st.code(f['content'][:500], language='python')
                else:
                    st.write("Source code context available for AI analysis. Reprocess to view full files here.")
                    
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
                with st.spinner("Analyzing architecture..."):
                    prompt = "Analyze this code. Provide two clear sections: 1. MODULE ANALYSIS (Architecture overview) and 2. RISK MAP (Potential vulnerabilities/risks). Separate them strictly with the token '<<<SEP>>>'.\n" + st.session_state['full_code_context'][:25000]
                    res, m = generate_content_with_fallback(prompt, api_key)
                    if m == "Error": st.error(res)
                    else:
                        if "<<<SEP>>>" in res:
                            p1, p2 = res.split("<<<SEP>>>", 1)
                            st.session_state['analysis_module'], st.session_state['analysis_risk'] = p1.strip(), p2.strip()
                        else: st.session_state['analysis_module'] = res
        if st.session_state['analysis_module']: st.markdown(st.session_state['analysis_module'])
        
    with t3:
        if st.session_state['analysis_risk']: st.markdown(st.session_state['analysis_risk'])
        else: st.info("Run module analysis first.")
        
    with t4:
        col_c1, col_c2 = st.columns([5, 1])
        if col_c2.button("🗑️ Clear", use_container_width=True):
            st.session_state['messages'] = []
            st.rerun()
            
        # Fixed height message container
        chat_container = st.container()
        with chat_container:
            for idx, m in enumerate(st.session_state['messages']):
                c_chat1, c_chat2 = st.columns([0.93, 0.07])
                with c_chat1:
                    with st.chat_message(m['role'], avatar=USER_ICON if m['role']=='user' else BOT_ICON):
                        st.write(m['content'])
                with c_chat2:
                    if st.button("❌", key=f"chat_del_{idx}", help="Delete"):
                        st.session_state['messages'].pop(idx)
                        st.rerun()

        if q := st.chat_input("Ask about the code..."):
            st.session_state['messages'].append({"role": "user", "content": q})
            st.rerun()
            
        if st.session_state['messages'] and st.session_state['messages'][-1]['role'] == 'user':
            with st.chat_message("assistant", avatar=BOT_ICON):
                with st.spinner("Thinking..."):
                    if not api_key: st.error("API Key missing")
                    else:
                        ctx = st.session_state['full_code_context'][:20000] + "\nQ: " + st.session_state['messages'][-1]['content']
                        ans, m = generate_content_with_fallback(ctx, api_key)
                        if m == "Error": st.error(ans)
                        else:
                            st.write(ans)
                            st.session_state['messages'].append({"role": "assistant", "content": ans})
                            st.rerun()

if session: session.close()


# Close session at end of script run if using scoped session management in a real app, 
# but Streamlit runs top-down. session.close() is handled by context managers or left to pool in simple scripts.
# For this simple script, we leave it to SQLAlchemy connection pool to handle.
