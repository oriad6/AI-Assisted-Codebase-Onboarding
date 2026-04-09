import { useState } from 'react';
import { runAnalysis, saveProject } from '../api/client';
import { useAuth } from '../context/AuthContext';
import ReactMarkdown from 'react-markdown';
import {
    LayoutGrid,
    Shield,
    FileCode,
    Sparkles,
    Save,
    Loader2,
    ArrowLeft,
    CheckCircle,
    FileText,
    Box,
    Database,
    History,
} from 'lucide-react';

export default function AnalysisDashboard({
    project,
    apiKey,
    onBack,
    onUpdate,
}) {
    const { auth } = useAuth();
    const [activeTab, setActiveTab] = useState('structure');
    const [analyzing, setAnalyzing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [saveMsg, setSaveMsg] = useState('');
    const [error, setError] = useState('');
    const [projectName, setProjectName] = useState(() => {
        if (project.repoUrl && project.repoUrl.includes('/')) {
            return project.repoUrl.split('/').pop() || 'My Project';
        }
        return 'My Project';
    });

    const handleAnalyze = async () => {
        if (!apiKey) {
            setError('Please set your API key in the header settings.');
            return;
        }
        setError('');
        setAnalyzing(true);
        try {
            const data = await runAnalysis(project.codeContext, apiKey);
            if (data.success) {
                onUpdate({
                    analysisModule: data.analysis_module,
                    analysisRisk: data.analysis_risk,
                });
                setActiveTab('module');
            } else {
                setError(data.error || 'Analysis failed');
            }
        } catch {
            setError('Connection failed. Is the backend running?');
        } finally {
            setAnalyzing(false);
        }
    };

    const handleSave = async () => {
        setSaveMsg('');
        setSaving(true);
        try {
            const data = await saveProject({
                user_id: auth.userId,
                name: projectName,
                source_type: project.sourceType,
                repo_url: project.repoUrl,
                code_context: project.codeContext,
                analysis_module: project.analysisModule || '',
                analysis_risk: project.analysisRisk || '',
            });
            setSaveMsg(data.success ? 'Saved!' : data.message);
        } catch {
            setSaveMsg('Save failed');
        } finally {
            setSaving(false);
        }
    };

    const tabs = [
        { id: 'structure', label: 'Structure', icon: LayoutGrid },
        { id: 'module', label: 'Module Analysis', icon: FileText },
        { id: 'risk', label: 'Risk Map', icon: Shield },
    ];

    return (
        <div className="animate-fade-in">
            {/* Top bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <button
                    onClick={onBack}
                    className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Projects
                </button>

                <div className="flex items-center gap-2">
                    <input
                        id="project-name-input"
                        type="text"
                        value={projectName}
                        onChange={(e) => setProjectName(e.target.value)}
                        className="px-3 py-1.5 text-sm rounded-lg border border-border bg-surface-alt text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition w-48"
                        placeholder="Project Name"
                    />
                    <button
                        id="save-project-btn"
                        onClick={handleSave}
                        disabled={saving}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-surface border border-border text-text-primary hover:bg-surface-hover transition-colors"
                    >
                        {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                        Save
                    </button>
                    {saveMsg && (
                        <span className={`text-xs font-medium ${saveMsg === 'Saved!' ? 'text-success' : 'text-danger'}`}>
                            {saveMsg}
                        </span>
                    )}
                </div>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                {[
                    { label: 'Files', value: project.files?.length || 0, icon: FileCode, color: 'text-primary-600' },
                    { label: 'Source', value: project.sourceType || '—', icon: project.sourceType === 'github' ? Database : Box, color: 'text-violet-600' },
                    { label: 'Context', value: project.codeContext ? 'Yes' : 'No', icon: CheckCircle, color: 'text-success' },
                    { label: 'From DB', value: project.isLoadedFromDb ? 'Yes' : 'No', icon: History, color: 'text-amber-600' },
                ].map((s) => (
                    <div key={s.label} className="bg-surface rounded-xl border border-border p-4">
                        <div className="flex items-center gap-2 mb-1">
                            <s.icon className={`w-4 h-4 ${s.color}`} />
                            <span className="text-xs text-text-muted font-medium uppercase tracking-wider">{s.label}</span>
                        </div>
                        <p className="text-lg font-semibold text-text-primary">{s.value}</p>
                    </div>
                ))}
            </div>

            {/* Tabs */}
            <div className="flex gap-1 bg-surface-alt p-1 rounded-xl mb-6 border border-border">
                {tabs.map((t) => (
                    <button
                        key={t.id}
                        id={`tab-${t.id}`}
                        onClick={() => setActiveTab(t.id)}
                        className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium rounded-lg transition-all ${activeTab === t.id
                                ? 'bg-surface text-primary-600 shadow-sm border border-border'
                                : 'text-text-secondary hover:text-text-primary'
                            }`}
                    >
                        <t.icon className="w-4 h-4" />
                        {t.label}
                    </button>
                ))}
            </div>

            {/* Tab content */}
            <div className="bg-surface rounded-2xl border border-border shadow-sm p-6 animate-fade-in" key={activeTab}>
                {activeTab === 'structure' && (
                    <>
                        <h3 className="text-lg font-semibold text-text-primary mb-4">System Structure</h3>
                        {project.files && project.files.length > 0 ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                {project.files.map((f, i) => (
                                    <div key={i} className="rounded-xl border border-border p-4 hover:border-primary-300 hover:bg-primary-50/20 transition-all">
                                        <div className="flex items-center gap-2 mb-1">
                                            <FileCode className="w-4 h-4 text-primary-500 flex-shrink-0" />
                                            <span className="font-medium text-sm text-text-primary truncate">
                                                {f.name.split('/').pop()}
                                            </span>
                                        </div>
                                        <p className="text-xs text-text-muted truncate">{f.name}</p>
                                        {f.size != null && (
                                            <p className="text-xs text-text-muted mt-1">{f.size.toLocaleString()} bytes</p>
                                        )}
                                        {!project.isLoadedFromDb && f.content && f.content !== 'Project Data Loaded' && (
                                            <details className="mt-2">
                                                <summary className="text-xs text-primary-600 cursor-pointer hover:underline">
                                                    Preview
                                                </summary>
                                                <pre className="mt-1 text-xs bg-surface-alt rounded-lg p-2 overflow-x-auto max-h-40 border border-border">
                                                    {f.content.slice(0, 800)}
                                                </pre>
                                            </details>
                                        )}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-text-muted text-sm">No files loaded.</p>
                        )}
                    </>
                )}

                {activeTab === 'module' && (
                    <>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-text-primary">Module Analysis</h3>
                            <button
                                id="start-analysis-btn"
                                onClick={handleAnalyze}
                                disabled={analyzing}
                                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                {analyzing ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <Sparkles className="w-4 h-4" />
                                )}
                                {analyzing ? 'Analyzing...' : 'Start AI Analysis'}
                            </button>
                        </div>
                        {error && (
                            <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-danger">
                                {error}
                            </div>
                        )}
                        {project.analysisModule ? (
                            <div className="prose max-w-none text-text-primary text-sm leading-relaxed">
                                <ReactMarkdown>{project.analysisModule}</ReactMarkdown>
                            </div>
                        ) : (
                            <div className="text-center py-12">
                                <Sparkles className="w-8 h-8 text-text-muted mx-auto mb-3" />
                                <p className="text-text-secondary text-sm">
                                    Run AI analysis to see module breakdown
                                </p>
                            </div>
                        )}
                    </>
                )}

                {activeTab === 'risk' && (
                    <>
                        <h3 className="text-lg font-semibold text-text-primary mb-4">Risk Map</h3>
                        {project.analysisRisk ? (
                            <div className="prose max-w-none text-text-primary text-sm leading-relaxed">
                                <ReactMarkdown>{project.analysisRisk}</ReactMarkdown>
                            </div>
                        ) : (
                            <div className="text-center py-12">
                                <Shield className="w-8 h-8 text-text-muted mx-auto mb-3" />
                                <p className="text-text-secondary text-sm">
                                    Run module analysis first to generate the risk map
                                </p>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
