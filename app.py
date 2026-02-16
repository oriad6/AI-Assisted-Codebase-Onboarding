import streamlit as st
import google.generativeai as genai
from pathlib import Path
import requests

# Page configuration
st.set_page_config(
    page_title="Code Repository Onboarding",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if 'analysis_result' not in st.session_state:
    st.session_state['analysis_result'] = None

if 'available_models' not in st.session_state:
    st.session_state['available_models'] = []

if 'messages' not in st.session_state:
    st.session_state['messages'] = []

if 'full_code_context' not in st.session_state:
    st.session_state['full_code_context'] = ""

# Title and introduction
st.title("🤖 Code Repository Onboarding Tool")
st.info("💡 **Get Started:** Upload your code files and let AI analyze the structure, modules, and risks of your project.")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Advanced Configuration Expander
    with st.expander("⚙️ Advanced Configuration", expanded=True):
        # API Key input
        api_key = st.text_input(
            "Google AI API Key",
            type="password",
            help="Enter your API key from Google AI Studio (https://aistudio.google.com/app/apikey)"
        )

        # API Key status and test
        if api_key:
            st.success("🔑 API Key provided")
            
            # Test API Connection
            if st.button("🔍 Test API Connection"):
                try:
                    genai.configure(api_key=api_key)
                    models = genai.list_models()
                    available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
                    st.session_state['available_models'] = available_models
                    
                    if available_models:
                        st.success(f"✅ Connection Successful! Found {len(available_models)} models.")
                    else:
                        st.warning("⚠️ Connected, but no text generation models found.")
                except Exception as e:
                    st.error(f"❌ Connection Failed: {str(e)}")
        else:
            st.warning("⚠️ Please enter API Key")
    
    # Model selection handled automatically with fallback
    # PRIORITY_MODELS = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.0-pro"]
    
    st.divider()
    
    # Helper function for model fallback
    def generate_content_with_fallback(prompt, api_key, generation_config=None):
        genai.configure(api_key=api_key)
        
        # Get available models dynamically
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except Exception as e:
            raise Exception(f"Failed to list models: {str(e)}")
            
        if not available_models:
             raise Exception("No models found that support generateContent.")

        # Define priority order (partial matching)
        priority_order = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]
        
        # Sort available models based on priority
        def get_priority(model_name):
            for i, p in enumerate(priority_order):
                if p in model_name:
                    return i
            return len(priority_order) # Lowest priority if not in list

        sorted_models = sorted(available_models, key=lambda m: get_priority(m))
        
        errors = []
        for model_name in sorted_models:
            # Skip if it's an embedding model or similar (though filter above handles most)
            if "embedding" in model_name:
                continue
                
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config=generation_config)
                return response.text, model_name
            except Exception as e:
                errors.append(f"{model_name}: {str(e)}")
                continue
        
        # If we get here, all models failed
        error_details = "\n".join(errors)
        raise Exception(f"All models failed to generate content.\nDetails:\n{error_details}")

    # Helper function for GitHub fetching
    def fetch_github_repo(repo_url):
        # Extract owner and repo
        try:
            parts = repo_url.rstrip("/").split("/")
            owner, repo = parts[-2], parts[-1]
        except:
            return None, "Invalid GitHub URL format."
        
        # Get repository tree
        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
        try:
            response = requests.get(api_url)
            if response.status_code == 404:
                # Try master branch if main fails
                api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
                response = requests.get(api_url)
            
            if response.status_code != 200:
                return None, f"Failed to fetch repo: {response.json().get('message', 'Unknown error')}"
            
            tree = response.json().get('tree', [])
            files_data = []
            
            allowed_extensions = {'.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go', '.rs', '.php', '.rb', '.kt', '.swift', '.dart', '.html', '.css', '.json', '.yaml', '.yml', '.xml', '.sh', '.bat', '.sql'}
            
            for item in tree:
                if item['type'] == 'blob':
                    file_path = item['path']
                    ext = Path(file_path).suffix
                    if ext in allowed_extensions:
                        # Fetch file content
                        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{'main' if 'main' in api_url else 'master'}/{file_path}"
                        file_response = requests.get(raw_url)
                        if file_response.status_code == 200:
                            files_data.append({
                                "name": file_path,
                                "content": file_response.text,
                                "size": len(file_response.content)
                            })
                            
            if not files_data:
                return None, "No supported code files found in repository."
                
            return files_data, None
            
        except Exception as e:
            return None, str(e)

    # How to use section
    st.markdown("""
    ### 📋 How to Use
    
    **Step 1:** Upload Files
    - Upload your code files (Python, JS, Java, C++, Go, etc.)
    - Multiple files supported
    
    **Step 2:** Start Analysis
    - Go to 'Module Analysis' tab
    - Click 'Start AI Analysis'
    - Wait for comprehensive report
    
    **Step 3:** Chat with Code
    - Go to 'Ask Your Code' tab
    - Ask questions about your codebase
    - Get AI-powered answers
    """)
    
    st.divider()
    
    # API Key status


