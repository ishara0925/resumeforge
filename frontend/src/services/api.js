/**
 * CV Agent Frontend - API Integration Service
 * 
 * This service contains stubbed functions to communicate with the Python backend's REST API endpoints.
 * It simulates network latency and returns mock data that matches the expected data structures.
 */

// Simulated delay helper
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Simple log utility for debugging
const logApiCall = (endpoint, payload, response) => {
  console.log(`[API Call] ${endpoint}`, {
    request: payload,
    response: response,
    timestamp: new Date().toISOString()
  });
};

export const apiService = {
  /**
   * Uploads the raw CV file (.pdf, .docx, .md) to parse it into Markdown.
   * Endpoint: /api/upload-cv
   * @param {File} file - The raw file object
   * @returns {Promise<{ success: boolean, cvMarkdown: string, filename: string }>}
   */
  uploadCv: async (file) => {
    await delay(1500); // Simulate network latency
    
    // Default parsed CV markdown content
    const mockMarkdown = `# John Doe
**Software Engineer** | john.doe@example.com | +1-555-0199 | github.com/johndoe | linkedin.com/in/johndoe

## Professional Summary
Detail-oriented and results-driven Software Engineer with 3+ years of experience in designing, building, and maintaining scalable web applications. Proficient in Python, JavaScript, and cloud technologies. Strong track record of improving application performance and deploying containerized microservices.

## Work Experience
**Software Developer** | TechInnovate Corp | 2024 - Present
- Led technology implementation for a real-time data analysis platform.
- Increased sales and user engagement by integrating third-party analytical APIs.
- Improved application load times and managed a team of developers for core feature deployments.

**Junior Engineer** | DevSystems Inc | 2022 - 2024
- Responsible for deployment and testing of Python backend web services.
- Created microservices using Docker and maintained SQL databases for high availability.

## Education
**Bachelor of Science in Computer Science** | University of Engineering | 2018 - 2022
- GPA: 3.8/4.0
- Graduation Honors: Cum Laude

## Projects
**Personal Project: ChatSphere** | 2024
- Built a real-time chat application with WebSockets and Node.js.
- Containerized the entire deployment using Docker and Kubernetes.

## Skills
- **Languages:** Python, JavaScript, SQL, C++
- **Frameworks & Libs:** React, Node.js, Express, FastAPI
- **Tools & DevOps:** Docker, Git, AWS, CI/CD pipelines
`;

    const response = {
      success: true,
      cvMarkdown: mockMarkdown,
      filename: file ? file.name : "sample_cv.pdf"
    };

    logApiCall("/api/upload-cv", { fileName: file?.name, fileSize: file?.size }, response);
    return response;
  },

  /**
   * Parses the Job Description from a URL or raw text string.
   * Endpoint: /api/parse-jd
   * @param {string} jdInput - Either a URL or raw text of the job description
   * @param {boolean} isUrl - True if the input is a URL to scrape
   * @returns {Promise<{ success: boolean, jdDetails: object }>}
   */
  parseJd: async (jdInput, isUrl = false) => {
    await delay(2000); // Scraping/LLM parsing takes a bit longer

    const mockJdDetails = {
      company_name: isUrl ? "Starlight Systems" : "Apex Solutions",
      position: "Senior Python Developer",
      required_skills: [
        "Python",
        "FastAPI",
        "Docker",
        "SQL",
        "Kubernetes",
        "AWS",
        "Unit Testing"
      ],
      preferred_experience: "5+ years of experience in software development",
      raw_text: isUrl 
        ? "Looking for a Senior Python Developer at Starlight Systems. Requirements: Expert in Python and FastAPI, experience containerizing apps with Docker and Kubernetes, strong database design in SQL, deploy to AWS, and ensure 90%+ code coverage with Unit Testing. Experience managing teams is a plus." 
        : jdInput
    };

    const response = {
      success: true,
      jdDetails: mockJdDetails
    };

    logApiCall("/api/parse-jd", { jdInput, isUrl }, response);
    return response;
  },

  /**
   * Matches the CV Markdown against the parsed Job Description to get a match analysis.
   * Endpoint: /api/get-match-report
   * @param {string} cvMarkdown - The current CV in markdown format
   * @param {object} jdDetails - The parsed Job Description details
   * @returns {Promise<{ success: boolean, matchAnalysis: object }>}
   */
  getMatchReport: async (cvMarkdown, jdDetails) => {
    await delay(1800);

    // Dynamic checks to make the mock somewhat interactive
    const hasFastApi = cvMarkdown.toLowerCase().includes("fastapi");
    const hasKubernetes = cvMarkdown.toLowerCase().includes("kubernetes");
    const hasUnitTesting = cvMarkdown.toLowerCase().includes("unit testing");

    const skillsComparison = [
      { required_skill: "Python", possessed: true, details: "Candidate has 3+ years experience with Python." },
      { required_skill: "SQL", possessed: true, details: "Used SQL databases extensively at DevSystems Inc." },
      { required_skill: "Docker", possessed: true, details: "Containerized ChatSphere and legacy Python microservices." },
      { required_skill: "FastAPI", possessed: hasFastApi, details: hasFastApi ? "Listed in technical skills." : "FastAPI is not mentioned in the candidate's CV." },
      { required_skill: "Kubernetes", possessed: hasKubernetes, details: hasKubernetes ? "Mentioned in personal project deployment." : "No Kubernetes experience is mentioned in the CV." },
      { required_skill: "AWS", possessed: true, details: "Experienced with deployment on AWS cloud infrastructure." },
      { required_skill: "Unit Testing", possessed: hasUnitTesting, details: hasUnitTesting ? "Mentioned under testing and quality practices." : "No explicit mention of Unit Testing or test-driven development." }
    ];

    // Calculate score dynamically
    const possessedCount = skillsComparison.filter(s => s.possessed).length;
    const matchScore = Math.round((possessedCount / skillsComparison.length) * 100);

    // Gaps and improvements
    const strongMatches = [
      "Excellent core language match (Python, SQL, JavaScript).",
      "Demonstrated experience deploying with Docker.",
      "Cloud platform experience (AWS) matches the target infrastructure."
    ];

    const requiredImprovements = [];
    if (!hasFastApi) requiredImprovements.push("Add FastAPI framework experience to highlight API creation skills.");
    if (!hasKubernetes) requiredImprovements.push("Highlight container orchestration tools like Kubernetes to match standard scaling requirements.");
    if (!hasUnitTesting) requiredImprovements.push("Integrate Unit Testing and testing libraries (pytest) to address software quality requirements.");
    
    // Metric interrogation
    const followUpQuestions = [
      "In your 'TechInnovate Corp' role, by what percentage did you increase sales and user engagement?",
      "How many developers did you manage in your team at TechInnovate Corp?",
      "Can you quantify the improvement in application load times (e.g. reduced load times by 40%)?"
    ];

    // Interview preparation questions
    const interviewQuestions = [
      {
        question: "We see you have Docker experience, but our architecture relies heavily on Kubernetes. Can you describe your familiarity with container orchestration?",
        talking_points: [
          "Explain the transition from single container development to multi-node orchestration.",
          "Talk about deploying services in pods, managing ingress, and configmaps.",
          "Cite ChatSphere project and mention readiness to expand knowledge in prod environments."
        ]
      },
      {
        question: "The job requires FastAPI experience, but your history focuses on node.js and general Python. How would you approach building an asynchronous microservice in FastAPI?",
        talking_points: [
          "Discuss FastAPI's use of Pydantic for request validation.",
          "Explain async/await syntax in Python and advantages of ASGI.",
          "Highlight speed benchmarks and automatic OpenAPI docs generation."
        ]
      },
      {
        question: "How do you structure unit tests in your python projects to ensure 90%+ code coverage?",
        talking_points: [
          "Discuss using pytest for fixtures and test runners.",
          "Explain mocks and patches for database connections and API calls.",
          "Mention incorporating coverage tools in CI/CD pipeline steps."
        ]
      },
      {
        question: "Can you elaborate on the third-party analytical APIs you integrated? What was the business impact?",
        talking_points: [
          "Describe integration mechanics (e.g., REST API, webhook subscriptions).",
          "Highlight metrics (e.g., 'integrated Stripe analytics which improved retention visibility by 15%').",
          "Address how you handled failures in external API services."
        ]
      },
      {
        question: "You mentioned managing a team. What is your leadership style and how do you handle technical debt conflicts?",
        talking_points: [
          "Explain agile sprint planning and distributing developer tasks.",
          "Discuss balancing product features with refactoring sprints.",
          "Mention facilitating cross-functional design reviews to reduce friction."
        ]
      }
    ];

    const response = {
      success: true,
      matchAnalysis: {
        target_job_title: jdDetails.position || "Senior Python Developer",
        match_score: matchScore,
        strong_matches: strongMatches,
        required_improvements: requiredImprovements,
        skills_comparison: skillsComparison,
        follow_up_questions: followUpQuestions,
        interview_questions: interviewQuestions
      }
    };

    logApiCall("/api/get-match-report", { cvMarkdownLength: cvMarkdown.length, jdDetails }, response);
    return response;
  },

  /**
   * Generates the final tailored CV and Cover Letter files based on the matchmaker approval.
   * Endpoint: /api/generate-final
   * @param {string} cvMarkdown - The final modified CV markdown
   * @param {object} matchAnalysis - The approved match analysis object
   * @returns {Promise<{ success: boolean, cvPdfUrl: string, coverLetterPdfUrl: string, atsScore: number }>}
   */
  generateFinal: async (cvMarkdown, matchAnalysis) => {
    await delay(3000); // Hard LaTeX compilation and ATS checks loop simulation

    const response = {
      success: true,
      cvPdfUrl: "mock_cv.pdf",
      coverLetterPdfUrl: "mock_cover_letter.pdf",
      atsScore: 94, // Refined score above 90
      cvMarkdown: cvMarkdown,
      latexCv: `% Dummy Latex CV Output
\\documentclass[11pt, a4paper]{awesome-cv}
\\name{John}{Doe}
\\position{Senior Python Developer}
\\begin{document}
\\makecvheader[C]
\\begin{cvparagraph}
Result-oriented Software Engineer with 3+ years experience...
\\end{cvparagraph}
\\end{document}
`,
      coverLetter: `% Dummy Cover Letter LaTeX
\\documentclass[11pt, a4paper]{awesome-cv}
\\begin{document}
Dear Hiring Team, I am writing to express my strong interest...
\\end{document}
`
    };

    logApiCall("/api/generate-final", { cvMarkdownLength: cvMarkdown.length, matchAnalysis }, response);
    return response;
  }
};
