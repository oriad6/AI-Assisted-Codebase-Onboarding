import streamlit as st
import google.generativeai as genai
from pathlib import Path
import requests
import hashlib
import json
import socket
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

# --- Configuration & Setup ---
st.set_page_config(
    page_title="Code Repository Onboarding",
    page_icon="🤖",
    layout="wide"
)

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

# Database Connection
def get_db_session():
    try:
        host = None
        port = None
        user = None
        password = None
        dbname = None

        if "postgres" in st.secrets:
            secrets = st.secrets["postgres"]
            user = secrets["user"]
            password = secrets["password"]
            host = secrets["host"]
            port = secrets["port"]
            dbname = secrets["dbname"]
        elif "database" in st.secrets and "url" in st.secrets["database"]:
             # Basic parsing if URL provided (fallback)
             st.error("Please use the [postgres] format in secrets for best compatibility.")
             return None
        else:
            st.error("Missing database configuration in secrets.toml")
            return None

        # Workaround for IPv6 issues on local Windows with Supabase
        # Force IPv4 resolution
        try:
            # Force IPv4 resolution
            addr_info = socket.getaddrinfo(host, port, family=socket.AF_INET, proto=socket.IPPROTO_TCP)
            if addr_info:
                host_ip = addr_info[0][4][0]
                # Use hostaddr to force connection to IP, but keep host for SSL verification
                db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}?hostaddr={host_ip}&sslmode=require"
            else:
                 # Fallback if no IPv4 found
                 db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"
        except Exception:
            # Fallback if resolution fails completely
            db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"

        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None

# --- Auth Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

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

def login_user(session, username, password):
    user = session.query(User).filter_by(username=username, password_hash=hash_password(password)).first()
    return user

# --- Project Functions ---
def save_project(session, user_id, name, source_type, repo_url, code_context, analysis_module, analysis_risk):
    try:
        # Use simple 'N/A' or empty string if context/analysis is missing to allow saving partial states if desired, 
        # but user asked for "After an analysis... save". We will save whatever is in state.
        new_project = Project(
            user_id=user_id,
            name=name,
            source_type=source_type,
            repo_url=repo_url,
            code_context=code_context,
            analysis_module=analysis_module,
            analysis_risk=analysis_risk
        )
        session.add(new_project)
        session.commit()
        return True, "Project saved successfully!"
    except Exception as e:
        session.rollback()
        return False, str(e)

def get_user_projects(session, user_id):
    return session.query(Project).filter_by(user_id=user_id).order_by(Project.created_at.desc()).all()

# --- Helper Functions (Existing) ---
def generate_content_with_fallback(prompt, api_key, generation_config=None):
    # ... (Keep existing robust logic)
    try:
        genai.configure(api_key=api_key)
        try:
            models = genai.list_models()
            available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        except:
             # Fallback if list_models fails (e.g. key permissions)
             available_models = ["gemini-1.5-pro", "gemini-1.5-flash"]

        priority_order = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]
        sorted_models = sorted(available_models, key=lambda m: next((i for i, p in enumerate(priority_order) if p in m), len(priority_order)))
        
        errors = []
        for model_name in sorted_models:
            if "embedding" in model_name: continue
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config=generation_config)
                return response.text, model_name
            except Exception as e:
                errors.append(f"{model_name}: {str(e)}")
        raise Exception(f"All models failed. {errors}")
    except Exception as e:
        raise e

def fetch_github_repo(repo_url):
    # ... (Keep existing fetch logic)
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
        
        if not tree_data: return None, "Repo not found or private."
        
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
                    if count >= 60: break # Safety limit
        
        if not files_data: return None, "No code files found."
        return files_data, None
    except Exception as e:
        return None, str(e)


