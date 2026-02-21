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
        # Construct connection string from secrets
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
        else:
            return None

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
    try:
        user = session.query(User).filter_by(username=username, password_hash=hash_password(password)).first()
        return user
    except:
        return None

# --- Project Functions ---
def save_project(session, user_id, name, source_type, repo_url, code_context, analysis_module, analysis_risk):
    try:
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
    try:
        return session.query(Project).filter_by(user_id=user_id).order_by(Project.created_at.desc()).all()
    except:
        return []

# --- AI Helper Functions ---
def generate_content_with_fallback(prompt, api_key, generation_config=None):
    try:
        genai.configure(api_key=api_key)
        try:
            models = genai.list_models()
            available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        except:
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
        
        # If all failed, return error message and "Error" model name to avoid unpacking issues
        return f"All models failed. {'; '.join(errors)}", "Error"
    except Exception as e:
        return f"Unexpected Error: {str(e)}", "Error"

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
        
        if not tree_data: return None, "Repo not found, private, or branch issue."
        
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
    except Exception as e:
        return None, str(e)


# --- Session State ---
if 'user_info' not in st.session_state: st.session_state['user_info'] = None
if 'analysis_module' not in st.session_state: st.session_state['analysis_module'] = ""
if 'analysis_risk' not in st.session_state: st.session_state['analysis_risk'] = ""
if 'full_code_context' not in st.session_state: st.session_state['full_code_context'] = ""
if 'uploaded_files_data' not in st.session_state: st.session_state['uploaded_files_data'] = []
if 'messages' not in st.session_state: st.session_state['messages'] = []
if 'project_source' not in st.session_state: st.session_state['project_source'] = None
if 'current_repo_url' not in st.session_state: st.session_state['current_repo_url'] = ""
if 'show_import_screen' not in st.session_state: st.session_state['show_import_screen'] = False

# --- Database ---
session = get_db_session()

# --- Sidebar ---
with st.sidebar:
    st.title("🔐 Account")
    if st.session_state['user_info']:
        st.success(f"Hi, {st.session_state['user_info']['username']}")
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
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
                with st.spinner("Testing connection..."):
                    try:
                        genai.configure(api_key=api_key)
                        models = genai.list_models()
                        model_names = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
                        if model_names:
                            st.success(f"✅ Connection Successful! Found {len(model_names)} models.")
                        else:
                            st.warning("⚠️ Connected, but no text models found.")
                    except Exception as e:
                        st.error(f"❌ Connection Failed: {str(e)}")

    if st.session_state['user_info'] and (st.session_state['uploaded_files_data'] or st.session_state['full_code_context']):
        st.divider()
        if st.button("🏠 Project Selection", use_container_width=True):
            st.session_state['uploaded_files_data'] = []
            st.session_state['full_code_context'] = ""
            st.session_state['analysis_module'] = ""
            st.session_state['analysis_risk'] = ""
            st.session_state['show_import_screen'] = False
            st.rerun()

st.markdown("# 🤖 Code Repository Onboarding")

# Not logged in
if not st.session_state['user_info']:
    st.info("Welcome! Please login to start analyzing code repositories.")
    st.image("https://img.icons8.com/clouds/200/code.png")

# Logged in, show landing page or import screen
elif not st.session_state['uploaded_files_data'] and not st.session_state['show_import_screen']:
    st.header("Projects History")
    
    col_new, _ = st.columns([1, 3])
    with col_new:
        if st.button("➕ Analyze New Project", type="primary", use_container_width=True):
            st.session_state['show_import_screen'] = True
            st.rerun()
            
    st.divider()
    if session:
        projects = get_user_projects(session, st.session_state['user_info']['id'])
        if projects:
            for p in projects:
                c1, c2, c3 = st.columns([4, 2, 1])
                c1.write(f"**{p.name}**  \n`Source: {p.repo_url or 'Local'}`")
                c2.caption(f"📅 {p.created_at.strftime('%Y-%m-%d %H:%M')}")
                if c3.button("📂 Load", key=f"load_{p.id}", use_container_width=True):
                    st.session_state['full_code_context'] = p.code_context
                    st.session_state['analysis_module'] = p.analysis_module
                    st.session_state['analysis_risk'] = p.analysis_risk
                    st.session_state['uploaded_files_data'] = [{"name": "Loaded Project", "content": "Loaded from History"}]
                    st.session_state['project_source'] = p.source_type
                    st.session_state['current_repo_url'] = p.repo_url
                    st.rerun()
        else:
            st.info("No saved projects found. Click 'Analyze New Project' to get started!")

