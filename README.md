# ResumeForge: Agentic CV & Cover Letter Tailoring Platform

ResumeForge is an intelligent, multi-agent platform designed to parse candidate CVs, compare them against Job Descriptions (JDs), identify gaps, perform simulated ATS keyword density auditing, and automatically draft & compile tailored, publication-ready LaTeX CVs and cover letters.

This repository is structured as a full-stack application:
*   **`backend/`**: A Python FastAPI backend utilizing the Google Agent Development Kit (ADK) and XeLaTeX compiler.
*   **`frontend/`**: A Vite + React single-page web application featuring dynamic markdown editors, fit analysis reports, and real-time compiled PDF viewers.

---

## 🛠️ Prerequisites

To run ResumeForge locally, ensure you have the following installed:

1.  **Python**: Version 3.10 or higher.
2.  **Node.js**: Node 18+ (includes `npm`).
3.  **LaTeX Compiler**: A compiler supporting the `xelatex` engine:
    *   **Windows**: [MiKTeX](https://miktex.org/) is recommended (verify `xelatex` is added to your system `PATH`).
    *   **macOS / Linux**: [TeX Live](https://www.tug.org/texlive/).
4.  **Gemini API Key**: Required by the ADK agents.

---

## 🚀 Quick Start Instructions

You will need two terminal sessions running: one for the backend server and one for the frontend server.

### 1. Run the Backend API

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Create and activate a virtual environment:
    *   **Windows**:
        ```bash
        python -m venv .venv
        .venv\Scripts\activate
        ```
    *   **macOS / Linux**:
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Configure your environment variables:
    Create a `.env` file in the `backend/` directory:
    ```env
    GEMINI_API_KEY=your_gemini_api_key_here
    ```
5.  Start the FastAPI server:
    ```bash
    python -m uvicorn app:app --reload --port 8000
    ```
    The API will be available at [http://localhost:8000](http://localhost:8000).

---

### 2. Run the Frontend UI

1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install npm dependencies:
    ```bash
    npm install
    ```
3.  Start the Vite React development server:
    ```bash
    npm run dev
    ```
    The application will open automatically at [http://localhost:5173](http://localhost:5173).

---

## 📂 Project Architecture & Features

### Core Agents (`backend/agents/`)
*   **CV Parser**: Extracts raw resume documents (PDF, DOCX, MD) into structured JSON details, compiling them into a base Markdown schema.
*   **JD Parser**: Extracts required skills, qualifications, and company tone from job descriptions or web URLs.
*   **Match Maker**: Performs a deep fit analysis, compiling a match score, strong matches, gaps, achievement metrics suggestions, and 5 custom interview preparation questions.
*   **CV & Cover Letter Writers**: Draft high-quality LaTeX files matching the **Awesome-CV** styling template.
*   **ATS Verifier**: Simulates legacy keyword-matching tracking software to calculate exact keyword density.

### Key API Integration Features
*   **ATS Loop Optimization**: Under `/api/generate-final`, the backend automatically runs a 3-step loop, updating the LaTeX draft with verifier feedback until the simulated ATS score reaches 90+.
*   **Live Markdown Caching**: Whenever you generate a final resume, any edits you made to the base CV Markdown are saved back to `backend/data/input/{your_resume}_parsed.md`. The next time you upload that CV, your edits are loaded instantly, skipping the parser LLM call.
*   **Live PDF Previews**: The frontend embeds a dynamic `<iframe>` pointing directly to the LaTeX-compiled PDF assets hosted on `/static`, allowing real-time inspection.
