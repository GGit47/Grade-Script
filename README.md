# Grade-Script

### AI-Powered Handwritten Exam Evaluation System

Grade Script is a deep learning-based examination evaluation platform designed to help educators and mentors assess handwritten answer sheets more efficiently. It combines handwriting recognition, natural language processing, and rubric-based grading to extract student answers, compare them against reference answers, and recommend marks for teacher review.

The goal is to reduce repetitive evaluation work while maintaining transparency, consistency, and human oversight in the grading process.

> **Project status:** MVP development
> **Project type:** Deep Learning | Computer Vision | Natural Language Processing | Full-Stack Development

---

## Overview

Evaluating large volumes of handwritten examination papers is time-consuming and repetitive. Manual grading can also introduce inconsistencies when educators assess similar answers across multiple students.

Grade Script aims to streamline this process through an AI-assisted workflow:

1. Upload a scanned handwritten answer sheet.
2. Preprocess the document and extract handwritten text.
3. Associate recognized answers with examination questions.
4. Compare student answers with teacher-provided reference answers and marking rubrics.
5. Generate suggested marks and explanations.
6. Review, correct, and approve the evaluation.
7. Export the final assessment report.

**Grade Script is designed to assist educators, not replace their judgment.** AI-generated scores remain provisional until reviewed and approved by a teacher.

## Key Features

### Handwriting Recognition

* Process scanned examination papers in PDF and image formats.
* Apply image preprocessing to improve readability.
* Use pretrained handwriting recognition models to extract text.
* Allow teachers to inspect and correct recognized answers.

### Intelligent Answer Evaluation

* Compare student responses against reference answers.
* Identify essential concepts and potentially missing information.
* Use semantic similarity to support answer comparison.
* Support rubric-based scoring and partial-credit rules.
* Generate explanations for suggested marks.

### Teacher Review and Approval

* Display the original answer alongside its extracted text.
* Present reference answers, suggested marks, and grading explanations.
* Allow teachers to adjust individual question scores.
* Preserve the distinction between AI recommendations and approved marks.

### Examination Management

* Create examinations and configure questions.
* Define maximum marks, reference answers, and marking criteria.
* Upload and manage student submissions.
* Track evaluation progress.

### Reports and Analytics

* Generate student-wise evaluation reports.
* Display question-wise marks and total scores.
* Export evaluation results as PDF documents.
* Provide basic examination and score analytics.

---

## Technology Stack

| Component               | Technology                                 |
| ----------------------- | ------------------------------------------ |
| Frontend                | React, Vite, TypeScript                    |
| UI Styling              | Tailwind CSS                               |
| Backend                 | Python, FastAPI                            |
| Database                | SQLite, SQLAlchemy                         |
| Deep Learning           | PyTorch                                    |
| Handwriting Recognition | Hugging Face Transformers, Microsoft TrOCR |
| Image Processing        | OpenCV, Pillow                             |
| Semantic Similarity     | Sentence Transformers                      |
| PDF Processing          | PyMuPDF                                    |
| Report Generation       | ReportLab                                  |
| Testing                 | pytest                                     |

The technology stack may evolve during development as compatibility, performance, and evaluation requirements are validated.

## System Architecture

```text
                 TEACHER
                    |
                    v
          React Web Application
                    |
                    v
              FastAPI Backend
                    |
          +---------+----------+
          |         |          |
          v         v          v
      Document   Handwriting  Database
      Processing Recognition   (SQLite)
          |         |
          +----+----+
               |
               v
        Extracted Student Text
               |
               v
        Answer Evaluation Engine
        +----------------------+
        | Reference Answers    |
        | Essential Concepts  |
        | Semantic Similarity  |
        | Marking Rubrics      |
        +----------------------+
               |
               v
        Suggested Marks
               |
               v
       Teacher Review and Approval
               |
               v
        Final Score and PDF Report
```

## How It Works

### 1. Document Processing

The uploaded examination paper is validated and converted into page images when necessary. Image processing techniques can improve contrast, reduce noise, correct rotation, and prepare answer regions for recognition.

### 2. Handwriting Recognition

A pretrained TrOCR model is used to recognize handwriting from appropriately cropped text regions. The recognized text is presented to the teacher for correction before grading.

### 3. Answer Comparison

The evaluation engine compares student answers against the teacher's reference answers and marking criteria. Text normalization, essential-concept matching, and semantic similarity help identify relevant content even when students phrase answers differently.

### 4. Rubric-Based Scoring

The grading engine recommends marks based on the configured criteria and maximum marks. It can identify potentially missing concepts and provide a concise explanation for the suggested score.

Semantic similarity alone is not sufficient to determine correctness. The grading logic must also consider the meaning of the response and the requirements of the question.

### 5. Human Review

Teachers can inspect the evidence, correct transcription errors, modify suggested marks, and approve the final result. The system maintains a distinction between AI-generated recommendations and teacher-approved grades.

---

## Getting Started

### Prerequisites

Install the following before starting:

* Python 3.10 or a compatible version supported by the selected dependencies
* Node.js LTS and npm
* Git
* A code editor such as Visual Studio Code
* An internet connection for the initial installation and pretrained model download

