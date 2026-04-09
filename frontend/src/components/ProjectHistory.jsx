import { useState, useEffect } from 'react';
import { getHistory, getProject } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
    Plus,
    FolderOpen,
    Calendar,
    GitBranch,
    Upload,
    ShieldCheck,
    LayoutGrid,
    Loader2,
} from 'lucide-react';

export default function ProjectHistory({ onNewProject, onProjectLoaded }) {
    const { auth } = useAuth();
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingId, setLoadingId] = useState(null);
    const [error, setError] = useState('');

    useEffect(() => {
        loadHistory();
    }, []);

    const loadHistory = async () => {
        setLoading(true);
        setError('');
        try {
            const data = await getHistory(auth.userId);
            setProjects(data);
        } catch {
            setError('Failed to load project history');
        } finally {
            setLoading(false);
        }
    };

    const openProject = async (projectId) => {
        setLoadingId(projectId);
        try {
            const p = await getProject(projectId);
            onProjectLoaded({
                files: [{ name: p.name, content: 'Project Data Loaded' }],
                codeContext: p.code_context || '',
                sourceType: p.source_type,
                repoUrl: p.repo_url,
                analysisModule: p.analysis_module,
                analysisRisk: p.analysis_risk,
                isLoadedFromDb: true,
            });
        } catch {
            setError('Failed to load project');
        } finally {
            setLoadingId(null);
        }
    };

    return (
        <div className="max-w-5xl mx-auto animate-fade-in">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h2 className="text-2xl font-bold text-text-primary">Projects</h2>
                    <p className="text-text-secondary text-sm mt-0.5">Your analyzed codebases</p>
                </div>
                <button
                    id="new-project-btn"
                    onClick={onNewProject}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors shadow-sm"
                >
                    <Plus className="w-4 h-4" />
                    New Analysis
                </button>
            </div>

            {error && (
                <div className="mb-6 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-danger">
                    {error}
                </div>
            )}

            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
                </div>
            ) : projects.length === 0 ? (
                <div className="text-center py-20 bg-surface rounded-2xl border border-border">
                    <FolderOpen className="w-12 h-12 text-text-muted mx-auto mb-3" />
                    <p className="text-text-secondary font-medium">No projects yet</p>
                    <p className="text-text-muted text-sm mt-1">Click "New Analysis" to get started</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {projects.map((p) => {
                        const displayName =
                            p.repo_url && p.repo_url.includes('github.com/')
                                ? p.repo_url.split('/').pop() || p.name
                                : p.name;

                        return (
                            <div
                                key={p.id}
                                className="bg-surface rounded-xl border border-border hover:border-primary-300 hover:shadow-md transition-all p-5 flex flex-col"
                            >
                                <div className="flex items-start gap-3 mb-3">
                                    <div className="w-9 h-9 rounded-lg bg-primary-50 flex items-center justify-center flex-shrink-0">
                                        {p.source_type === 'github' ? (
                                            <GitBranch className="w-4 h-4 text-primary-600" />
                                        ) : (
                                            <Upload className="w-4 h-4 text-primary-600" />
                                        )}
                                    </div>
                                    <div className="min-w-0">
                                        <h3 className="font-semibold text-text-primary truncate">{displayName}</h3>
                                        <div className="flex items-center gap-1.5 text-xs text-text-muted mt-0.5">
                                            <Calendar className="w-3 h-3" />
                                            {p.created_at}
                                        </div>
                                    </div>
                                </div>

                                {/* Tags */}
                                <div className="flex flex-wrap gap-1.5 mb-4">
                                    {p.has_module_analysis && (
                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 text-xs text-primary-700 font-medium">
                                            <LayoutGrid className="w-3 h-3" />
                                            Modules
                                        </span>
                                    )}
                                    {p.has_risk_map && (
                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-50 text-xs text-amber-700 font-medium">
                                            <ShieldCheck className="w-3 h-3" />
                                            Risks
                                        </span>
                                    )}
                                </div>

                                <button
                                    id={`open-project-${p.id}`}
                                    onClick={() => openProject(p.id)}
                                    disabled={loadingId === p.id}
                                    className="mt-auto w-full py-2 rounded-lg bg-surface-alt border border-border text-sm font-medium text-text-primary hover:bg-surface-hover hover:border-border-strong transition-colors flex items-center justify-center gap-2"
                                >
                                    {loadingId === p.id ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <FolderOpen className="w-4 h-4" />
                                    )}
                                    Open
                                </button>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
