import React, { useState } from 'react';
import {
  Plus,
  Trash2,
  Check,
  ArrowLeft,
  ArrowRight,
  Upload,
  FileText,
  Image as ImageIcon,
  AlertCircle,
  HelpCircle,
  CheckCircle2,
  ListPlus
} from 'lucide-react';

import { api } from '../services/api';
import type { RubricItem } from '../types';

interface CreateExamProps {
  onExamCreated: (examId: number) => void;
  onCancel: () => void;
}

interface QuestionFormItem {
  question_number: number;
  question_label: string;
  question_type: string;
  question_text: string;
  reference_answer: string;
  max_marks: number;
  essential_keywords: string;
  rubric_criteria: RubricItem[];
  partial_credit_rules: string;
  alternative_answers: string[];
  negative_marking: number;
  source_page?: number;
  crop_path?: string;
}

export const CreateExam: React.FC<CreateExamProps> = ({ onExamCreated, onCancel }) => {
  // Wizard steps: 1 = Exam Meta & Source, 2 = OCR Review, 3 = Marking Scheme, 4 = Final Review
  const [step, setStep] = useState<number>(1);

  // Exam Metadata
  const [title, setTitle] = useState('');
  const [subject, setSubject] = useState('');
  const [classOrBatch, setClassOrBatch] = useState('');

  // Ingestion Mode: 'text' | 'scanned' | 'manual'
  const [inputMethod, setInputMethod] = useState<'text' | 'scanned' | 'manual'>('text');
  const [textKeyInput, setTextKeyInput] = useState(`Q1. Define Operating System and list two of its primary functions.
Answer: An operating system is system software that manages computer hardware and software resources, providing common services for computer programs. Primary functions include process management, memory management, file systems, and hardware abstraction.
[Max Marks: 5]
Keywords: system software, hardware, resource management, memory management, process
Rubric: 2 marks for clear definition; 3 marks for mentioning at least 2 primary functions accurately.

Q2. What is the difference between synchronous and asynchronous transmission?
Answer: In synchronous transmission, data is transmitted in blocks or frames synchronized by an external clock signal. In asynchronous transmission, data is sent byte-by-byte using start and stop bits without a shared clock.
[Max Marks: 5]
Keywords: clock signal, start bit, stop bit, frames, synchronous, asynchronous
Rubric: 2.5 marks for clock synchronization vs start/stop bits; 2.5 marks for data units (frames vs bytes).`);

  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionStatus, setExtractionStatus] = useState('');
  const [unparsedText, setUnparsedText] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Questions State
  const [questions, setQuestions] = useState<QuestionFormItem[]>([]);

  // Step 1: Trigger Answer Key Extraction
  const handleIngestAnswerKey = async () => {
    setError(null);
    if (!title.trim() || !subject.trim() || !classOrBatch.trim()) {
      setError('Please provide Exam Title, Subject, and Class/Batch.');
      return;
    }

    if (inputMethod === 'manual') {
      // Initialize with 1 blank question
      setQuestions([
        {
          question_number: 1,
          question_label: 'Q1',
          question_type: 'subjective',
          question_text: '',
          reference_answer: '',
          max_marks: 5,
          essential_keywords: '',
          rubric_criteria: [
            { criterion: 'Core definition and conceptual accuracy', marks: 2.5 },
            { criterion: 'Explanation, mechanism, and examples', marks: 2.5 }
          ],
          partial_credit_rules: 'Award partial marks based on percentage of essential concepts addressed.',
          alternative_answers: [],
          negative_marking: 0.0,
        }
      ]);
      setStep(2);
      return;
    }

    try {
      setIsExtracting(true);
      if (inputMethod === 'text') {
        setExtractionStatus('Parsing text-based answer key...');
        const res = await api.parseTextAnswerKey(uploadedFile || undefined, textKeyInput);
        setQuestions(res.questions.map((q) => ({
          ...q,
          question_type: q.question_type || 'subjective',
          rubric_criteria: q.rubric_criteria || [
            { criterion: 'Core conceptual accuracy', marks: Math.round(q.max_marks / 2) },
            { criterion: 'Detailed explanation and examples', marks: Math.round(q.max_marks / 2) }
          ],
          partial_credit_rules: q.partial_credit_rules || '',
          alternative_answers: q.alternative_answers || [],
          negative_marking: q.negative_marking || 0.0
        })));
        setUnparsedText(res.unparsed_text);
        setStep(2);
      } else if (inputMethod === 'scanned') {
        if (!uploadedFile) {
          setError('Please choose a scanned answer key file (PDF, JPG, or PNG).');
          setIsExtracting(false);
          return;
        }
        setExtractionStatus('Rendering pages and performing TrOCR handwriting recognition...');
        const res = await api.parseScannedAnswerKey(uploadedFile);
        setQuestions(res.questions.map((q) => ({
          ...q,
          question_type: q.question_type || 'subjective',
          rubric_criteria: q.rubric_criteria || [
            { criterion: 'Accurate definition', marks: Math.round(q.max_marks / 2) },
            { criterion: 'Technical explanation', marks: Math.round(q.max_marks / 2) }
          ],
          partial_credit_rules: '',
          alternative_answers: [],
          negative_marking: 0.0
        })));
        setUnparsedText(res.unparsed_text);
        setStep(2);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Extraction failed. Please verify file format.');
    } finally {
      setIsExtracting(false);
      setExtractionStatus('');
    }
  };

  // Question manipulation
  const updateQuestion = (idx: number, field: keyof QuestionFormItem, val: any) => {
    const updated = [...questions];
    updated[idx] = { ...updated[idx], [field]: val };
    setQuestions(updated);
  };

  const addQuestion = () => {
    const nextNum = questions.length + 1;
    setQuestions([
      ...questions,
      {
        question_number: nextNum,
        question_label: `Q${nextNum}`,
        question_type: 'subjective',
        question_text: '',
        reference_answer: '',
        max_marks: 5,
        essential_keywords: '',
        rubric_criteria: [
          { criterion: 'Core definition and accuracy', marks: 2.5 },
          { criterion: 'Explanation and application', marks: 2.5 }
        ],
        partial_credit_rules: '',
        alternative_answers: [],
        negative_marking: 0.0
      }
    ]);
  };

  const removeQuestion = (idx: number) => {
    if (questions.length <= 1) return;
    const updated = questions.filter((_, i) => i !== idx).map((q, i) => ({
      ...q,
      question_number: i + 1,
      question_label: q.question_label.startsWith('Q') ? `Q${i + 1}` : q.question_label
    }));
    setQuestions(updated);
  };

  // Rubric manipulation per question
  const addRubricCriterion = (qIdx: number) => {
    const q = questions[qIdx];
    const newCriteria = [...q.rubric_criteria, { criterion: 'Additional evaluation point', marks: 1.0 }];
    updateQuestion(qIdx, 'rubric_criteria', newCriteria);
  };

  const updateRubricCriterion = (qIdx: number, cIdx: number, field: keyof RubricItem, val: any) => {
    const q = questions[qIdx];
    const newCriteria = [...q.rubric_criteria];
    newCriteria[cIdx] = { ...newCriteria[cIdx], [field]: val };
    updateQuestion(qIdx, 'rubric_criteria', newCriteria);
  };

  const removeRubricCriterion = (qIdx: number, cIdx: number) => {
    const q = questions[qIdx];
    if (q.rubric_criteria.length <= 1) return;
    const newCriteria = q.rubric_criteria.filter((_, i) => i !== cIdx);
    updateQuestion(qIdx, 'rubric_criteria', newCriteria);
  };

  // Validation before proceeding
  const validateQuestionsReview = () => {
    setError(null);
    if (!questions || questions.length === 0) {
      setError('No valid questions detected in answer key. Please enter or upload questions.');
      return false;
    }
    for (const q of questions) {
      if (!q.reference_answer || !q.reference_answer.trim()) {
        setError(`Question ${q.question_label || q.question_number} is missing a reference answer.`);
        return false;
      }
    }
    return true;
  };

  const validateMarkingScheme = () => {
    setError(null);
    const seen = new Set<string>();

    for (const q of questions) {
      const lbl = (q.question_label || `Q${q.question_number}`).trim().toUpperCase();
      if (seen.has(lbl)) {
        setError(`Duplicate question identifier detected: '${lbl}'. Please ensure all question identifiers are distinct.`);
        return false;
      }
      seen.add(lbl);

      if (q.max_marks <= 0) {
        setError(`Question ${lbl} must have maximum marks greater than 0.`);
        return false;
      }

      // Check sum of rubric criteria (for subjective questions with multiple criteria)
      if (q.question_type !== 'mcq' && q.rubric_criteria && q.rubric_criteria.length > 0) {
        const sumMarks = q.rubric_criteria.reduce((s, c) => s + (Number(c.marks) || 0), 0);
        if (sumMarks > q.max_marks + 0.05) {
          setError(
            `Sum of rubric criteria (${sumMarks} marks) exceeds Question ${lbl} Maximum Marks (${q.max_marks} marks). Please adjust criteria marks.`
          );
          return false;
        }
      }
    }
    return true;
  };

  // Final Submit to Backend
  const handleFinalSubmit = async () => {
    if (!validateMarkingScheme()) return;

    try {
      setIsExtracting(true);
      setError(null);

      const payload = {
        title,
        subject,
        class_or_batch: classOrBatch,
        questions: questions.map((q) => ({
          question_number: q.question_number,
          question_label: q.question_label || `Q${q.question_number}`,
          question_type: q.question_type || 'subjective',
          question_text: q.question_text || `Question ${q.question_number}`,
          reference_answer: q.reference_answer,
          max_marks: Number(q.max_marks),
          essential_keywords: q.essential_keywords,
          rubric_criteria: JSON.stringify(q.rubric_criteria),
          partial_credit_rules: q.partial_credit_rules,
          alternative_answers: JSON.stringify(q.alternative_answers),
          negative_marking: Number(q.negative_marking) || 0.0
        }))
      };

      const res = await api.createExam(payload);
      onExamCreated(res.id);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save examination.');
    } finally {
      setIsExtracting(false);
    }
  };

  const totalExamMarks = questions.reduce((sum, q) => sum + (Number(q.max_marks) || 0), 0);

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-fade-in pb-16">
      {/* Top Header & Step Breadcrumbs */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <button
          onClick={onCancel}
          className="text-sm font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1.5 transition"
        >
          <ArrowLeft className="w-4 h-4" /> Cancel & Exit
        </button>

        <div className="flex items-center gap-2 text-xs font-semibold">
          <span
            className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 ${
              step === 1 ? 'bg-blue-600 text-white shadow-sm' : 'bg-slate-200 text-slate-700'
            }`}
          >
            1. Ingest Answer Key
          </span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
          <span
            className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 ${
              step === 2 ? 'bg-blue-600 text-white shadow-sm' : 'bg-slate-200 text-slate-700'
            }`}
          >
            2. Review OCR & Q&A
          </span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
          <span
            className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 ${
              step === 3 ? 'bg-blue-600 text-white shadow-sm' : 'bg-slate-200 text-slate-700'
            }`}
          >
            3. Marking Scheme
          </span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
          <span
            className={`px-3 py-1.5 rounded-xl flex items-center gap-1.5 ${
              step === 4 ? 'bg-blue-600 text-white shadow-sm' : 'bg-slate-200 text-slate-700'
            }`}
          >
            4. Approve Exam
          </span>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* STEP 1: Exam Metadata & Ingestion Source */}
      {step === 1 && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 sm:p-8 space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Create Examination Paper</h2>
            <p className="text-sm text-slate-500 mt-1">
              Provide exam details, then supply the answer key via text-based upload, scanned handwritten document, or manual entry.
            </p>
          </div>

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

          {/* Answer Key Input Selection (Feature A) */}
          <div className="border-t border-slate-200 pt-6 space-y-4">
            <label className="block text-sm font-bold text-slate-900">
              Select Answer Key Input Method
            </label>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div
                onClick={() => setInputMethod('text')}
                className={`p-5 rounded-2xl border-2 cursor-pointer transition ${
                  inputMethod === 'text'
                    ? 'border-blue-600 bg-blue-50/50 text-blue-950 shadow-sm'
                    : 'border-slate-200 bg-white hover:border-slate-300 text-slate-700'
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-xl bg-blue-100 text-blue-700">
                    <FileText className="w-5 h-5" />
                  </div>
                  <h4 className="font-bold text-sm">Option 1: Text-Based Key</h4>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Paste structured questions and answers or upload `.txt`, `.docx`, or text-based `.pdf`.
                </p>
              </div>

              <div
                onClick={() => setInputMethod('scanned')}
                className={`p-5 rounded-2xl border-2 cursor-pointer transition ${
                  inputMethod === 'scanned'
                    ? 'border-blue-600 bg-blue-50/50 text-blue-950 shadow-sm'
                    : 'border-slate-200 bg-white hover:border-slate-300 text-slate-700'
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-xl bg-indigo-100 text-indigo-700">
                    <ImageIcon className="w-5 h-5" />
                  </div>
                  <h4 className="font-bold text-sm">Option 2: Scanned Key</h4>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Upload educator's scanned handwritten answer sheet (PDF/JPG/PNG) with TrOCR handwriting recognition.
                </p>
              </div>

              <div
                onClick={() => setInputMethod('manual')}
                className={`p-5 rounded-2xl border-2 cursor-pointer transition ${
                  inputMethod === 'manual'
                    ? 'border-blue-600 bg-blue-50/50 text-blue-950 shadow-sm'
                    : 'border-slate-200 bg-white hover:border-slate-300 text-slate-700'
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-xl bg-slate-100 text-slate-700">
                    <ListPlus className="w-5 h-5" />
                  </div>
                  <h4 className="font-bold text-sm">Manual Direct Entry</h4>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Type questions, reference answers, and marking rubrics from scratch in the form.
                </p>
              </div>
            </div>

            {/* Sub-interface for Option 1: Text-based */}
            {inputMethod === 'text' && (
              <div className="mt-4 p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Answer Key Text (Direct Entry or File Upload)
                  </span>
                  <label className="cursor-pointer text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1">
                    <Upload className="w-3.5 h-3.5" /> Upload .txt / .csv / .docx / .pdf
                    <input
                      type="file"
                      accept=".txt,.csv,.tsv,.docx,.pdf"
                      className="hidden"
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          setUploadedFile(e.target.files[0]);
                        }
                      }}
                    />
                  </label>
                </div>

                {uploadedFile && (
                  <div className="p-3 bg-white rounded-xl border border-slate-200 flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-800">Selected file: {uploadedFile.name}</span>
                    <button
                      onClick={() => setUploadedFile(null)}
                      className="text-red-600 hover:text-red-800 font-semibold"
                    >
                      Remove
                    </button>
                  </div>
                )}

                <textarea
                  rows={8}
                  value={textKeyInput}
                  onChange={(e) => setTextKeyInput(e.target.value)}
                  placeholder={`Format A (Structured Text):
Q1. Define Operating System and list two functions.
Answer: An operating system is system software that manages hardware resources...
[Max Marks: 5]
Keywords: system software, hardware, resource management
Rubric: 2 marks for definition; 3 marks for functions

Or Format B (CSV answer keys):
Question_Number,Type,Correct_Answer
1,MCQ,B
21,Short_Answer,"A type of ML where the model is trained on labeled data..."`}
                  className="w-full p-3.5 bg-white border border-slate-300 rounded-xl text-xs font-mono focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            )}

            {/* Sub-interface for Option 2: Scanned handwritten */}
            {inputMethod === 'scanned' && (
              <div className="mt-4 p-6 rounded-2xl bg-indigo-50/50 border border-indigo-200 space-y-4 text-center">
                <input
                  type="file"
                  id="scanned-key-upload"
                  accept=".pdf,.jpg,.jpeg,.png"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setUploadedFile(e.target.files[0]);
                    }
                  }}
                />
                <label htmlFor="scanned-key-upload" className="cursor-pointer block">
                  {uploadedFile ? (
                    <div className="flex flex-col items-center">
                      <FileText className="w-10 h-10 text-indigo-600 mb-2" />
                      <span className="font-semibold text-slate-800 text-sm">{uploadedFile.name}</span>
                      <span className="text-xs text-slate-500 mt-0.5">
                        {(uploadedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready for OCR extraction
                      </span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center">
                      <Upload className="w-10 h-10 text-indigo-400 mb-2" />
                      <span className="font-semibold text-indigo-950 text-sm">
                        Upload Scanned Handwritten Answer Key (PDF / JPG / PNG)
                      </span>
                      <span className="text-xs text-indigo-700/70 mt-1">
                        TrOCR will read page handwriting blocks and extract structured Q&A records.
                      </span>
                    </div>
                  )}
                </label>
              </div>
            )}

            {isExtracting && (
              <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 text-blue-800 text-sm flex items-center gap-3">
                <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-600 border-t-transparent" />
                <span className="font-semibold">{extractionStatus}</span>
              </div>
            )}

            <div className="pt-4 flex justify-end">
              <button
                type="button"
                onClick={handleIngestAnswerKey}
                disabled={isExtracting}
                className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl shadow-md transition flex items-center gap-2 disabled:opacity-50"
              >
                <span>Continue to OCR & Question Review</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 2: Extraction & OCR Review */}
      {step === 2 && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 sm:p-8 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Review & Correct Extracted Q&A</h2>
              <p className="text-sm text-slate-500 mt-1">
                Inspect extracted question prompts and reference answers. Correct OCR transcription errors before configuring the marking scheme.
              </p>
            </div>

            <button
              type="button"
              onClick={addQuestion}
              className="px-3.5 py-2 bg-blue-50 text-blue-700 hover:bg-blue-100 font-semibold text-xs rounded-xl flex items-center gap-1.5 transition"
            >
              <Plus className="w-4 h-4" /> Add Question
            </button>
          </div>

          {unparsedText && (
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-1">
              <div className="font-bold flex items-center gap-1.5">
                <HelpCircle className="w-4 h-4 text-amber-600" /> Unparsed Content Detected
              </div>
              <p className="text-slate-600">
                The following text could not be unambiguously assigned to a question. You can copy it into any question below:
              </p>
              <pre className="p-2 bg-white/80 rounded border border-amber-200 overflow-x-auto whitespace-pre-wrap font-mono">
                {unparsedText}
              </pre>
            </div>
          )}

          <div className="space-y-6">
            {questions.map((q, idx) => (
              <div
                key={idx}
                className="p-5 rounded-2xl border border-slate-200 bg-slate-50/50 space-y-4 relative"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-sm text-slate-700 bg-white px-3 py-1 rounded-lg border border-slate-200">
                      #{q.question_number}
                    </span>
                    <input
                      type="text"
                      placeholder="Label e.g. Q1, 1(a)"
                      value={q.question_label}
                      onChange={(e) => updateQuestion(idx, 'question_label', e.target.value)}
                      className="w-24 px-2 py-1 bg-white border border-slate-300 rounded-lg text-xs font-bold text-blue-700 uppercase"
                    />
                    <select
                      value={q.question_type || 'subjective'}
                      onChange={(e) => updateQuestion(idx, 'question_type', e.target.value)}
                      className="px-2.5 py-1 bg-white border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    >
                      <option value="subjective">Subjective / Short Answer</option>
                      <option value="mcq">Multiple Choice (MCQ)</option>
                    </select>
                    <div className="flex items-center gap-1.5 ml-2">
                      <label className="text-xs font-semibold text-slate-600">Max Marks:</label>
                      <input
                        type="number"
                        min="0.5"
                        max="100"
                        step="0.5"
                        value={q.max_marks}
                        onChange={(e) => updateQuestion(idx, 'max_marks', parseFloat(e.target.value) || 0)}
                        className="w-16 px-2 py-1 bg-white border border-slate-300 rounded-lg text-xs font-bold text-blue-700 text-center"
                      />
                    </div>
                    {q.source_page && (
                      <span className="text-[11px] px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded font-medium">
                        Page {q.source_page}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
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
                    Question Prompt / Statement
                  </label>
                  <textarea
                    rows={2}
                    value={q.question_text}
                    onChange={(e) => updateQuestion(idx, 'question_text', e.target.value)}
                    placeholder="Enter question statement..."
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    {q.question_type === 'mcq' ? 'Reference Option (e.g. A, B, C, D)' : 'Reference Answer (Model Answer)'}
                  </label>
                  <textarea
                    rows={q.question_type === 'mcq' ? 1 : 3}
                    value={q.reference_answer}
                    onChange={(e) => updateQuestion(idx, 'reference_answer', e.target.value)}
                    placeholder={q.question_type === 'mcq' ? 'e.g. B' : 'Extracted reference answer text...'}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    required
                  />
                </div>

                {q.question_type !== 'mcq' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">Keywords</label>
                      <input
                        type="text"
                        value={q.essential_keywords}
                        onChange={(e) => updateQuestion(idx, 'essential_keywords', e.target.value)}
                        placeholder="Comma-separated keywords"
                        className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-600 mb-1">
                        Marking Rubric ({q.rubric_criteria?.length || 0} criteria)
                      </label>
                      <div className="text-xs text-slate-600 py-1.5 px-3 bg-white border border-slate-200 rounded-lg truncate">
                        {q.rubric_criteria && q.rubric_criteria.length > 0
                          ? q.rubric_criteria.map((c) => `${c.criterion} (${c.marks}m)`).join('; ')
                          : 'Configurable in next step'}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="pt-4 flex justify-between">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="px-5 py-2.5 rounded-xl border border-slate-300 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              Back
            </button>
            <button
              type="button"
              onClick={() => {
                if (validateQuestionsReview()) setStep(3);
              }}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl shadow-md transition flex items-center gap-2"
            >
              <span>Configure Marking Scheme</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: Question-Wise Marking Scheme Configuration (Feature B) */}
      {step === 3 && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 sm:p-8 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
                Question-Wise Marking Scheme Configuration
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                Configure maximum marks, essential concepts, detailed rubric criteria, and acceptable alternative answers.
              </p>
            </div>

            <div className="px-4 py-2 bg-blue-50 rounded-xl border border-blue-200 text-blue-900 text-sm font-bold">
              Total Examination Marks: <span className="text-blue-600 text-lg">{totalExamMarks}</span>
            </div>
          </div>

          <div className="space-y-8">
            {questions.map((q, qIdx) => {
              const rubricSum = q.rubric_criteria.reduce((s, c) => s + (Number(c.marks) || 0), 0);
              const isOverAllocated = rubricSum > q.max_marks;

              return (
                <div
                  key={qIdx}
                  className="p-6 rounded-2xl border border-slate-200 bg-slate-50/40 space-y-5"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
                    <div>
                      <span className="font-extrabold text-base text-slate-900">
                        {q.question_label || `Question ${q.question_number}`}
                      </span>
                      <p className="text-xs text-slate-500 line-clamp-1">{q.question_text}</p>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1.5">
                        <label className="text-xs font-bold text-slate-600">Max Marks:</label>
                        <input
                          type="number"
                          min="1"
                          max="100"
                          step="0.5"
                          value={q.max_marks}
                          onChange={(e) => updateQuestion(qIdx, 'max_marks', parseFloat(e.target.value) || 0)}
                          className="w-16 px-2 py-1 bg-white border border-slate-300 rounded-lg text-sm text-center font-bold text-blue-700"
                        />
                      </div>

                      <div className="flex items-center gap-1.5">
                        <label className="text-xs font-bold text-slate-600">Penalty / Negative (optional):</label>
                        <input
                          type="number"
                          min="0"
                          max="5"
                          step="0.25"
                          value={q.negative_marking}
                          onChange={(e) => updateQuestion(qIdx, 'negative_marking', parseFloat(e.target.value) || 0)}
                          className="w-16 px-2 py-1 bg-white border border-slate-300 rounded-lg text-xs text-center font-bold text-red-600"
                        />
                      </div>
                    </div>
                  </div>

                  {q.question_type === 'mcq' ? (
                    <div className="p-4 bg-blue-50/70 rounded-xl border border-blue-200 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <span className="px-3 py-1 bg-blue-600 text-white font-bold rounded-lg text-sm uppercase">
                          Option {q.reference_answer.trim().toUpperCase()}
                        </span>
                        <span className="text-xs text-slate-700">
                          Multiple Choice Question: Evaluated by exact matching of detected option letter against reference option.
                        </span>
                      </div>
                      <div className="text-xs font-semibold text-blue-900">
                        Awards {q.max_marks} marks if correct{q.negative_marking > 0 ? `, -${q.negative_marking} penalty if incorrect` : ''}
                      </div>
                    </div>
                  ) : (
                    <>
                      {/* Essential Keywords & Partial Credit */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                            Essential Keywords & Concepts
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. process management, hardware abstraction, kernel"
                            value={q.essential_keywords}
                            onChange={(e) => updateQuestion(qIdx, 'essential_keywords', e.target.value)}
                            className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                          />
                          <span className="text-[11px] text-slate-400">Comma-separated key terms</span>
                        </div>

                        <div>
                          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                            Acceptable Alternative Answers
                          </label>
                          <input
                            type="text"
                            placeholder="Alternative valid solutions or synonyms (semicolon-separated)"
                            value={Array.isArray(q.alternative_answers) ? q.alternative_answers.join('; ') : q.alternative_answers}
                            onChange={(e) =>
                              updateQuestion(
                                qIdx,
                                'alternative_answers',
                                e.target.value.split(';').map((s) => s.trim()).filter(Boolean)
                              )
                            }
                            className="w-full px-3 py-2 bg-white border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                          />
                          <span className="text-[11px] text-slate-400">Alternative phrasings accepted for full credit</span>
                        </div>
                      </div>

                      {/* Rubric Criteria Table */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                              Marking Rubric Criteria Breakdown
                            </span>
                            <span
                              className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                                isOverAllocated
                                  ? 'bg-red-100 text-red-800'
                                  : rubricSum === q.max_marks
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : 'bg-blue-100 text-blue-800'
                              }`}
                            >
                              Sum: {rubricSum} / {q.max_marks} marks
                            </span>
                          </div>

                          <button
                            type="button"
                            onClick={() => addRubricCriterion(qIdx)}
                            className="text-xs text-blue-600 hover:text-blue-800 font-bold flex items-center gap-1"
                          >
                            <Plus className="w-3.5 h-3.5" /> Add Criterion
                          </button>
                        </div>

                        <div className="space-y-2">
                          {q.rubric_criteria.map((c, cIdx) => (
                            <div key={cIdx} className="flex items-center gap-2 bg-white p-2.5 rounded-xl border border-slate-200">
                              <input
                                type="text"
                                value={c.criterion}
                                onChange={(e) => updateRubricCriterion(qIdx, cIdx, 'criterion', e.target.value)}
                                placeholder="Criterion description..."
                                className="flex-1 px-2.5 py-1 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                              />
                              <div className="flex items-center gap-1">
                                <span className="text-xs text-slate-500">Marks:</span>
                                <input
                                  type="number"
                                  min="0.5"
                                  max={q.max_marks}
                                  step="0.5"
                                  value={c.marks}
                                  onChange={(e) =>
                                    updateRubricCriterion(qIdx, cIdx, 'marks', parseFloat(e.target.value) || 0)
                                  }
                                  className="w-14 px-2 py-1 text-xs font-bold text-center border border-slate-200 rounded-lg"
                                />
                              </div>
                              {q.rubric_criteria.length > 1 && (
                                <button
                                  type="button"
                                  onClick={() => removeRubricCriterion(qIdx, cIdx)}
                                  className="p-1 text-slate-400 hover:text-red-500"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>

          <div className="pt-4 flex justify-between">
            <button
              type="button"
              onClick={() => setStep(2)}
              className="px-5 py-2.5 rounded-xl border border-slate-300 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              Back
            </button>
            <button
              type="button"
              onClick={() => {
                if (validateMarkingScheme()) setStep(4);
              }}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl shadow-md transition flex items-center gap-2"
            >
              <span>Review & Finalize Examination</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: Final Summary & Persistence */}
      {step === 4 && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 sm:p-8 space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Approve Examination & Save</h2>
              <p className="text-sm text-slate-500">
                Confirm your examination configuration. All questions, criteria, and reference answers will be persisted into the database.
              </p>
            </div>
          </div>

          {/* Exam Summary Banner */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div>
              <span className="text-xs uppercase font-bold text-slate-400 block">Exam Title</span>
              <span className="font-bold text-slate-800 text-sm">{title}</span>
            </div>
            <div>
              <span className="text-xs uppercase font-bold text-slate-400 block">Subject</span>
              <span className="font-bold text-slate-800 text-sm">{subject}</span>
            </div>
            <div>
              <span className="text-xs uppercase font-bold text-slate-400 block">Batch</span>
              <span className="font-bold text-slate-800 text-sm">{classOrBatch}</span>
            </div>
            <div>
              <span className="text-xs uppercase font-bold text-slate-400 block">Total Marks</span>
              <span className="font-extrabold text-blue-600 text-base">{totalExamMarks} Marks</span>
            </div>
          </div>

          {/* Questions summary preview */}
          <div className="divide-y divide-slate-100">
            {questions.map((q, i) => (
              <div key={i} className="py-4 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-slate-900">
                    {q.question_label || `Question #${q.question_number}`} — {q.max_marks} marks
                  </span>
                  <span className="text-xs text-slate-500 font-medium">
                    {q.rubric_criteria.length} criteria configured
                  </span>
                </div>
                <p className="text-xs text-slate-600 italic">Q: {q.question_text}</p>
                <p className="text-xs text-slate-500">Ref: {q.reference_answer}</p>
              </div>
            ))}
          </div>

          <div className="pt-4 flex justify-between">
            <button
              type="button"
              onClick={() => setStep(3)}
              className="px-5 py-2.5 rounded-xl border border-slate-300 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              Back to Marking Scheme
            </button>
            <button
              type="button"
              onClick={handleFinalSubmit}
              disabled={isExtracting}
              className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold rounded-xl shadow-md transition flex items-center gap-2 disabled:opacity-50"
            >
              <Check className="w-4 h-4" /> Save & Finalize Exam
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