# --- Initialization ---
if 'user_info' not in st.session_state: st.session_state['user_info'] = None # {id, username}
if 'analysis_module' not in st.session_state: st.session_state['analysis_module'] = ""
if 'analysis_risk' not in st.session_state: st.session_state['analysis_risk'] = ""
if 'full_code_context' not in st.session_state: st.session_state['full_code_context'] = ""
if 'uploaded_files_data' not in st.session_state: st.session_state['uploaded_files_data'] = []
if 'messages' not in st.session_state: st.session_state['messages'] = []
if 'project_source' not in st.session_state: st.session_state['project_source'] = None
if 'current_repo_url' not in st.session_state: st.session_state['current_repo_url'] = ""


# --- Main App ---
session = get_db_session()

# Sidebar: Auth & Settings
with st.sidebar:
    st.title("🔐 Account")
    
    if st.session_state['user_info']:
        st.success(f"Hi, {st.session_state['user_info']['username']}")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
    else:
        tab_login, tab_reg = st.tabs(["Login", "Register"])
        with tab_login:
            l_user = st.text_input("Username", key="l_u")
            l_pass = st.text_input("Password", type="password", key="l_p")
            if st.button("Login", type="primary"):
                if session:
                    user = login_user(session, l_user, l_pass)
                    if user:
                        st.session_state['user_info'] = {'id': user.id, 'username': user.username}
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                else:
                    st.error("DB Connection Failed")
        
        with tab_reg:
            r_user = st.text_input("Username", key="r_u")
            r_pass = st.text_input("Password", type="password", key="r_p")
            if st.button("Register"):
                if session:
                    ok, msg = register_user(session, r_user, r_pass)
                    if ok: st.success(msg)
                    else: st.error(msg)
                else:
                    st.error("DB Connection Failed")

    st.divider()
    with st.expander("⚙️ API Settings", expanded=True):
        api_key = st.text_input("Google API Key", type="password")
        
    st.divider()
    with st.expander("☁️ Metadata"):
        st.caption(f"Source: {st.session_state['project_source'] or 'None'}")
        st.caption(f"Files: {len(st.session_state['uploaded_files_data'])}")

st.title("🤖 Cloud-Native Code Onboarding")

# Only allow usage if logged in (Optional, but acts as a gatekeeper for DB features)
if not st.session_state['user_info']:
    st.warning("Please Login or Register in the sidebar to access the full functionality and save your projects.")

# Input Section
if not st.session_state['uploaded_files_data']:
    st.info("Start by importing your codebase:")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("GitHub Repo")
        repo_url = st.text_input("Repository URL")
        if st.button("Fetch from GitHub"):
            with st.spinner("Fetching..."):
                files, err = fetch_github_repo(repo_url)
                if files:
                    st.session_state['uploaded_files_data'] = files
                    st.session_state['full_code_context'] = "".join([f"\n--- {f['name']} ---\n{f['content']}" for f in files])
                    st.session_state['project_source'] = "github"
                    st.session_state['current_repo_url'] = repo_url
                    st.rerun()
                else:
                    st.error(err)
                    
    with col2:
        st.subheader("File Upload")
        uploaded = st.file_uploader("Upload Files", accept_multiple_files=True)
        if uploaded:
            if st.button("Process Uploads"):
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
                    st.rerun()
                else:
                    st.error("No valid text files.")

