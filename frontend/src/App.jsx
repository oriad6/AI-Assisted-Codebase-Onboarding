import { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Header from './components/Header';
import LoginForm from './components/LoginForm';
import ProjectHistory from './components/ProjectHistory';
import ProjectInput from './components/ProjectInput';
import AnalysisDashboard from './components/AnalysisDashboard';
import ChatInterface from './components/ChatInterface';

function AppContent() {
  const { auth } = useAuth();
  const [apiKey, setApiKey] = useState('');
  const [view, setView] = useState('history'); // 'history' | 'input' | 'dashboard'
  const [project, setProject] = useState(null);

  // Not logged in — show login
  if (!auth) {
    return <LoginForm />;
  }

  const handleProjectLoaded = (data) => {
    setProject({
      files: data.files,
      codeContext: data.codeContext,
      sourceType: data.sourceType,
      repoUrl: data.repoUrl,
      analysisModule: data.analysisModule || '',
      analysisRisk: data.analysisRisk || '',
      isLoadedFromDb: data.isLoadedFromDb || false,
    });
    setView('dashboard');
  };

  const handleBack = () => {
    setProject(null);
    setView('history');
  };

  const handleUpdateAnalysis = (updates) => {
    setProject((prev) => ({ ...prev, ...updates }));
  };

  return (
    <div className="min-h-screen bg-surface-alt">
      <Header apiKey={apiKey} onApiKeyChange={setApiKey} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {view === 'history' && (
          <ProjectHistory
            onNewProject={() => setView('input')}
            onProjectLoaded={handleProjectLoaded}
          />
        )}

        {view === 'input' && (
          <ProjectInput
            onProjectLoaded={handleProjectLoaded}
            onBack={() => setView('history')}
          />
        )}

        {view === 'dashboard' && project && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <AnalysisDashboard
                project={project}
                apiKey={apiKey}
                onBack={handleBack}
                onUpdate={handleUpdateAnalysis}
              />
            </div>
            <div className="lg:col-span-1">
              <ChatInterface codeContext={project.codeContext} apiKey={apiKey} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
