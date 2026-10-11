import { useState, useEffect } from 'react';
import { BookOpen, UploadCloud, GraduationCap, LayoutDashboard } from 'lucide-react';
import { Dashboard } from './pages/Dashboard';
import { CreateExam } from './pages/CreateExam';
import { UploadSheet } from './pages/UploadSheet';
import { EvaluationReview } from './pages/EvaluationReview';
import { api } from './services/api';
import type { Exam, DashboardStats } from './types';

export function App() {
  const [currentView, setCurrentView] = useState<'dashboard' | 'create-exam' | 'upload' | 'review'>('dashboard');
  const [selectedExamId, setSelectedExamId] = useState<number | undefined>(undefined);
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<number | undefined>(undefined);

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshData = async () => {
    try {
      setLoading(true);
      const [statsData, examsData] = await Promise.all([
        api.getDashboard(),
        api.getExams(),
      ]);
      setStats(statsData);
      setExams(examsData);
    } catch (err) {
      console.error('Failed to load initial data from backend:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshData();
  }, []);

  const handleNavigate = (view: string, id?: number) => {
    if (view === 'create-exam') {
      setCurrentView('create-exam');
    } else if (view === 'upload') {
      setSelectedExamId(id);
      setCurrentView('upload');
    } else if (view === 'review') {
      setSelectedSubmissionId(id);
      setCurrentView('review');
    } else {
      setCurrentView('dashboard');
      refreshData();
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => handleNavigate('dashboard')}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <span className="font-extrabold text-slate-900 text-lg tracking-tight">
                Grade Script
              </span>
              <span className="block text-[10px] text-blue-600 font-bold uppercase tracking-wider">
                DL Handwriting OCR & Evaluator
              </span>
            </div>
          </div>

          <nav className="flex items-center gap-2">
            <button
              onClick={() => handleNavigate('dashboard')}
              className={`px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition ${
                currentView === 'dashboard'
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <LayoutDashboard className="w-4 h-4" /> Dashboard
            </button>
            <button
              onClick={() => handleNavigate('create-exam')}
              className={`px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition ${
                currentView === 'create-exam'
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <BookOpen className="w-4 h-4" /> New Exam
            </button>
            <button
              onClick={() => handleNavigate('upload')}
              className={`px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition ${
                currentView === 'upload'
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <UploadCloud className="w-4 h-4" /> Upload Paper
            </button>
          </nav>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {loading && currentView === 'dashboard' && !stats ? (
          <div className="flex flex-col items-center justify-center py-24">
            <div className="animate-spin rounded-full h-10 w-10 border-4 border-blue-600 border-t-transparent" />
            <p className="mt-4 text-sm font-semibold text-slate-500">
              Connecting to Grade Script backend...
            </p>
          </div>
        ) : (
          <>
            {currentView === 'dashboard' && (
              <Dashboard stats={stats} onNavigate={handleNavigate} />
            )}

            {currentView === 'create-exam' && (
              <CreateExam
                onExamCreated={(examId) => {
                  refreshData();
                  handleNavigate('upload', examId);
                }}
                onCancel={() => handleNavigate('dashboard')}
              />
            )}

            {currentView === 'upload' && (
              <UploadSheet
                exams={exams}
                preselectedExamId={selectedExamId}
                onUploaded={(subId) => {
                  refreshData();
                  handleNavigate('review', subId);
                }}
                onCancel={() => handleNavigate('dashboard')}
              />
            )}

            {currentView === 'review' && selectedSubmissionId && (
              <EvaluationReview
                submissionId={selectedSubmissionId}
                onBack={() => handleNavigate('dashboard')}
              />
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 text-center text-xs text-slate-500">
          Grade Script • B.Tech AI-ML • Pretrained TrOCR Line Recognition & Sentence Transformers Evaluation
        </div>
      </footer>
    </div>
  );
}

export default App;