else:
    # Main Dashboard
    btn_col1, btn_col2 = st.columns([1,5])
    with btn_col1:
        if st.button("🔙 New Project"):
            st.session_state['uploaded_files_data'] = []
            st.session_state['full_code_context'] = ""
            st.session_state['analysis_module'] = ""
            st.session_state['analysis_risk'] = ""
            st.rerun()
            
    # Tabs
    t1, t2, t3, t4, t5 = st.tabs(["📊 Structure", "🔍 Module Analysis", "🗺️ Risk Map", "💬 Chat", "📜 My History"])
    
    with t1:
        st.metric("Total Files", len(st.session_state['uploaded_files_data']))
        for f in st.session_state['uploaded_files_data']:
            with st.expander(f.get('name', 'Unknown')):
                st.code(f.get('content', '')[:300], language='python')
                
    with t2:
        if st.button("🚀 Run AI Analysis"):
            if not api_key:
                st.error("API Key missing in sidebar.")
            else:
                with st.spinner("Analyzing..."):
                    try:
                        prompt = "Analyze this code. Split into MODULE ANALYSIS and RISK MAP sections using '<<<SEP>>>'."
                        prompt += "\n" + st.session_state['full_code_context'][:25000]
                        res, _ = generate_content_with_fallback(prompt, api_key)
                        if "<<<SEP>>>" in res:
                            p1, p2 = res.split("<<<SEP>>>")
                            st.session_state['analysis_module'] = p1
                            st.session_state['analysis_risk'] = p2
                        else:
                            st.session_state['analysis_module'] = res
                    except Exception as e:
                        st.error(str(e))
        
        if st.session_state['analysis_module']:
            st.markdown(st.session_state['analysis_module'])
            
            # Save Project Button (Only if analyzed)
            if st.session_state['user_info']:
                st.divider()
                save_name = st.text_input("Project Name for Saving", value=f"Analysis {datetime.now().strftime('%H:%M')}")
                if st.button("💾 Save to History"):
                    if session:
                        ok, msg = save_project(
                            session, 
                            st.session_state['user_info']['id'],
                            save_name,
                            st.session_state['project_source'],
                            st.session_state['current_repo_url'],
                            st.session_state['full_code_context'],
                            st.session_state['analysis_module'],
                            st.session_state['analysis_risk']
                        )
                        if ok: st.success(msg)
                        else: st.error(msg)
            else:
                st.info("Login to save this analysis.")

    with t3:
        if st.session_state['analysis_risk']:
            st.markdown(st.session_state['analysis_risk'])
        else:
            st.info("Run module analysis first.")
            
    with t4:
        # Chat interface
        for m in st.session_state['messages']:
            with st.chat_message(m['role'], avatar="🧑💻" if m['role']=='user' else "🤖"):
                st.write(m['content'])
        
        if q := st.chat_input("Ask about the code"):
            st.session_state['messages'].append({"role": "user", "content": q})
            st.rerun()
            
        if st.session_state['messages'] and st.session_state['messages'][-1]['role'] == 'user':
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Thinking..."):
                    if not api_key:
                        st.error("API Key missing")
                    else:
                        ctx = st.session_state['full_code_context'][:20000] + "\nQ: " + st.session_state['messages'][-1]['content']
                        try:
                            ans, _ = generate_content_with_fallback(ctx, api_key)
                            st.write(ans)
                            st.session_state['messages'].append({"role": "assistant", "content": ans})
                        except Exception as e:
                            st.error(str(e))
                            
    with t5:
        st.header("📜 My Saved Projects")
        if not st.session_state['user_info']:
            st.warning("Login to view history.")
        elif session:
            projects = get_user_projects(session, st.session_state['user_info']['id'])
            if projects:
                for p in projects:
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.write(f"**{p.name}**")
                    c2.caption(f"{p.created_at.strftime('%Y-%m-%d %H:%M')}")
                    if c3.button("📂 Load", key=f"load_{p.id}"):
                        st.session_state['full_code_context'] = p.code_context
                        st.session_state['analysis_module'] = p.analysis_module
                        st.session_state['analysis_risk'] = p.analysis_risk
                        st.session_state['uploaded_files_data'] = [{"name": "Loaded Project", "content": "Loaded from DB", "size": 0}]
                        st.session_state['project_source'] = p.source_type
                        st.session_state['current_repo_url'] = p.repo_url
                        st.success(f"Loaded {p.name}")
                        st.rerun()
            else:
                st.info("No saved projects.")

# Close session at end of script run if using scoped session management in a real app, 
# but Streamlit runs top-down. session.close() is handled by context managers or left to pool in simple scripts.
# For this simple script, we leave it to SQLAlchemy connection pool to handle.