# Import Screen
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
                    st.rerun()
                else: st.error("No valid text files.")

# Analysis view
else:
    t1, t2, t3, t4 = st.tabs(["📊 Structure", "🔍 Module Analysis", "🗺️ Risk Map", "💬 Ask Your Code"])
    
    with t1:
        st.metric("Total Files", len(st.session_state['uploaded_files_data']))
        for f in st.session_state['uploaded_files_data']:
            with st.expander(f.get('name', 'Unknown')):
                if 'content' in f: st.code(f['content'][:300], language='python')
                else: st.write("Content loaded from history.")
    
    with t2:
        if st.button("🚀 Start AI Analysis", type="primary"):
            if not api_key: st.error("Please provide an API Key in settings.")
            else:
                with st.spinner("Analyzing architecture..."):
                    prompt = "Analyze this code. Split into MODULE ANALYSIS and RISK MAP sections using '<<<SEP>>>'.\n" + st.session_state['full_code_context'][:25000]
                    res, m = generate_content_with_fallback(prompt, api_key)
                    if m == "Error": st.error(res)
                    else:
                        if "<<<SEP>>>" in res:
                            p1, p2 = res.split("<<<SEP>>>", 1)
                            st.session_state['analysis_module'], st.session_state['analysis_risk'] = p1, p2
                        else: st.session_state['analysis_module'] = res
        
        if st.session_state['analysis_module']:
            st.markdown(st.session_state['analysis_module'])
            st.divider()
            save_name = st.text_input("Project Name to Save", value=f"Analysis {datetime.now().strftime('%H:%M')}")
            if st.button("💾 Save Project", use_container_width=True):
                if session:
                    ok, msg = save_project(session, st.session_state['user_info']['id'], save_name, st.session_state['project_source'], 
                                          st.session_state['current_repo_url'], st.session_state['full_code_context'], 
                                          st.session_state['analysis_module'], st.session_state['analysis_risk'])
                    if ok: st.success(msg)
                    else: st.error(msg)
                else: st.error("DB Connection Failed")

    with t3:
        if st.session_state['analysis_risk']: st.markdown(st.session_state['analysis_risk'])
        else: st.info("Run module analysis first.")
            
    with t4:
        for m in st.session_state['messages']:
            with st.chat_message(m['role'], avatar="�" if m['role']=='user' else "🤖"):
                st.write(m['content'])
        
        if q := st.chat_input("Ask about the code..."):
            st.session_state['messages'].append({"role": "user", "content": q})
            st.rerun()
            
        if st.session_state['messages'] and st.session_state['messages'][-1]['role'] == 'user':
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Thinking..."):
                    if not api_key: st.error("API Key missing")
                    else:
                        ctx = st.session_state['full_code_context'][:20000] + "\nQ: " + st.session_state['messages'][-1]['content']
                        ans, m = generate_content_with_fallback(ctx, api_key)
                        if m == "Error": st.error(ans)
                        else:
                            st.write(ans)
                            st.session_state['messages'].append({"role": "assistant", "content": ans})


# Close session at end of script run if using scoped session management in a real app, 
# but Streamlit runs top-down. session.close() is handled by context managers or left to pool in simple scripts.
# For this simple script, we leave it to SQLAlchemy connection pool to handle.
