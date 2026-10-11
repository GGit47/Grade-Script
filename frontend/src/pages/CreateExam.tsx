import React, { useState } from 'react';
import { Plus, Trash2, Check, ArrowLeft } from 'lucide-react';
import { api } from '../services/api';

interface CreateExamProps {
  onExamCreated: (examId: number) => void;
  onCancel: () => void;
}

interface QuestionInput {
  question_number: number;
  question_text: string;
  reference_answer: string;
  max_marks: number;
  essential_keywords: string;
  rubric_criteria: string;
}

export const CreateExam: React.FC<CreateExamProps> = ({ onExamCreated, onCancel }) => {
  const [title, setTitle] = useState('');
  const [subject, setSubject] = useState('');
  const [classOrBatch, setClassOrBatch] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [questions, setQuestions] = useState<QuestionInput[]>([
    {
      question_number: 1,
      question_text: 'Define Operating System and list two of its primary functions.',
      reference_answer: 'An operating system is system software that manages computer hardware and software resources, providing common services for computer programs. Primary functions include process management, memory management, file systems, and hardware abstraction.',
      max_marks: 5,
      essential_keywords: 'system software, hardware, resource management, memory management, process',
      rubric_criteria: '2 marks for clear definition; 3 marks for mentioning at least 2 primary functions accurately.',
    },
    {
      question_number: 2,
      question_text: 'What is the difference between synchronous and asynchronous transmission?',
      reference_answer: 'In synchronous transmission, data is transmitted in blocks or frames synchronized by an external clock signal. In asynchronous transmission, data is sent byte-by-byte using start and stop bits without a shared clock.',
      max_marks: 5,
      essential_keywords: 'clock signal, start bit, stop bit, frames, synchronous, asynchronous',
      rubric_criteria: '2.5 marks for clock synchronization vs start/stop bits; 2.5 marks for data units (frames vs bytes).',
    },
  ]);

  const addQuestion = () => {
    setQuestions([
      ...questions,
      {
        question_number: questions.length + 1,
        question_text: '',
        reference_answer: '',
        max_marks: 5,
        essential_keywords: '',
        rubric_criteria: '',
      },
    ]);
  };

  const removeQuestion = (idx: number) => {
    if (questions.length <= 1) return;
    const updated = questions.filter((_, i) => i !== idx).map((q, i) => ({
      ...q,
      question_number: i + 1,
    }));
    setQuestions(updated);
  };

  const updateQuestion = (idx: number, field: keyof QuestionInput, val: any) => {
    const updated = [...questions];
    updated[idx] = { ...updated[idx], [field]: val };
    setQuestions(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!title.trim() || !subject.trim() || !classOrBatch.trim()) {
      setError('Please fill out all exam metadata (title, subject, class/batch).');
      return;
    }

    for (const q of questions) {
      if (!q.question_text.trim() || !q.reference_answer.trim() || q.max_marks <= 0) {
        setError(`Question #${q.question_number} must have valid text, reference answer, and positive maximum marks.`);
        return;
      }
    }

    try {
      setLoading(true);
      const res = await api.createExam({
        title,
        subject,
        class_or_batch: classOrBatch,
        questions,
      });
      onExamCreated(res.id);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create exam.');
    } finally {
      setLoading(false);
    }
  };

  const totalAllocatedMarks = questions.reduce((sum, q) => sum + (Number(q.max_marks) || 0), 0);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <button
          onClick={onCancel}
          className="text-sm font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1.5"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </button>
        <span className="text-sm text-slate-500 font-medium">
          Total Paper Marks: <strong className="text-blue-600 text-base">{totalAllocatedMarks}</strong>
        </span>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 sm:p-8">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Create New Examination</h2>
        <p className="text-sm text-slate-500 mt-1">
          Specify questions, comprehensive reference answers, essential keywords, and marking rubrics for accurate AI comparison.
        </p>

        {error && (
          <div className="mt-4 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Exam Title
              </label>
              <input
                type="text"
                placeholder="e.g. Midterm Examination 2026"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Subject / Course
              </label>
              <input
                type="text"
                placeholder="e.g. Operating Systems (CS301)"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Class / Batch
              </label>
              <input
                type="text"
                placeholder="e.g. 3rd Year B.Tech AI-ML"
                value={classOrBatch}
                onChange={(e) => setClassOrBatch(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                required
              />
            </div>
          </div>

          <div className="border-t border-slate-200 pt-6 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900">Questions & Evaluation Criteria</h3>
              <button
                type="button"
                onClick={addQuestion}
                className="px-3.5 py-2 bg-blue-50 text-blue-700 hover:bg-blue-100 font-semibold text-xs rounded-xl flex items-center gap-1.5 transition"
              >
                <Plus className="w-4 h-4" /> Add Question
              </button>
            </div>

            {questions.map((q, idx) => (
              <div
                key={idx}
                className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 space-y-4 relative"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-slate-700 bg-white px-3 py-1 rounded-lg border border-slate-200">
                    Question #{q.question_number}
                  </span>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-slate-500 font-medium">Max Marks:</span>
                      <input
                        type="number"
                        min="1"
                        max="50"
                        value={q.max_marks}
                        onChange={(e) => updateQuestion(idx, 'max_marks', parseFloat(e.target.value) || 0)}
                        className="w-16 px-2 py-1 bg-white border border-slate-300 rounded-lg text-sm text-center font-bold text-blue-700"
                        required
                      />
                    </div>
                    {questions.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeQuestion(idx)}
                        className="p-1.5 text-slate-400 hover:text-red-600 transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Question Prompt
                  </label>
                  <textarea
                    rows={2}
                    value={q.question_text}
                    onChange={(e) => updateQuestion(idx, 'question_text', e.target.value)}
                    placeholder="Enter the question text..."
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Standard Reference Answer
                  </label>
                  <textarea
                    rows={3}
                    value={q.reference_answer}
                    onChange={(e) => updateQuestion(idx, 'reference_answer', e.target.value)}
                    placeholder="Enter the model / reference answer that students will be graded against..."
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    required
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">
                      Essential Keywords / Concepts (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={q.essential_keywords}
                      onChange={(e) => updateQuestion(idx, 'essential_keywords', e.target.value)}
                      placeholder="e.g. process, synchronization, deadlock, semaphore"
                      className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">
                      Marking Rubric / Partial Credit Instructions
                    </label>
                    <input
                      type="text"
                      value={q.rubric_criteria}
                      onChange={(e) => updateQuestion(idx, 'rubric_criteria', e.target.value)}
                      placeholder="e.g. 2 marks for definition, 3 marks for explanation"
                      className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="pt-4 flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="px-5 py-2.5 rounded-xl border border-slate-300 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-md transition flex items-center gap-2 disabled:opacity-50"
            >
              {loading ? 'Creating Examination...' : (
                <>
                  <Check className="w-4 h-4" /> Save & Continue
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