# Main Input Area
st.header("📂 Select Input Method")
input_method = st.radio("Choose how to provide code:", ["Upload Files", "GitHub Repository"], horizontal=True, label_visibility="collapsed")

if 'uploaded_files_data' not in st.session_state:
    st.session_state['uploaded_files_data'] = []

with st.container():
    if input_method == "Upload Files":
        uploaded_files = st.file_uploader(
            "Select code files to upload",
            accept_multiple_files=True,
            help="You can upload multiple files at once. The system will attempt to analyze any text-based code file."
        )
        
        if uploaded_files:
            # Process uploaded files into standard format
            files_data = []
            for file in uploaded_files:
                try:
                    content = file.getvalue().decode('utf-8')
                    files_data.append({
                        "name": file.name,
                        "content": content,
                        "size": len(file.getvalue())
                    })
                except:
                    st.warning(f"Skipped binary or unsupported file: {file.name}")
            
            st.session_state['uploaded_files_data'] = files_data
            
             # Build context string
            st.session_state['full_code_context'] = ""
            for file in files_data:
                st.session_state['full_code_context'] += f"\n--- FILE: {file['name']} ---\n{file['content']}\n"

    else:  # GitHub Repository
        col_repo, col_btn = st.columns([4, 1])
        with col_repo:
            repo_url = st.text_input("Enter GitHub Repository URL", placeholder="https://github.com/owner/repo")
        with col_btn:
            fetch_clicked = st.button("Fetch Repo", type="primary", use_container_width=True)
            
        if fetch_clicked and repo_url:
            with st.spinner("Fetching repository..."):
                files_data, error = fetch_github_repo(repo_url)
                if error:
                    st.error(f"❌ {error}")
                else:
                    st.session_state['uploaded_files_data'] = files_data
                    st.success(f"✅ Successfully fetched {len(files_data)} files!")
                    
                    # Build context string
                    st.session_state['full_code_context'] = ""
                    for file in files_data:
                        st.session_state['full_code_context'] += f"\n--- FILE: {file['name']} ---\n{file['content']}\n"

