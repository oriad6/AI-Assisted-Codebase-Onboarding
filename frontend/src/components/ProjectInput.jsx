import { useState, useRef } from 'react';
import { fetchGithub, uploadFiles } from '../api/client';
import { GitBranch, Upload, Loader2, ArrowLeft, Globe, FileUp } from 'lucide-react';

export default function ProjectInput({ onProjectLoaded, onBack }) {
    const [tab, setTab] = useState('github');
    const [url, setUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const fileInputRef = useRef(null);
    const [selectedFiles, setSelectedFiles] = useState([]);

    const handleGithubFetch = async () => {
        if (!url.trim()) return;
        setError('');
        setLoading(true);
        try {
            const data = await fetchGithub(url);
            if (data.success) {
                onProjectLoaded({
                    files: data.files,
                    codeContext: data.code_context,
                    sourceType: 'github',
                    repoUrl: url,
                });
            } else {
                setError(data.error || 'Failed to fetch repository');
            }
        } catch {
            setError('Connection failed. Is the backend server running?');
        } finally {
            setLoading(false);
        }
    };

    const handleFileUpload = async () => {
        if (!selectedFiles.length) return;
        setError('');
        setLoading(true);
        try {
            const data = await uploadFiles(selectedFiles);
            if (data.success) {
                onProjectLoaded({
                    files: data.files,
                    codeContext: data.code_context,
                    sourceType: 'upload',
                    repoUrl: 'Local Upload',
                });
            } else {
                setError(data.error || 'Failed to process files');
            }
        } catch {
            setError('Connection failed. Is the backend server running?');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-3xl mx-auto animate-fade-in">
            <button
                onClick={onBack}
                className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary mb-6 transition-colors"
            >
                <ArrowLeft className="w-4 h-4" />
                Back to Projects
            </button>

            <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-text-primary">Analyze a Project</h2>
                <p className="text-text-secondary mt-1">Import code from GitHub or upload files</p>
            </div>

            <div className="bg-surface rounded-2xl border border-border shadow-sm overflow-hidden">
                {/* Tab selector */}
                <div className="flex border-b border-border">
                    <button
                        id="github-tab"
                        onClick={() => setTab('github')}
                        className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-sm font-medium transition-colors ${tab === 'github'
                            ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50/50'
                            : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                            }`}
                    >
                        <Globe className="w-4 h-4" />
                        GitHub Repository
                    </button>
                    <button
                        id="upload-tab"
                        onClick={() => setTab('upload')}
                        className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-sm font-medium transition-colors ${tab === 'upload'
                            ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50/50'
                            : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                            }`}
                    >
                        <FileUp className="w-4 h-4" />
                        File Upload
                    </button>
                </div>

                <div className="p-6">
                    {tab === 'github' ? (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                                    Repository URL
                                </label>
                                <input
                                    id="github-url-input"
                                    type="text"
                                    value={url}
                                    onChange={(e) => setUrl(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && handleGithubFetch()}
                                    placeholder="https://github.com/owner/repo"
                                    className="w-full px-4 py-3 rounded-xl border border-border bg-surface-alt text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition"
                                />
                            </div>
                            <button
                                id="fetch-github-btn"
                                onClick={handleGithubFetch}
                                disabled={loading || !url.trim()}
                                className="w-full py-3 rounded-xl bg-primary-600 text-white font-medium text-sm hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                            >
                                {loading ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <GitBranch className="w-4 h-4" />
                                )}
                                {loading ? 'Fetching Repository...' : 'Fetch & Analyze'}
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <div
                                onClick={() => fileInputRef.current?.click()}
                                className="border-2 border-dashed border-border rounded-xl p-8 text-center cursor-pointer hover:border-primary-400 hover:bg-primary-50/30 transition-colors"
                            >
                                <Upload className="w-8 h-8 text-text-muted mx-auto mb-3" />
                                <p className="text-sm font-medium text-text-primary">
                                    Click to select files
                                </p>
                                <p className="text-xs text-text-muted mt-1">
                                    Supports .py, .js, .ts, .jsx, .tsx, .java, .go, .cpp, .c, .h, .rs, and more
                                </p>
                                {selectedFiles.length > 0 && (
                                    <p className="text-sm text-primary-600 font-medium mt-3">
                                        {selectedFiles.length} file(s) selected
                                    </p>
                                )}
                            </div>
                            <input
                                ref={fileInputRef}
                                type="file"
                                multiple
                                className="hidden"
                                onChange={(e) => setSelectedFiles(Array.from(e.target.files))}
                            />
                            <button
                                id="upload-files-btn"
                                onClick={handleFileUpload}
                                disabled={loading || !selectedFiles.length}
                                className="w-full py-3 rounded-xl bg-primary-600 text-white font-medium text-sm hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                            >
                                {loading ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <Upload className="w-4 h-4" />
                                )}
                                {loading ? 'Processing Files...' : 'Process & Analyze'}
                            </button>
                        </div>
                    )}

                    {error && (
                        <div className="mt-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-danger">
                            {error}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
