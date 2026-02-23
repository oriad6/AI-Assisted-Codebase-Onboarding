# 🚀 AI-Powered Codebase Analyzer & Onboarding Tool

An advanced full-stack application designed to help developers quickly understand new codebases. The tool integrates Google's **Gemini 1.5 Pro/Flash** AI to analyze repositories, map risks, and answer complex architectural questions.

---

## 🌐 Live Demo
**Access the application directly here:** 👉 https://codebase-analysis-ai-tool.streamlit.app/

## 🌟 Key Features

* **Multi-Source Input:** Upload local files or connect directly to any **GitHub Repository** via REST API.
* **AI Analysis Dashboard:**
    * **System Architecture:** High-level overview of the project structure.
    * **Logic Flow:** Deep dive into how the code functions.
    * **Risk Mapping:** Identification of security vulnerabilities and technical debt.
* **User Management:** Secure authentication system (Login/Register) with hashed passwords.
* **Persistence:** Save and reload your analysis history, powered by a **PostgreSQL (Supabase)** database.
* **Smart Fallback:** Adaptive AI logic that switches between Gemini models based on availability.

---

## 🛠 Tech Stack

* **Frontend:** [Streamlit](https://streamlit.io/) (Python-based Web Framework).
* **AI Brain:** [Google Gemini API](https://ai.google.dev/).
* **Database:** [PostgreSQL via Supabase](https://supabase.com/) (Cloud-hosted SQL).
* **Version Control & Deployment:** GitHub & Streamlit Cloud.
* **Authentication:** SHA-256 Password Hashing
* **Integration:** GitHub REST API for remote repository fetching.

---

## 🏗 System Architecture (Three-Tier)

1.  **Presentation Layer:** Streamlit Web Interface.
2.  **Logic Layer:** Python backend handling AI prompting, file processing, and authentication logic.
3.  **Data Layer:** PostgreSQL database for persistent storage of users and analyzed projects.

---

## 🔐 Security & Best Practices
The project follows industry-standard security protocols:
* **Environment Variables:** Sensitive keys (API/Database) are managed via `st.secrets` and are never stored in the source code.
* **Data Protection:** Passwords are never stored in plain text; we use `hashlib` for one-way cryptographic hashing.
* **Connection Pooling:** Optimized database traffic using a dedicated Connection Pooler.
* **Input Sanitization:** AI prompts are structured to prevent data leakage.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.9+
* Google Gemini API Key
* Supabase Database URI

## 🏗 Installation

If you wish to run this project locally on your machine, follow these steps:

### 1. Clone the Project
git clone [https://github.com/oriad6/AI-Assisted-Codebase-Onboarding.git](https://github.com/oriad6/AI-Assisted-Codebase-Onboarding.git)
cd AI-Assisted-Codebase-Onboarding

### 2. Install Dependencies
pip install -r requirements.txt

### 3. Setup Configuration (Secrets)
Create a folder named .streamlit and inside it a file named secrets.toml:
GOOGLE_API_KEY = "your_google_api_key"

[database]
url = "postgresql://postgres.user:password@host:port/postgres"

### 4. Database Setup
Initialize your Supabase project with the following tables:

users (id, username, password_hash)

projects (id, user_id, repo_name, analysis_json, created_at)

### 5. Run Locally
streamlit run app.py
