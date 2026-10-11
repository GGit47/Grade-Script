import axios from 'axios';
import type { Exam, DashboardStats, SubmissionDetail } from '../types';

const API_BASE = '/api';

export const api = {
  getDashboard: async (): Promise<DashboardStats> => {
    const res = await axios.get(`${API_BASE}/dashboard`);
    return res.data;
  },

  getExams: async (): Promise<Exam[]> => {
    const res = await axios.get(`${API_BASE}/exams`);
    return res.data;
  },

  getExam: async (id: number): Promise<Exam> => {
    const res = await axios.get(`${API_BASE}/exams/${id}`);
    return res.data;
  },

  createExam: async (examData: {
    title: string;
    subject: string;
    class_or_batch: string;
    questions: {
      question_number: number;
      question_text: string;
      reference_answer: string;
      max_marks: number;
      essential_keywords?: string;
      rubric_criteria?: string;
    }[];
  }): Promise<Exam> => {
    const res = await axios.post(`${API_BASE}/exams`, examData);
    return res.data;
  },

  uploadSubmission: async (
    examId: number,
    studentRollNo: string,
    file: File
  ): Promise<SubmissionDetail> => {
    const formData = new FormData();
    formData.append('exam_id', examId.toString());
    formData.append('student_roll_no', studentRollNo);
    formData.append('file', file);

    const res = await axios.post(`${API_BASE}/submissions/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  getSubmission: async (id: number): Promise<SubmissionDetail> => {
    const res = await axios.get(`${API_BASE}/submissions/${id}`);
    return res.data;
  },

  updateRegion: async (
    regionId: number,
    data: { question_id?: number | null; edited_text?: string }
  ) => {
    const res = await axios.put(`${API_BASE}/regions/${regionId}`, data);
    return res.data;
  },

  updateEvaluation: async (
    evalId: number,
    data: { approved_marks: number; teacher_notes?: string; is_teacher_approved?: boolean }
  ) => {
    const res = await axios.put(`${API_BASE}/evaluations/${evalId}`, data);
    return res.data;
  },

  finalizeSubmission: async (subId: number) => {
    const res = await axios.post(`${API_BASE}/submissions/${subId}/finalize`);
    return res.data;
  },

  getReportUrl: (subId: number) => `${API_BASE}/submissions/${subId}/report`,
};
