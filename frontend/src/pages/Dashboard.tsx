import React from 'react';
import { BookOpen, UploadCloud, CheckCircle2, FileText, ArrowRight } from 'lucide-react';
import type { DashboardStats } from '../types';

interface DashboardProps {
  stats: DashboardStats | null;
  onNavigate: (view: string, id?: number) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ stats, onNavigate }) => {
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-blue-700 via-indigo-700 to-indigo-900 rounded-2xl p-8 text-white shadow-xl">
        <div className="max-w-3xl">
          <span className="px-3 py-1 bg-blue-500/30 text-blue-100 rounded-full text-xs font-semibold uppercase tracking-wider">
            AI-Assisted Assessment Platform
          </span>
          <h1 className="text-3xl font-extrabold mt-3 tracking-tight">
            Handwritten Examination Evaluation
          </h1>
          <p className="mt-2 text-blue-100/90 text-sm leading-relaxed">
            Grade Script integrates Microsoft TrOCR for line-level handwriting recognition and semantic embedding analysis to provide explainable grading proposals with complete teacher authority.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              onClick={() => onNavigate('create-exam')}
              className="px-5 py-2.5 bg-white text-indigo-900 font-semibold rounded-xl text-sm shadow hover:bg-blue-50 transition flex items-center gap-2"
            >
              <BookOpen className="w-4 h-4" /> Create New Examination
            </button>
            <button
              onClick={() => onNavigate('upload')}
              className="px-5 py-2.5 bg-blue-600/40 border border-blue-400/40 text-white font-semibold rounded-xl text-sm hover:bg-blue-600/60 transition flex items-center gap-2"
            >
              <UploadCloud className="w-4 h-4" /> Upload Answer Sheet
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
            <BookOpen className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Exams</p>
            <h3 className="text-2xl font-bold text-slate-900">{stats?.total_exams ?? 0}</h3>
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center font-bold">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Submissions</p>
            <h3 className="text-2xl font-bold text-slate-900">{stats?.total_submissions ?? 0}</h3>
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
            <UploadCloud className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Awaiting Review</p>
            <h3 className="text-2xl font-bold text-amber-600">{stats?.evaluations_pending ?? 0}</h3>
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 border border-slate-200/80 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Approved & Done</p>
            <h3 className="text-2xl font-bold text-emerald-600">{stats?.evaluations_completed ?? 0}</h3>
          </div>
        </div>
      </div>

      {/* Recent Activity Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Exams */}
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-slate-900 text-lg">Examinations</h3>
            <button
              onClick={() => onNavigate('create-exam')}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              + Add Exam
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {stats?.recent_exams && stats.recent_exams.length > 0 ? (
              stats.recent_exams.map((exam) => (
                <div key={exam.id} className="py-3 flex items-center justify-between hover:bg-slate-50 px-2 rounded-lg transition">
                  <div>
                    <h4 className="font-semibold text-slate-800 text-sm">{exam.title}</h4>
                    <p className="text-xs text-slate-500">
                      {exam.subject} • {exam.class_or_batch} • {exam.total_max_marks} marks
                    </p>
                  </div>
                  <button
                    onClick={() => onNavigate('upload', exam.id)}
                    className="px-3 py-1.5 text-xs font-medium bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 flex items-center gap-1"
                  >
                    Upload <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-slate-400 text-sm">
                No exams created yet. Click "+ Add Exam" to define your first examination paper.
              </div>
            )}
          </div>
        </div>

        {/* Recent Submissions */}
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-slate-900 text-lg">Recent Submissions</h3>
            <span className="text-xs font-medium text-slate-400">Latest Evaluations</span>
          </div>

          <div className="divide-y divide-slate-100">
            {stats?.recent_submissions && stats.recent_submissions.length > 0 ? (
              stats.recent_submissions.map((sub) => (
                <div key={sub.id} className="py-3 flex items-center justify-between hover:bg-slate-50 px-2 rounded-lg transition">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-800 text-sm">{sub.student_roll_no}</span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase ${
                          sub.is_approved
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {sub.is_approved ? 'Approved' : 'Pending Review'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {sub.exam_title} • Approved: {sub.approved_total} pts (AI suggested: {sub.suggested_total})
                    </p>
                  </div>
                  <button
                    onClick={() => onNavigate('review', sub.id)}
                    className="px-3 py-1.5 text-xs font-medium bg-indigo-50 text-indigo-700 rounded-md hover:bg-indigo-100 flex items-center gap-1"
                  >
                    Review <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-slate-400 text-sm">
                No answer sheets submitted yet. Upload a student handwritten sheet to start AI evaluation.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
