import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, ArrowLeft } from 'lucide-react';
import { api } from '../services/api';
import type { Exam } from '../types';

interface UploadSheetProps {
  exams: Exam[];
  preselectedExamId?: number;
  onUploaded: (submissionId: number) => void;
  onCancel: () => void;
}

export const UploadSheet: React.FC<UploadSheetProps> = ({
  exams,
  preselectedExamId,
  onUploaded,
  onCancel,
}) => {
  const [examId, setExamId] = useState<number>(preselectedExamId || (exams[0]?.id ?? 0));
  const [rollNo, setRollNo] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      const validTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
      if (!validTypes.includes(selected.type)) {
        setError('Invalid file type. Please upload a PDF, JPG, or PNG document.');
        return;
      }
      if (selected.size > 20 * 1024 * 1024) {
        setError('File size exceeds the 20MB limit.');
        return;
      }

      setError(null);
      setFile(selected);
      if (selected.type.startsWith('image/')) {
        setPreviewUrl(URL.createObjectURL(selected));
      } else {
        setPreviewUrl(null);
      }
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!examId) {
      setError('Please select an examination.');
      return;
    }
    if (!rollNo.trim()) {
      setError('Please enter the student roll number / registration ID.');
      return;
    }
    if (!file) {
      setError('Please select an answer sheet file.');
      return;
    }

    try {
      setUploading(true);
      setError(null);
      setUploadStep('Uploading file & rendering pages...');

      const submission = await api.uploadSubmission(examId, rollNo.trim(), file);
      setUploadStep('Preprocessing image and running deep learning OCR inference...');
      
      onUploaded(submission.id);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Upload or processing failed. Please check backend server.');
    } finally {
      setUploading(false);
      setUploadStep('');
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <button
          onClick={onCancel}
          className="text-sm font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1.5"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 sm:p-8">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl">
            <Upload className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
              Upload Student Answer Sheet
            </h2>
            <p className="text-sm text-slate-500">
              Submit a scanned handwritten answer paper in PDF, JPG, or PNG format for AI OCR and automated grading.
            </p>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleUpload} className="mt-6 space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Select Examination
              </label>
              <select
                value={examId}
                onChange={(e) => setExamId(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white"
                required
              >
                <option value="">-- Choose an Exam --</option>
                {exams.map((exam) => (
                  <option key={exam.id} value={exam.id}>
                    {exam.title} ({exam.subject}) - {exam.total_max_marks} marks
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Student Roll / Registration No.
              </label>
              <input
                type="text"
                placeholder="e.g. 21BCE1042"
                value={rollNo}
                onChange={(e) => setRollNo(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-2">
              Scanned Paper (PDF / JPG / PNG)
            </label>
            <div className="border-2 border-dashed border-slate-300 hover:border-blue-400 rounded-2xl p-6 text-center cursor-pointer transition bg-slate-50/50">
              <input
                type="file"
                id="file-upload"
                onChange={handleFileChange}
                accept=".pdf,.jpg,.jpeg,.png"
                className="hidden"
              />
              <label htmlFor="file-upload" className="cursor-pointer block">
                {file ? (
                  <div className="flex flex-col items-center">
                    <FileText className="w-10 h-10 text-blue-600 mb-2" />
                    <span className="font-semibold text-slate-800 text-sm">{file.name}</span>
                    <span className="text-xs text-slate-500 mt-0.5">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready to process
                    </span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center">
                    <Upload className="w-10 h-10 text-slate-400 mb-2" />
                    <span className="font-semibold text-slate-700 text-sm">
                      Click to choose file or drag & drop
                    </span>
                    <span className="text-xs text-slate-400 mt-1">
                      Clear handwritten text scans give the highest recognition accuracy.
                    </span>
                  </div>
                )}
              </label>
            </div>
          </div>

          {previewUrl && (
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
              <span className="text-xs font-semibold text-slate-600 block mb-2">Image Preview:</span>
              <img
                src={previewUrl}
                alt="Answer Sheet Preview"
                className="max-h-64 mx-auto object-contain rounded-lg border border-slate-200 shadow-sm"
              />
            </div>
          )}

          {uploading && (
            <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 text-blue-800 text-sm space-y-2">
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent" />
                <span className="font-semibold">{uploadStep}</span>
              </div>
              <p className="text-xs text-blue-600/80">
                Deep learning inference is evaluating line-level handwriting regions.
              </p>
            </div>
          )}

          <div className="pt-2 flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="px-5 py-2.5 rounded-xl border border-slate-300 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={uploading || !file}
              className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-md transition flex items-center gap-2 disabled:opacity-50"
            >
              <CheckCircle className="w-4 h-4" /> Start Evaluation
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
