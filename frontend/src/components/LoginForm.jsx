import { useState } from 'react';
import { login, register } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Code2, Loader2 } from 'lucide-react';

export default function LoginForm() {
    const { loginUser } = useAuth();
    const [isLogin, setIsLogin] = useState(true);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        if (!username.trim() || !password.trim()) {
            setError('Please fill in all fields');
            return;
        }
        setLoading(true);
        try {
            if (isLogin) {
                const data = await login(username, password);
                if (data.success) {
                    loginUser(data);
                } else {
                    setError(data.message || 'Invalid credentials');
                }
            } else {
                const data = await register(username, password);
                if (data.success) {
                    setSuccess(data.message);
                    setIsLogin(true);
                    setPassword('');
                } else {
                    setError(data.message);
                }
            }
        } catch {
            setError('Connection failed. Is the server running?');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-surface-alt">
            <div className="w-full max-w-md animate-fade-in">
                {/* Logo */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-600 shadow-lg mb-4">
                        <Code2 className="w-7 h-7 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-text-primary">Code Onboarding</h1>
                    <p className="text-text-secondary mt-1">Analyze and understand codebases with AI</p>
                </div>

                {/* Card */}
                <div className="bg-surface rounded-2xl border border-border shadow-sm p-6">
                    {/* Tabs */}
                    <div className="flex mb-6 bg-surface-alt rounded-lg p-1">
                        <button
                            id="login-tab"
                            onClick={() => { setIsLogin(true); setError(''); setSuccess(''); }}
                            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${isLogin
                                    ? 'bg-surface text-text-primary shadow-sm'
                                    : 'text-text-secondary hover:text-text-primary'
                                }`}
                        >
                            Login
                        </button>
                        <button
                            id="register-tab"
                            onClick={() => { setIsLogin(false); setError(''); setSuccess(''); }}
                            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${!isLogin
                                    ? 'bg-surface text-text-primary shadow-sm'
                                    : 'text-text-secondary hover:text-text-primary'
                                }`}
                        >
                            Register
                        </button>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-text-secondary mb-1.5">
                                Username
                            </label>
                            <input
                                id="username-input"
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="Enter username"
                                className="w-full px-3.5 py-2.5 rounded-xl border border-border bg-surface-alt text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-text-secondary mb-1.5">
                                Password
                            </label>
                            <input
                                id="password-input"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter password"
                                className="w-full px-3.5 py-2.5 rounded-xl border border-border bg-surface-alt text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition"
                            />
                        </div>

                        {error && (
                            <div className="px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-danger">
                                {error}
                            </div>
                        )}
                        {success && (
                            <div className="px-3 py-2 rounded-lg bg-green-50 border border-green-200 text-sm text-success">
                                {success}
                            </div>
                        )}

                        <button
                            id="auth-submit"
                            type="submit"
                            disabled={loading}
                            className="w-full py-2.5 rounded-xl bg-primary-600 text-white font-medium text-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500/30 disabled:opacity-60 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                        >
                            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                            {isLogin ? 'Sign In' : 'Create Account'}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