CPU inference is supported as the baseline. A compatible CUDA-enabled GPU may improve inference speed, depending on the environment.

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/grade-script.git
cd grade-script
```

Replace `YOUR_USERNAME` with your GitHub username.

### 2. Set Up the Backend

Create a virtual environment:

**Windows**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux or macOS**

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the backend dependencies:

```bash
pip install -r backend/requirements.txt
```

The dependency file should contain the compatible packages required by the implemented backend, including FastAPI, Uvicorn, SQLAlchemy, PyTorch, Transformers, OpenCV, Pillow, Sentence Transformers, PyMuPDF, and ReportLab.

If the project does not yet contain `backend/requirements.txt`, create it with the dependencies and versions used by the implementation before running this command.

Start the backend from the repository root:

```bash
uvicorn app.main:app --app-dir backend --reload
```

Once running, open:

* API: http://127.0.0.1:8000
* Interactive API documentation: http://127.0.0.1:8000/docs

### 3. Set Up the Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL displayed by Vite, usually:

http://localhost:5173

The frontend must be configured to communicate with the backend API. Use an environment variable such as `VITE_API_BASE_URL` instead of hardcoding the backend URL throughout the application.

### 4. Download the Handwriting Recognition Model

The initial implementation uses the pretrained checkpoint:

`microsoft/trocr-base-handwritten`

Hugging Face Transformers can download the model automatically when it is first loaded, provided the required packages and network access are available.

The initial model download may take time and require additional disk space and memory. For offline usage, download and cache the required model files in advance.

---

## Example Workflow

1. Create an examination named *Introduction to Machine Learning*.
2. Add questions, reference answers, maximum marks, and marking criteria.
3. Upload a scanned handwritten answer sheet.
4. Inspect the recognized student answers and correct any transcription errors.
5. Run the grading engine.
6. Review the suggested marks and explanations for each question.
7. Adjust scores where necessary and approve the evaluation.
8. Download the final PDF report.

Use synthetic or appropriately authorized examination papers for initial testing.

## Evaluation and Testing

Grade Script should be evaluated using separate measures for handwriting recognition and answer grading.

### Handwriting Recognition

* **Character Error Rate (CER):** Measures character-level transcription errors.
* **Word Error Rate (WER):** Measures word-level transcription errors.

These metrics require manually transcribed reference text for comparison.

### Answer Grading

* **Mean Absolute Error (MAE):** Measures the average difference between AI-recommended marks and teacher-assigned marks.
* **Exact Agreement:** Measures the proportion of answers receiving the same score as the reference evaluation.
* **Tolerance-Based Agreement:** Measures how often the recommended score falls within a defined mark difference from the reference score.

### System Reliability

* Successful document upload and processing rate.
* Correct association between answers and questions.
* Correct calculation of total marks.
* Successful persistence of teacher edits and approvals.
* Successful generation of downloadable reports.

No accuracy or performance figures should be assumed. Report measured results only after testing against a documented sample of handwritten papers and teacher-assigned marks.

## Current Limitations

The initial version focuses on conventional written answers and relatively structured examination layouts.

Potential limitations include:

* Difficult or unusually stylized handwriting.
* Poor-quality scans and photographs.
* Automatic identification of question boundaries.
* Mathematical equations, diagrams, and complex symbols.
* Answers that require extensive reasoning or subject-specific interpretation.
* Semantic similarity scores that do not fully capture factual correctness.

Uncertain or unreadable answers should be flagged for teacher review rather than automatically assigned a definitive score.

## Roadmap

### Phase 1: Core MVP

* [ ] Examination and question management.
* [ ] PDF and image uploads.
* [ ] Document preprocessing.
* [ ] Pretrained handwriting recognition.
* [ ] Editable recognized text.
* [ ] Reference-answer comparison.
* [ ] Rubric-based suggested marks.
* [ ] Teacher review and approval.
* [ ] PDF evaluation reports.

### Phase 2: Improved Intelligence

* [ ] More reliable automatic question and answer segmentation.
* [ ] Improved partial-credit evaluation.
* [ ] Recognition quality and grading agreement analysis.
* [ ] Better handling of poor-quality handwriting.
* [ ] Expanded evaluation datasets and automated tests.

### Phase 3: Advanced Platform

* [ ] Batch processing for entire classes.
* [ ] Improved mathematical notation and diagram handling.
* [ ] Optional LLM-assisted rubric interpretation.
* [ ] Fine-tuning with suitable labeled handwriting datasets.
* [ ] Teacher authentication and role-based access.
* [ ] Cloud deployment and scalable document storage.
* [ ] Advanced grading analytics and reporting.

## Privacy and Responsible AI

Examination papers can contain sensitive student information.

Grade Script should use controlled file access, safe upload handling, appropriate data retention policies, and secure storage. Real student papers should not be sent to external AI services without the necessary authorization.

AI-generated grades should remain recommendations until approved by an educator. The platform should preserve teacher corrections and make grading decisions reviewable.

## Contributing

Contributions, suggestions, bug reports, and improvements are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Implement and test your changes.
4. Submit a pull request with a clear explanation of the changes.

## License

Choose an appropriate open-source license before publishing the repository. For example, the MIT License may be suitable if you want others to reuse and modify your code. Add a `LICENSE` file before describing the project as MIT-licensed.

## Author

Gokul Sethumadhavan & Eshaan Sumesh


AI-ML Undergraduate | Deep Learning | Computer Vision | Natural Language Processing

GitHub: https://github.com/GGit47
GitHub: https://github.com/Eshaan1e24

---

*Grade Script: Making handwritten exam evaluation faster, more transparent, and easier for educators.*

