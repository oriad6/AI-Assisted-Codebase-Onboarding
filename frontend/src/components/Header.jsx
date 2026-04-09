import { useAuth } from '../context/AuthContext';
import { Code2, LogOut, Settings } from 'lucide-react';
import { useState } from 'react';

export default function Header({ apiKey, onApiKeyChange }) {
    const { auth, logout } = useAuth();
    const [showSettings, setShowSettings] = useState(false);

    return (
        <header className="bg-surface border-b border-border sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-primary-600 flex items-center justify-center shadow-sm">
                            <Code2 className="w-5 h-5 text-white" />
                        </div>
                        <h1 className="text-lg font-semibold text-text-primary tracking-tight">
                            Code Onboarding
                        </h1>
                    </div>

                    {/* Right side */}
                    {auth && (
                        <div className="flex items-center gap-3">
                            {/* Settings toggle */}
                            <div className="relative">
                                <button
                                    id="settings-toggle"
                                    onClick={() => setShowSettings(!showSettings)}
                                    className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-hover transition-colors"
                                >
                                    <Settings className="w-4 h-4" />
                                    <span className="hidden sm:inline">API Key</span>
                                </button>

                                {showSettings && (
                                    <div className="absolute right-0 top-full mt-2 w-80 bg-surface rounded-xl border border-border shadow-lg p-4 animate-fade-in">
                                        <label className="block text-xs font-medium text-text-secondary mb-1.5">
                                            Google AI API Key
                                        </label>
                                        <input
                                            id="api-key-input"
                                            type="password"
                                            value={apiKey}
                                            onChange={(e) => onApiKeyChange(e.target.value)}
                                            placeholder="Enter your API key..."
                                            className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-alt text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition"
                                        />
                                        <p className="mt-2 text-xs text-text-muted">
                                            Get a key from{' '}
                                            <a
                                                href="https://aistudio.google.com/app/apikey"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-primary-600 hover:underline"
                                            >
                                                Google AI Studio
                                            </a>
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* User info */}
                            <div className="flex items-center gap-2 pl-3 border-l border-border">
                                <div className="w-7 h-7 rounded-full bg-primary-100 flex items-center justify-center">
                                    <span className="text-xs font-semibold text-primary-700">
                                        {auth.username.charAt(0).toUpperCase()}
                                    </span>
                                </div>
                                <span className="text-sm font-medium text-text-primary hidden sm:inline">
                                    {auth.username}
                                </span>
                                <button
                                    id="logout-btn"
                                    onClick={logout}
                                    className="p-1.5 rounded-lg text-text-muted hover:text-danger hover:bg-red-50 transition-colors"
                                    title="Logout"
                                >
                                    <LogOut className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
}
