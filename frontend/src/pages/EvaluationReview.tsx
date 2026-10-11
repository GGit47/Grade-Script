import React, { useState, useEffect } from 'react';
import {
  Check,
  AlertTriangle,
  Download,
  Edit2,
  Save,
  FileCheck,
  ArrowLeft,
} from 'lucide-react';
import { api } from '../services/api';
import type { SubmissionDetail } from '../types';

interface EvaluationReviewProps {
  submissionId: number;
  onBack: () => void;
}

export const EvaluationReview: React.FC<EvaluationReviewProps> = ({
  submissionId,
  onBack,
}) => {
  const [submission, setSubmission] = useState<SubmissionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingRegionId, setEditingRegionId] = useState<number | null>(null);
  const [editText, setEditText] = useState('');
  const [editingMarksId, setEditingMarksId] = useState<number | null>(null);
  const [teacherMarks, setTeacherMarks] = useState<number>(0);
  const [teacherNotes, setTeacherNotes] = useState<string>('');
  const [saving, setSaving] = useState(false);

  const fetchSubmission = async () => {
    try {
      setLoading(true);
      const data = await api.getSubmission(submissionId);
      setSubmission(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load submission data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubmission();
  }, [submissionId]);

  const handleSaveTranscription = async (regionId: number) => {
    try {
      setSaving(true);
      await api.updateRegion(regionId, { edited_text: editText });
      setEditingRegionId(null);
      await fetchSubmission();
    } catch (err) {
      alert('Failed to update transcription.');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveMarks = async (evalId: number) => {
    try {
      setSaving(true);
      await api.updateEvaluation(evalId, {
        approved_marks: teacherMarks,
        teacher_notes: teacherNotes,
        is_teacher_approved: true,
      });
      setEditingMarksId(null);
      await fetchSubmission();
    } catch (err) {
      alert('Failed to save teacher marks.');
    } finally {
      setSaving(false);
    }
  };

  const handleFinalize = async () => {
    if (!confirm('Are you sure you want to approve and finalize this student evaluation?')) return;
    try {
      setSaving(true);
      await api.finalizeSubmission(submissionId);
      await fetchSubmission();
      alert('Evaluation finalized successfully! You can now download the official report.');
    } catch (err) {
      alert('Failed to finalize evaluation.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-4 border-blue-600 border-t-transparent" />
        <p className="mt-4 text-slate-600 font-medium">Loading evaluation data & recognized crops...</p>
      </div>
    );
  }

  if (!submission) {
    return (
      <div className="text-center py-20">
        <p className="text-red-600 font-semibold">{error || 'Submission not found.'}</p>
        <button onClick={onBack} className="mt-4 px-4 py-2 bg-slate-200 rounded-lg text-sm">
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header Bar */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-slate-100 rounded-xl transition text-slate-600"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-slate-900">
                Evaluation: {submission.student_roll_no}
              </h2>
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-bold uppercase ${
                  submission.is_approved
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-amber-100 text-amber-800'
                }`}
              >
                {submission.is_approved ? 'Teacher Approved' : 'Review Required'}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              File: {submission.original_filename} • Evaluated on{' '}
              {new Date(submission.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Score Summary & Actions */}
        <div className="flex items-center gap-4">
          <div className="text-right">
            <span className="text-xs uppercase text-slate-400 font-bold tracking-wider block">
              Teacher Score
            </span>
            <div className="text-2xl font-black text-blue-600">
              {submission.approved_total.toFixed(1)}{' '}
              <span className="text-sm font-normal text-slate-400">
                (AI: {submission.suggested_total.toFixed(1)})
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {!submission.is_approved ? (
              <button
                onClick={handleFinalize}
                disabled={saving}
                className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-bold shadow-md transition flex items-center gap-2"
              >
                <FileCheck className="w-4 h-4" /> Approve Evaluation
              </button>
            ) : (
              <a
                href={api.getReportUrl(submission.id)}
                target="_blank"
                rel="noreferrer"
                className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-bold shadow-md transition flex items-center gap-2"
              >
                <Download className="w-4 h-4" /> Download PDF Report
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Question Evaluation Cards */}
      <div className="space-y-6">
        {submission.evaluations.map((evalItem, index) => {
          // Find corresponding region
          const page = submission.pages.find((p) =>
            p.regions.some((r) => r.id === evalItem.region_id)
          );
          const region = page?.regions.find((r) => r.id === evalItem.region_id);

          const conceptsMatched: string[] = evalItem.concepts_identified
            ? JSON.parse(evalItem.concepts_identified)
            : [];
          const conceptsMissing: string[] = evalItem.missing_concepts
            ? JSON.parse(evalItem.missing_concepts)
            : [];

          return (
            <div
              key={evalItem.id}
              className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden"
            >
              <div className="bg-slate-50 px-6 py-3.5 border-b border-slate-200 flex items-center justify-between">
                <span className="font-bold text-sm text-slate-800 flex items-center gap-2">
                  <span className="w-6 h-6 rounded-lg bg-blue-600 text-white text-xs flex items-center justify-center font-bold">
                    {index + 1}
                  </span>
                  Question #{index + 1}
                </span>

                <div className="flex items-center gap-3">
                  {evalItem.review_needed && (
                    <span className="px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 text-xs font-semibold flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" /> Needs Teacher Check
                    </span>
                  )}
                  <span className="text-xs text-slate-500 font-medium">
                    Max Marks: <strong>{evalItem.max_marks}</strong>
                  </span>
                </div>
              </div>

              <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left: Scanned Image Crop & Recognized Text */}
                <div className="space-y-4 border-r border-slate-100 pr-0 lg:pr-6">
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                      Handwritten Source Crop
                    </h4>
                    {region?.crop_path ? (
                      <div className="border border-slate-200 rounded-xl overflow-hidden bg-slate-100">
                        <img
                          src={`/${region.crop_path.replace(/\\/g, '/')}`}
                          alt="Handwriting Crop"
                          className="w-full max-h-52 object-contain mx-auto"
                        />
                      </div>
                    ) : (
                      <div className="h-32 border border-dashed border-slate-200 rounded-xl flex items-center justify-center text-xs text-slate-400">
                        No crop assigned
                      </div>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                        TrOCR Extracted Text
                      </h4>
                      {region && editingRegionId !== region.id && (
                        <button
                          onClick={() => {
                            setEditingRegionId(region.id);
                            setEditText(region.edited_text || region.recognized_text);
                          }}
                          className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 font-semibold"
                        >
                          <Edit2 className="w-3 h-3" /> Edit Transcription
                        </button>
                      )}
                    </div>

                    {region && editingRegionId === region.id ? (
                      <div className="space-y-2">
                        <textarea
                          rows={4}
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          className="w-full p-3 border border-blue-400 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none bg-blue-50/20"
                        />
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => setEditingRegionId(null)}
                            className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleSaveTranscription(region.id)}
                            disabled={saving}
                            className="px-3 py-1.5 text-xs bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 flex items-center gap-1"
                          >
                            <Save className="w-3 h-3" /> Save & Re-evaluate
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-sm text-slate-800 leading-relaxed italic">
                        "{evalItem.transcribed_answer || '[No text transcribed]'}"
                      </div>
                    )}
                  </div>
                </div>

                {/* Right: AI Grading Breakdown & Teacher Override */}
                <div className="space-y-4">
                  {/* Semantic & Concept Analysis */}
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-600">Semantic Alignment:</span>
                      <span className="font-bold text-blue-700">
                        {(evalItem.semantic_similarity * 100).toFixed(0)}% Similarity
                      </span>
                    </div>

                    <div>
                      <span className="text-xs font-semibold text-slate-600 block mb-1">
                        Identified Concepts:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {conceptsMatched.length > 0 ? (
                          conceptsMatched.map((c, i) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[11px] font-medium rounded-md"
                            >
                              ✓ {c}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-slate-400 italic">None identified</span>
                        )}
                      </div>
                    </div>

                    <div>
                      <span className="text-xs font-semibold text-slate-600 block mb-1">
                        Missing Concepts:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {conceptsMissing.length > 0 ? (
                          conceptsMissing.map((c, i) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 bg-rose-100 text-rose-800 text-[11px] font-medium rounded-md"
                            >
                              ✗ {c}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-emerald-600 font-medium">All core concepts present</span>
                        )}
                      </div>
                    </div>

                    <div>
                      <span className="text-xs font-semibold text-slate-600 block mb-0.5">
                        AI Rationale:
                      </span>
                      <p className="text-xs text-slate-600 leading-relaxed">
                        {evalItem.rationale}
                      </p>
                    </div>
                  </div>

                  {/* Marks Allocation Section */}
                  <div className="p-4 bg-blue-50/50 rounded-xl border border-blue-200/80 flex items-center justify-between">
                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
                        AI Suggested Marks
                      </span>
                      <span className="text-xl font-bold text-slate-700">
                        {evalItem.suggested_marks.toFixed(1)} / {evalItem.max_marks}
                      </span>
                    </div>

                    <div className="text-right">
                      <span className="text-xs font-bold uppercase tracking-wider text-blue-700 block">
                        Teacher Approved Marks
                      </span>
                      {editingMarksId === evalItem.id ? (
                        <div className="flex items-center gap-2 mt-1">
                          <input
                            type="number"
                            step="0.5"
                            min="0"
                            max={evalItem.max_marks}
                            value={teacherMarks}
                            onChange={(e) => setTeacherMarks(parseFloat(e.target.value) || 0)}
                            className="w-16 px-2 py-1 bg-white border border-blue-400 rounded-lg text-sm text-center font-bold"
                          />
                          <button
                            onClick={() => handleSaveMarks(evalItem.id)}
                            disabled={saving}
                            className="p-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-2xl font-black text-blue-800">
                            {evalItem.approved_marks.toFixed(1)}
                          </span>
                          <button
                            onClick={() => {
                              setEditingMarksId(evalItem.id);
                              setTeacherMarks(evalItem.approved_marks);
                              setTeacherNotes(evalItem.teacher_notes || '');
                            }}
                            className="p-1 text-slate-400 hover:text-blue-600"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
