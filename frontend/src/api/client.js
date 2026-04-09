import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000/api',
    headers: { 'Content-Type': 'application/json' },
});

// --- Auth ---
export async function login(username, password) {
    const { data } = await api.post('/login', { username, password });
    return data;
}

export async function register(username, password) {
    const { data } = await api.post('/register', { username, password });
    return data;
}

// --- GitHub / Upload ---
export async function fetchGithub(url) {
    const { data } = await api.post('/fetch-github', { url });
    return data;
}

export async function uploadFiles(files) {
    const form = new FormData();
    files.forEach((f) => form.append('files', f));
    const { data } = await api.post('/upload-files', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
}

// --- Analysis ---
export async function runAnalysis(codeContext, apiKey) {
    const { data } = await api.post('/analyze', {
        code_context: codeContext,
        api_key: apiKey,
    });
    return data;
}

// --- Chat ---
export async function chat(question, codeContext, apiKey) {
    const { data } = await api.post('/chat', {
        question,
        code_context: codeContext,
        api_key: apiKey,
    });
    return data;
}

// --- History ---
export async function getHistory(userId) {
    const { data } = await api.get('/history', { params: { user_id: userId } });
    return data;
}

export async function getProject(projectId) {
    const { data } = await api.get(`/projects/${projectId}`);
    return data;
}

export async function saveProject(project) {
    const { data } = await api.post('/projects', project);
    return data;
}

export default api;
