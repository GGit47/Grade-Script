import React, { useState, useEffect } from 'react';
import {
  Check,
  AlertTriangle,
  Download,
  Edit2,
  Save,
  FileCheck,
  ArrowLeft,
  Shuffle,
  CheckCircle2,
  XCircle
} from 'lucide-react';

import { api } from '../services/api';
import type { SubmissionDetail, Exam, CandidateMatch, RubricScoreItem } from '../types';

interface EvaluationReviewProps {
  submissionId: number;
  onBack: () => void;
}

export const EvaluationReview: React.FC<EvaluationReviewProps> = ({
  submissionId,
  onBack,
}) => {
  const [submission, setSubmission] = useState<SubmissionDetail | null>(null);
  const [exam, setExam] = useState<Exam | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit Transcription state
  const [editingRegionId, setEditingRegionId] = useState<number | null>(null);
  const [editText, setEditText] = useState('');

  // Remap Question state
  const [remappingRegionId, setRemappingRegionId] = useState<number | null>(null);
  const [selectedRemapQuestionId, setSelectedRemapQuestionId] = useState<number | null>(null);

  // Edit Marks state
  const [editingMarksId, setEditingMarksId] = useState<number | null>(null);
  const [teacherMarks, setTeacherMarks] = useState<number>(0);
  const [teacherNotes, setTeacherNotes] = useState<string>('');
  const [saving, setSaving] = useState(false);

  const fetchSubmission = async () => {
    try {
      setLoading(true);
      const data = await api.getSubmission(submissionId);
      setSubmission(data);
      if (data.exam_id) {
        const examData = await api.getExam(data.exam_id);
        setExam(examData);
      }
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

  const handleRemapQuestion = async (regionId: number) => {
    try {
      setSaving(true);
      await api.remapRegion(regionId, { question_id: selectedRemapQuestionId });
      setRemappingRegionId(null);
      await fetchSubmission();
    } catch (err) {
      alert('Failed to remap answer region.');
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

  // Calculate intelligent mapping statistics
  const totalRegions = submission.pages.reduce((acc, p) => acc + p.regions.length, 0);
  const ambiguousRegions = submission.pages.flatMap((p) => p.regions).filter((r) => r.is_ambiguous);
  const unansweredEvals = submission.evaluations.filter((e) => !e.region_id);
  const duplicateRegions = submission.pages
    .flatMap((p) => p.regions)
    .filter((r) => r.mapping_method === 'duplicate_detected');

  return (
    <div className="space-y-6 pb-20 animate-fade-in">
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

      {/* Feature C: Intelligent Answer Mapping Status Banner */}
      <div className="p-4 rounded-2xl bg-gradient-to-r from-slate-900 to-indigo-950 text-white shadow-md flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-500/20 text-indigo-300 rounded-xl">
            <Shuffle className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold tracking-tight">Intelligent Answer-to-Question Mapping</h4>
            <p className="text-xs text-slate-300">
              Answers are matched to reference questions regardless of submission order using explicit labels, prompts, and semantic compatibility.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <span className="px-3 py-1 bg-white/10 rounded-lg">
            Total Answer Blocks: <strong>{totalRegions}</strong>
          </span>
          {ambiguousRegions.length > 0 && (
            <span className="px-3 py-1 bg-amber-500/30 text-amber-200 border border-amber-400/40 rounded-lg font-semibold flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5" /> {ambiguousRegions.length} Ambiguous / Check Needed
            </span>
          )}
          {duplicateRegions.length > 0 && (
            <span className="px-3 py-1 bg-rose-500/30 text-rose-200 border border-rose-400/40 rounded-lg font-semibold flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5" /> {duplicateRegions.length} Duplicate Answers
            </span>
          )}
          {unansweredEvals.length > 0 && (
            <span className="px-3 py-1 bg-slate-700/50 text-slate-300 rounded-lg">
              {unansweredEvals.length} Unanswered Question(s)
            </span>
          )}
        </div>
      </div>

      {/* Answer Region & Question Evaluation Cards */}
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

          const rubricScores: RubricScoreItem[] = evalItem.rubric_scores
            ? JSON.parse(evalItem.rubric_scores)
            : [];

          const candidateMatches: CandidateMatch[] = region?.candidate_matches
            ? JSON.parse(region.candidate_matches)
            : [];

          // Find mapped question details
          const mappedQ = exam?.questions?.find((q) => q.id === evalItem.question_id);
          const qLabel = mappedQ?.question_label || `Q${evalItem.question_id}`;

          return (
            <div
              key={evalItem.id}
              className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden"
            >
              {/* Card Header with Question & Mapping Info */}
              <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="w-7 h-7 rounded-lg bg-blue-600 text-white text-xs flex items-center justify-center font-extrabold shadow-sm">
                    {index + 1}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-extrabold text-slate-900 text-sm">
                        {qLabel}: {mappedQ?.question_text || `Question #${index + 1}`}
                      </span>

                      {/* Mapping Confidence Badge */}
                      {region && (
                        <span
                          className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                            region.is_manually_mapped
                              ? 'bg-purple-100 text-purple-800'
                              : region.is_ambiguous
                              ? 'bg-amber-100 text-amber-800 border border-amber-300'
                              : region.mapping_method === 'explicit_label'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          {region.is_manually_mapped
                            ? 'Teacher Remapped'
                            : region.is_ambiguous
                            ? '⚠️ Ambiguous Mapping'
                            : region.mapping_method === 'explicit_label'
                            ? `✓ Explicit Label (${region.detected_question_label || 'Matched'})`
                            : `Semantic Match (${(region.mapping_confidence * 100).toFixed(0)}%)`}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {evalItem.review_needed && (
                    <span className="px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 text-xs font-semibold flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" /> Review Needed
                    </span>
                  )}
                  <span className="text-xs text-slate-500 font-medium">
                    Max Marks: <strong>{evalItem.max_marks}</strong>
                  </span>
                </div>
              </div>

              <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left: Scanned Image Crop, Detected Identifiers & Transcription */}
                <div className="space-y-4 border-r border-slate-100 pr-0 lg:pr-6">
                  {/* Intelligent Mapping & Re-mapping Controls */}
                  {region && (
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-700 flex items-center gap-1">
                          <Shuffle className="w-3.5 h-3.5 text-blue-600" />
                          Mapping: {region.detected_question_label ? `Detected '${region.detected_question_label}'` : 'Inferred via AI'}
                        </span>

                        {remappingRegionId !== region.id ? (
                          <button
                            onClick={() => {
                              setRemappingRegionId(region.id);
                              setSelectedRemapQuestionId(region.question_id || null);
                            }}
                            className="text-blue-600 hover:text-blue-800 font-bold flex items-center gap-1"
                          >
                            <Shuffle className="w-3 h-3" /> Re-map Question
                          </button>
                        ) : null}
                      </div>

                      {/* Remap Dropdown Selection */}
                      {remappingRegionId === region.id && (
                        <div className="mt-2 p-3 bg-white rounded-xl border border-blue-400 space-y-2">
                          <label className="block text-[11px] font-bold uppercase text-slate-600">
                            Assign this answer block to:
                          </label>
                          <select
                            value={selectedRemapQuestionId || ''}
                            onChange={(e) => setSelectedRemapQuestionId(e.target.value ? Number(e.target.value) : null)}
                            className="w-full p-2 text-xs border border-slate-300 rounded-lg bg-white font-medium"
                          >
                            <option value="">-- Unmatched / Ignored --</option>
                            {exam?.questions?.map((q) => (
                              <option key={q.id} value={q.id}>
                                {q.question_label || `Q${q.question_number}`}: {q.question_text.slice(0, 45)}...
                              </option>
                            ))}
                          </select>
                          <div className="flex justify-end gap-2 pt-1">
                            <button
                              onClick={() => setRemappingRegionId(null)}
                              className="px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => handleRemapQuestion(region.id)}
                              disabled={saving}
                              className="px-3 py-1 text-xs bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700"
                            >
                              Confirm & Regrade
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Candidate Match Scores */}
                      {candidateMatches.length > 1 && (
                        <div className="pt-1 border-t border-slate-200/60 text-[11px] text-slate-500">
                          <span className="font-semibold block mb-0.5">Alternative Candidate Matches:</span>
                          <div className="space-y-0.5">
                            {candidateMatches.slice(0, 3).map((cand, ci) => (
                              <div key={ci} className="flex items-center justify-between">
                                <span>{cand.question_label}: {cand.reason}</span>
                                <span className="font-bold text-slate-700">{(cand.score * 100).toFixed(0)}%</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Scanned Crop */}
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
                      <div className="h-28 border border-dashed border-slate-200 rounded-xl flex items-center justify-center text-xs text-slate-400">
                        Unanswered question / No handwritten region mapped
                      </div>
                    )}
                  </div>

                  {/* OCR Transcription & Inline Editing */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                        TrOCR Extracted Transcription
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
                        "{evalItem.transcribed_answer || '[No answer written]'}"
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

                    {/* Rubric Breakdown List (Feature B) */}
                    {rubricScores.length > 0 && (
                      <div>
                        <span className="text-xs font-semibold text-slate-600 block mb-1">
                          Rubric Criteria Breakdown:
                        </span>
                        <div className="space-y-1">
                          {rubricScores.map((rb, rIdx) => (
                            <div
                              key={rIdx}
                              className="flex items-center justify-between text-xs bg-white p-2 rounded-lg border border-slate-200"
                            >
                              <div className="flex items-center gap-1.5">
                                {rb.satisfied ? (
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                                ) : (
                                  <XCircle className="w-3.5 h-3.5 text-rose-500 flex-shrink-0" />
                                )}
                                <span className="text-slate-700">{rb.criterion}</span>
                              </div>
                              <span className="font-bold text-slate-800">
                                {rb.awarded_marks} / {rb.max_marks} marks
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

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
