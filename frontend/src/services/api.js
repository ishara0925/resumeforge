/**
 * CV Agent Frontend - API Integration Service
 * 
 * This service communicates with the Python backend's REST API endpoints.
 */

const API_BASE_URL = "http://localhost:8000";

export const apiService = {
  /**
   * Uploads the raw CV file (.pdf, .docx, .md) to parse it into Markdown.
   * Endpoint: /api/upload-cv
   * @param {File} file - The raw file object
   * @returns {Promise<{ success: boolean, cvMarkdown: string, filename: string }>}
   */
  uploadCv: async (file) => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/api/upload-cv`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to upload CV");
    }

    return await response.json();
  },

  /**
   * Parses the Job Description from a URL or raw text string.
   * Endpoint: /api/parse-jd
   * @param {string} jdInput - Either a URL or raw text of the job description
   * @param {boolean} isUrl - True if the input is a URL to scrape
   * @returns {Promise<{ success: boolean, jdDetails: object }>}
   */
  parseJd: async (jdInput, isUrl = false) => {
    const response = await fetch(`${API_BASE_URL}/api/parse-jd`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ jdInput, isUrl }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to parse Job Description");
    }

    return await response.json();
  },

  /**
   * Matches the CV Markdown against the parsed Job Description to get a match analysis.
   * Endpoint: /api/get-match-report
   * @param {string} cvMarkdown - The current CV in markdown format
   * @param {object} jdDetails - The parsed Job Description details
   * @returns {Promise<{ success: boolean, matchAnalysis: object }>}
   */
  getMatchReport: async (cvMarkdown, jdDetails) => {
    const response = await fetch(`${API_BASE_URL}/api/get-match-report`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ cvMarkdown, jdDetails }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to get match report");
    }

    return await response.json();
  },

  /**
   * Generates the final tailored CV and Cover Letter files based on the matchmaker approval.
   * Endpoint: /api/generate-final
   * @param {string} cvMarkdown - The final modified CV markdown
   * @param {object} matchAnalysis - The approved match analysis object
   * @returns {Promise<{ success: boolean, cvPdfUrl: string, coverLetterPdfUrl: string, atsScore: number, cvMarkdown: string, latexCv: string, coverLetter: string }>}
   */
  generateFinal: async (cvMarkdown, matchAnalysis, originalFilename) => {
    const response = await fetch(`${API_BASE_URL}/api/generate-final`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ cvMarkdown, matchAnalysis, originalFilename }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to generate final optimized resumes");
    }

    return await response.json();
  }
};