# Only show tabs if we have data
if st.session_state['uploaded_files_data']:
    st.divider()
    
    # Analysis Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🔍 Module Analysis", "🗺️ Risk Map", "💬 Ask Your Code"])
    
    # Tab 1: Dashboard
    with tab1:
        st.header("Project Dashboard")
        
        total_files = len(st.session_state['uploaded_files_data'])
        total_size_kb = sum(f['size'] for f in st.session_state['uploaded_files_data']) / 1024
        
        # Determine primary language (simple heuristic)
        extensions = [Path(f['name']).suffix for f in st.session_state['uploaded_files_data']]
        if extensions:
            primary_lang = max(set(extensions), key=extensions.count).replace(".", "").upper()
            if primary_lang == "": primary_lang = "Mixed"
        else:
            primary_lang = "Unknown"

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Files Scanned", total_files)
        m2.metric("Total Codebase Size", f"{total_size_kb:.1f} KB")
        m3.metric("Primary Language", primary_lang)
        
        st.divider()
        st.markdown("### 📄 Files Found:")
        
        # Display files list in a scrollable container or expander
        for file in st.session_state['uploaded_files_data']:
             with st.expander(f"{file['name']} ({file['size']/1024:.1f} KB)"):
                st.code(file['content'][:500] + ("..." if len(file['content']) > 500 else ""), language=Path(file['name']).suffix[1:])
    
    # Tab 2: Module Analysis
    with tab2:
        st.header("Module Analysis")
        
        if not api_key:
            st.warning("⚠️ Please enter your API Key in the sidebar to enable AI analysis")
        else:
            st.info("🤖 Click the button below to generate a comprehensive code analysis report.")
            
            if st.button("🚀 Start AI Analysis", type="primary", use_container_width=True):
                if st.session_state['full_code_context']:
                    with st.spinner("🔄 Analyzing your codebase... This may take a moment."):
                        try:
                            # System prompt for analysis
                            analysis_prompt = """You are a Senior Software Engineer with 15+ years of experience in software architecture.

Your task is to analyze the provided codebase.

The report MUST be separated into two distinct parts using a specific separator.

# MODULE ANALYSIS
Start this section immediately with the content.

1. **Role Summary**: A brief overview of what this codebase does.

2. **Dependency Table**: List all external libraries.

3. **Onboarding Recommendations**: Provide actionable advice.

<<<RISK_ANALYSIS_START>>>
# RISK MAP

**Maintenance & Risk Points**: Identify potential issues including:
   - Code quality concerns
   - Security vulnerabilities
   - Performance bottlenecks
   - Technical debt
   - Missing error handling
   - Hard-coded values that should be configurable

Format your response in clear markdown with headers, bullet points, and tables where appropriate.
""" + st.session_state['full_code_context']

                            # Make API call with auto-fallback
                            generation_config = {
                                "temperature": 0.7,
                                "top_p": 0.95,
                                "top_k": 40,
                                "max_output_tokens": 8192,
                            }
                            
                            analysis_text, used_model = generate_content_with_fallback(
                                analysis_prompt, 
                                api_key, 
                                generation_config=generation_config
                            )
                            
                            # Extract analysis result
                            full_response = analysis_text
                            
                            # Split response into module and risk analysis
                            if "<<<RISK_ANALYSIS_START>>>" in full_response:
                                parts = full_response.split("<<<RISK_ANALYSIS_START>>>")
                                module_analysis = parts[0].replace("PART 1: MODULE ANALYSIS", "").replace("PART 1", "").strip()
                                risk_analysis = parts[1].replace("PART 2: RISK ANALYSIS", "").replace("PART 2", "").strip()
                            else:
                                module_analysis = full_response
                                risk_analysis = "Could not parse risk analysis separately. Please check the main report."
                            
                            st.session_state['analysis_result'] = full_response # Keep full for download
                            st.session_state['module_analysis'] = module_analysis
                            st.session_state['risk_analysis'] = risk_analysis
                            
                            st.success(f"✅ Analysis complete using {used_model}!")
                            
                        except Exception as e:
                            st.error(f"❌ Error during analysis: {str(e)}")
                            st.info("""
                            💡 **Troubleshooting Tips:**
                            - Verify your API key is correct
                            - Click 'Test API Connection' in the sidebar
                            - Get a free API key at: https://aistudio.google.com/app/apikey
                            """)
                else:
                    st.error("❌ No code context found. Please upload files first.")
            
            # Display module analysis result if available
            if st.session_state.get('module_analysis'):
                st.divider()
                st.markdown("### 📝 Analysis Report")
                st.markdown(st.session_state['module_analysis'])
                
                # Download button for the full report
                st.download_button(
                    label="📥 Download Full Report",
                    data=st.session_state.get('analysis_result', ''),
                    file_name="code_analysis_report.md",
                    mime="text/markdown"
                )
    
    # Tab 3: Risk Map
    with tab3:
        st.header("Risk Map")
        
        if st.session_state.get('risk_analysis'):
             st.markdown("### ⚠️ Maintenance & Risk Analysis")
             st.markdown(st.session_state['risk_analysis'])
        elif st.session_state.get('analysis_result'):
            # Fallback for old analyses
            st.warning("Please re-run the analysis to view the separated Risk Map.")
        else:
            st.warning("⚠️ Please run the AI Analysis in the 'Module Analysis' tab first to generate a risk map.")
    
    # Tab 4: Ask Your Code
    with tab4:
        st.header("Ask Your Code")
        
        if not api_key:
            st.warning("⚠️ Please enter your API Key in the sidebar to chat with your code")
        else:
            st.info("💬 Ask questions about your codebase and get AI-powered answers based on your uploaded code")
            
            # Display chat messages
            for message in st.session_state['messages']:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # Chat Input Form
            with st.form(key="chat_form", clear_on_submit=True):
                user_question = st.text_area("Ask your question:", height=100)
                submit_button = st.form_submit_button("Send", type="primary")
            
            if submit_button and user_question:
                # Add user message to chat history
                st.session_state['messages'].append({"role": "user", "content": user_question})
                
                # Force rerun to show user message immediately
                st.rerun()

            # Process AI response if last message is from user (handled after rerun)
            if st.session_state['messages'] and st.session_state['messages'][-1]["role"] == "user":
                 # Display latest user message is handled by the loop above, now generate response
                 last_question = st.session_state['messages'][-1]["content"]
                 
                 with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            # Build context
                            chat_context = f"""You are an expert code analyst. Answer questions about the provided codebase.
CRITICAL RULES:
- Base your answers ONLY on the code context provided
- If the answer cannot be found in the code, say "I cannot find that information in the provided code"
- Be specific and reference actual code snippets when relevant
- Provide helpful explanations for technical concepts

Here is the codebase to analyze:
{st.session_state['full_code_context']}

Previous conversation:
"""
                            for msg in st.session_state['messages'][:-1]:
                                if msg['role'] == 'user':
                                    chat_context += f"\nUser: {msg['content']}"
                                else:
                                    chat_context += f"\nAssistant: {msg['content']}"
                            
                            chat_context += f"\n\nUser: {last_question}\n\nAssistant:"
                            
                            # Make API call with auto-fallback
                            generation_config = {
                                "temperature": 0.7,
                                "top_p": 0.95,
                                "top_k": 40,
                                "max_output_tokens": 2048,
                            }
                            
                            assistant_response, used_model = generate_content_with_fallback(
                                chat_context,
                                api_key,
                                generation_config=generation_config
                            )
                            
                            # Add assistant response to chat history
                            st.session_state['messages'].append({
                                "role": "assistant",
                                "content": assistant_response
                            })
                            st.rerun()
                            
                        except Exception as e:
                            error_msg = f"❌ Error: {str(e)}"
                            st.error(error_msg)
                            st.session_state['messages'].append({
                                "role": "assistant",
                                "content": error_msg
                            })
                            # No rerun here to let user see error
            
            st.divider()
            
            # Clear chat button
            if st.session_state['messages']:
                if 'show_clear_confirm' not in st.session_state:
                    st.session_state['show_clear_confirm'] = False
                
                if not st.session_state['show_clear_confirm']:
                    if st.button("🗑️ Clear Chat History"):
                        st.session_state['show_clear_confirm'] = True
                        st.rerun()
                else:
                    st.warning("Are you sure you want to delete the chat history?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Yes, delete"):
                            st.session_state['messages'] = []
                            st.session_state['show_clear_confirm'] = False
                            st.rerun()
                    with col_no:
                        if st.button("Cancel"):
                            st.session_state['show_clear_confirm'] = False
                            st.rerun()

else:
    st.info("👆 Upload code files to get started with the analysis")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>Powered by Google Gemini | Built with Streamlit</small>
</div>
""", unsafe_allow_html=True)
