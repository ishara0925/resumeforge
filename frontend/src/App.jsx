import React, { useState, useEffect } from 'react';
import './App.css';
import { apiService } from './services/api';

// Circular Progress Ring component for Match Score
const MatchScoreRing = ({ score }) => {
  const radius = 60;
  const stroke = 8;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  // Determine color based on score
  let strokeColor = 'var(--color-accent)'; // Red
  if (score >= 80) {
    strokeColor = 'var(--color-primary)'; // Teal
  } else if (score >= 60) {
    strokeColor = 'hsl(38, 92%, 50%)'; // Orange
  }

  return (
    <div className="progress-ring-container">
      <svg
        height={radius * 2}
        width={radius * 2}
        className="progress-ring-svg"
      >
        <circle
          className="progress-ring-circle-bg"
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          className="progress-ring-circle-val"
          stroke={strokeColor}
          fill="transparent"
          strokeDasharray={circumference + ' ' + circumference}
          style={{ strokeDashoffset }}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
      </svg>
      <div className="progress-ring-text">
        <span className="progress-score">{score}%</span>
        <span className="progress-label">Match</span>
      </div>
    </div>
  );
};

export default function App() {
  // Workflow Stepper State
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');

  // Step 1: Upload & Job Details State
  const [cvFile, setCvFile] = useState(null);
  const [jdInput, setJdInput] = useState('');
  const [isJdUrl, setIsJdUrl] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  // Step 2: Markdown Editor State
  const [cvMarkdown, setCvMarkdown] = useState('');

  // Step 3: Match Maker Details State
  const [jdDetails, setJdDetails] = useState(null);
  const [matchAnalysis, setMatchAnalysis] = useState(null);

  // Step 4: Final Outputs State
  const [finalOutputs, setFinalOutputs] = useState(null);
  const [activeFinalTab, setActiveFinalTab] = useState('cv'); // 'cv' or 'cl'

  // Dynamic status details for the loading spinner
  const [loadingSubText, setLoadingSubText] = useState('');

  useEffect(() => {
    let interval;
    if (loading) {
      const messages = [
        "Analyzing resume structures...",
        "Scoping out legacy ATS parsing headers...",
        "Aligning qualifications with target roles...",
        "Identifying semantic gaps...",
        "Compiling LaTeX source files...",
        "Evaluating keyword density benchmarks..."
      ];
      let i = 0;
      setLoadingSubText(messages[0]);
      interval = setInterval(() => {
        i = (i + 1) % messages.length;
        setLoadingSubText(messages[i]);
      }, 2000);
    } else {
      setLoadingSubText('');
    }
    return () => clearInterval(interval);
  }, [loading]);

  // -------------------------------------------------------------
  // EVENT HANDLERS
  // -------------------------------------------------------------

  // Drag and Drop CV Handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const validTypes = ['.pdf', '.docx', '.md'];
      const fileExt = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
      if (validTypes.includes(fileExt)) {
        setCvFile({ name: file.name, size: (file.size / 1024 / 1024).toFixed(2) + " MB" });
      } else {
        alert("Please upload only .pdf, .docx, or .md files.");
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setCvFile({ name: file.name, size: (file.size / 1024 / 1024).toFixed(2) + " MB" });
    }
  };

  const triggerFileInput = () => {
    document.getElementById('file-upload-input').click();
  };

  const removeFile = (e) => {
    e.stopPropagation();
    setCvFile(null);
  };

  // Step 1: Submit Form to Analyze
  const handleStartAnalysis = async () => {
    if (!cvFile) {
      alert("Please upload your CV first.");
      return;
    }
    if (!jdInput.trim()) {
      alert("Please enter a job description or URL.");
      return;
    }

    try {
      setLoading(true);
      setLoadingMessage("Parsing CV & Extracting Text...");
      
      // 1. Upload/Parse CV
      const cvRes = await apiService.uploadCv(cvFile);
      setCvMarkdown(cvRes.cvMarkdown);

      // 2. Parse JD
      setLoadingMessage("Scraping & Analyzing Job Description...");
      const jdRes = await apiService.parseJd(jdInput, isJdUrl);
      setJdDetails(jdRes.jdDetails);

      setLoading(false);
      setStep(2);
    } catch (err) {
      console.error(err);
      alert("Failed to analyze CV/JD inputs. Please try again.");
      setLoading(false);
    }
  };

  // Step 2: Save Edited CV Markdown
  const handleProceedToMatch = async () => {
    try {
      setLoading(true);
      setLoadingMessage("Generating Alignment & Match Report...");
      
      const matchRes = await apiService.getMatchReport(cvMarkdown, jdDetails);
      setMatchAnalysis(matchRes.matchAnalysis);
      
      setLoading(false);
      setStep(3);
    } catch (err) {
      console.error(err);
      alert("Failed to match CV with Job Description.");
      setLoading(false);
    }
  };

  // Step 3: Approve and Refine CV (ATS optimization loop)
  const handleApproveAndGenerate = async () => {
    try {
      setLoading(true);
      setLoadingMessage("Running Simulated ATS Verification & LaTeX Optimization...");
      
      const finalRes = await apiService.generateFinal(cvMarkdown, matchAnalysis);
      setFinalOutputs(finalRes);
      
      setLoading(false);
      setStep(4);
    } catch (err) {
      console.error(err);
      alert("Error compiling final optimized resumes.");
      setLoading(false);
    }
  };

  const handleBackToEditor = () => {
    setStep(2);
  };

  const handleReset = () => {
    setStep(1);
    setCvFile(null);
    setJdInput('');
    setIsJdUrl(false);
    setCvMarkdown('');
    setJdDetails(null);
    setMatchAnalysis(null);
    setFinalOutputs(null);
  };

  // Render helper for Markdown Preview (handles basic bullet styles, headers)
  const renderSimpleMarkdown = (mdText) => {
    const lines = mdText.split('\n');
    return lines.map((line, idx) => {
      if (line.startsWith('# ')) {
        return <h1 key={idx}>{line.substring(2)}</h1>;
      }
      if (line.startsWith('## ')) {
        return <h2 key={idx}>{line.substring(3)}</h2>;
      }
      if (line.startsWith('- ')) {
        // Simple bold parser for markdown bullet point (e.g. **Languages:** text)
        const content = line.substring(2);
        return <li key={idx}>{parseBoldText(content)}</li>;
      }
      if (line.trim() === '') {
        return <br key={idx} />;
      }
      return <p key={idx}>{parseBoldText(line)}</p>;
    });
  };

  const parseBoldText = (text) => {
    const parts = text.split('**');
    return parts.map((part, index) => 
      index % 2 === 1 ? <strong key={index}>{part}</strong> : part
    );
  };

  return (
    <div className="App flex-column">
      {/* APP HEADER */}
      <header className="app-header">
        <div className="logo-container">
          <div className="logo-icon">F</div>
          <div>
            <span className="logo-text">ResumeForge</span>
            <span className="logo-badge">Agentic</span>
          </div>
        </div>
        <div className="header-actions">
          {step > 1 && (
            <button className="btn-secondary" onClick={handleReset} style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
              Reset Workflow
            </button>
          )}
        </div>
      </header>

      {/* STEPPER PROGRESS */}
      <div className="stepper-container">
        <div className="stepper-line"></div>
        <div 
          className="stepper-line-active" 
          style={{ width: `${((step - 1) / 3) * 100}%` }}
        ></div>
        
        <div className={`step-item ${step >= 1 ? 'active' : ''} ${step > 1 ? 'completed' : ''}`} onClick={() => step > 1 && setStep(1)}>
          <div className="step-circle">{step > 1 ? '✓' : '1'}</div>
          <span className="step-label">Upload</span>
        </div>
        <div className={`step-item ${step >= 2 ? 'active' : ''} ${step > 2 ? 'completed' : ''}`} onClick={() => step > 2 && setStep(2)}>
          <div className="step-circle">{step > 2 ? '✓' : '2'}</div>
          <span className="step-label">Review</span>
        </div>
        <div className={`step-item ${step >= 3 ? 'active' : ''} ${step > 3 ? 'completed' : ''}`} onClick={() => step > 3 && setStep(3)}>
          <div className="step-circle">{step > 3 ? '✓' : '3'}</div>
          <span className="step-label">Fit Analysis</span>
        </div>
        <div className={`step-item ${step >= 4 ? 'active' : ''}`} onClick={() => step === 4 && setStep(4)}>
          <div className="step-circle">4</div>
          <span className="step-label">Refined Output</span>
        </div>
      </div>

      {/* MAIN CONTAINER */}
      <main className="main-content">
        
        {/* LOADING STATE OVERLAY */}
        {loading ? (
          <div className="glass-panel text-center animate-fade-in" style={{ padding: '60px 40px', maxWidth: '650px', margin: '40px auto' }}>
            <div className="premium-loader-container">
              <div className="spinner-glow">
                <div className="spinner-circle"></div>
                <div className="spinner-inner"></div>
              </div>
              <h3 className="loading-text">{loadingMessage}</h3>
              <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>
                {loadingSubText}
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* STEP 1: UPLOAD & JOB DESCRIPTION */}
            {step === 1 && (
              <div className="animate-fade-in">
                <div className="text-center mb-8">
                  <h1 style={{ marginBottom: '8px' }}>Refine Your CV For Your Next Role</h1>
                  <p style={{ color: 'var(--color-text-muted)', fontSize: '1.1rem', maxWidth: '600px', margin: '0 auto' }}>
                    Upload your profile, paste the job posting details, and let our multi-agent pipeline draft, cross-examine, and compile a tailored resume.
                  </p>
                </div>

                <div className="split-grid">
                  {/* Left Column: Upload Dashboard */}
                  <div className="glass-panel">
                    <h3 className="mb-4">1. Base CV Upload</h3>
                    <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', marginBottom: '20px' }}>
                      Drag and drop your current CV. Supported file formats: PDF, DOCX, MD.
                    </p>

                    <div 
                      className={`dropzone-container ${dragActive ? 'drag-active' : ''}`}
                      onDragEnter={handleDrag}
                      onDragOver={handleDrag}
                      onDragLeave={handleDrag}
                      onDrop={handleDrop}
                      onClick={triggerFileInput}
                    >
                      <input 
                        type="file" 
                        id="file-upload-input" 
                        className="d-none" 
                        style={{ display: 'none' }}
                        onChange={handleFileChange}
                        accept=".pdf,.docx,.md"
                      />
                      
                      {!cvFile ? (
                        <>
                          <div className="upload-icon">↑</div>
                          <p style={{ fontWeight: '600', color: 'var(--color-text-primary)' }}>
                            Drag and drop your file here
                          </p>
                          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                            or click to browse from system files
                          </p>
                        </>
                      ) : (
                        <div className="file-info-box" onClick={(e) => e.stopPropagation()}>
                          <div className="file-details">
                            <span className="file-icon">📄</span>
                            <div style={{ textAlign: 'left' }}>
                              <p className="output-file-name" style={{ margin: 0, textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '200px' }}>
                                {cvFile.name}
                              </p>
                              <span className="output-file-size">{cvFile.size}</span>
                            </div>
                          </div>
                          <button className="btn-remove-file" onClick={removeFile} title="Remove file">
                            ✕
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Column: Job Description Input */}
                  <div className="glass-panel flex-column" style={{ display: 'flex' }}>
                    <h3 className="mb-4">2. Target Position Details</h3>
                    <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', marginBottom: '20px' }}>
                      Provide the details of the job listing. Input a URL or paste raw text description.
                    </p>

                    {/* Toggle split */}
                    <div className="jd-split-toggle">
                      <button 
                        className={`jd-toggle-btn ${isJdUrl ? 'active' : ''}`}
                        onClick={() => { setIsJdUrl(true); setJdInput(''); }}
                      >
                        Job Posting URL
                      </button>
                      <button 
                        className={`jd-toggle-btn ${!isJdUrl ? 'active' : ''}`}
                        onClick={() => { setIsJdUrl(false); setJdInput(''); }}
                      >
                        Paste JD text
                      </button>
                    </div>

                    <div style={{ flex: 1, marginBottom: '24px' }}>
                      {isJdUrl ? (
                        <input
                          type="url"
                          className="input-glass"
                          placeholder="e.g. https://careers.company.com/jobs/senior-python-dev"
                          value={jdInput}
                          onChange={(e) => setJdInput(e.target.value)}
                        />
                      ) : (
                        <textarea
                          className="input-glass"
                          style={{ minHeight: '144px', resize: 'none', height: '100%' }}
                          placeholder="Paste the full job responsibilities, skills, and qualifications here..."
                          value={jdInput}
                          onChange={(e) => setJdInput(e.target.value)}
                        ></textarea>
                      )}
                    </div>

                    <button 
                      className="btn-primary" 
                      onClick={handleStartAnalysis}
                      disabled={!cvFile || !jdInput.trim()}
                      style={{ width: '100%' }}
                    >
                      <span>Analyze Job Fit</span>
                      <span>➔</span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* STEP 2: CV MARKDOWN REVIEW (Human-in-the-loop 1) */}
            {step === 2 && (
              <div className="animate-fade-in">
                <div className="text-center mb-6">
                  <h2>Review Extracted CV Details</h2>
                  <p style={{ color: 'var(--color-text-muted)' }}>
                    Verify or edit the parsed details extracted from your CV. Click proceed once you are satisfied with the structure.
                  </p>
                </div>

                <div className="glass-panel editor-container">
                  {/* Left panel: Raw Markdown Editor */}
                  <div className="flex-column" style={{ display: 'flex', height: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 'bold' }}>
                        Source Markdown
                      </span>
                      <span className="badge badge-success">Editable</span>
                    </div>
                    <textarea
                      className="editor-textarea"
                      value={cvMarkdown}
                      onChange={(e) => setCvMarkdown(e.target.value)}
                    ></textarea>
                  </div>

                  {/* Right panel: Renders Preview */}
                  <div className="flex-column" style={{ display: 'flex', height: '100%' }}>
                    <span style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 'bold', marginBottom: '8px' }}>
                      Formatted Preview
                    </span>
                    <div className="preview-container">
                      <div className="markdown-preview">
                        {renderSimpleMarkdown(cvMarkdown)}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="d-flex justify-between mt-6">
                  <button className="btn-secondary" onClick={() => setStep(1)}>
                    ✕ Cancel
                  </button>
                  <button className="btn-primary" onClick={handleProceedToMatch}>
                    <span>Proceed to Match Analysis</span>
                    <span>➔</span>
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: MATCH REPORT VIEWER (Human-in-the-loop 2) */}
            {step === 3 && matchAnalysis && (
              <div className="animate-fade-in">
                <div className="text-center mb-6">
                  <h2>Fit Analysis & Gap Assessment</h2>
                  <p style={{ color: 'var(--color-text-muted)' }}>
                    A detailed alignment check mapping your skills against the requirements for <strong>{matchAnalysis.target_job_title}</strong>.
                  </p>
                </div>

                {/* Score Banner and Summary */}
                <div className="glass-panel match-header-panel">
                  <MatchScoreRing score={matchAnalysis.match_score} />
                  
                  <div className="match-summary-text">
                    <h3>
                      {matchAnalysis.match_score >= 80 
                        ? 'Strong Fit Candidate' 
                        : matchAnalysis.match_score >= 60 
                        ? 'Potential Fit Candidate' 
                        : 'Moderate Skills Mismatch'}
                    </h3>
                    <p style={{ marginBottom: '12px' }}>
                      Our Match Maker agent compared your CV content with the job requirements. We identified{' '}
                      <strong>{matchAnalysis.strong_matches.length}</strong> strengths and{' '}
                      <strong>{matchAnalysis.required_improvements.length}</strong> core missing skill gaps.
                    </p>
                    {matchAnalysis.match_score < 70 && (
                      <div className="badge badge-danger" style={{ display: 'inline-flex', padding: '6px 12px' }}>
                        ⚠️ Low Match score warning
                      </div>
                    )}
                  </div>
                </div>

                <div className="split-grid mt-6">
                  {/* Left Column: Strengths, Gaps, and Questions */}
                  <div className="flex-column gap-6">
                    {/* Strengths Card */}
                    <div className="glass-panel">
                      <h4 className="report-section-title" style={{ color: 'var(--color-primary)' }}>
                        <span>✓</span> Strong Matches
                      </h4>
                      <ul style={{ paddingLeft: '16px' }}>
                        {matchAnalysis.strong_matches.map((item, i) => (
                          <li key={i} style={{ marginBottom: '8px', color: 'var(--color-text-primary)' }}>{item}</li>
                        ))}
                      </ul>
                    </div>

                    {/* Gaps / Required Improvements Card */}
                    <div className="glass-panel">
                      <h4 className="report-section-title" style={{ color: 'var(--color-accent)' }}>
                        <span>✦</span> Required Improvements
                      </h4>
                      {matchAnalysis.required_improvements.length > 0 ? (
                        <ul style={{ paddingLeft: '16px' }}>
                          {matchAnalysis.required_improvements.map((item, i) => (
                            <li key={i} style={{ marginBottom: '8px', color: 'var(--color-text-primary)' }}>{item}</li>
                          ))}
                        </ul>
                      ) : (
                        <p style={{ fontStyle: 'italic', color: 'var(--color-text-muted)' }}>
                          No critical skill gaps identified.
                        </p>
                      )}
                    </div>

                    {/* Metric Interrogation Qs */}
                    <div className="glass-panel">
                      <h4 className="report-section-title" style={{ color: 'hsl(38, 92%, 50%)' }}>
                        <span>⚖</span> Achievements Interrogation
                      </h4>
                      <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', marginBottom: '16px' }}>
                        To improve impact, define metrics for these achievements before final PDF compilation:
                      </p>
                      <ul style={{ paddingLeft: '16px' }}>
                        {matchAnalysis.follow_up_questions.map((item, i) => (
                          <li key={i} style={{ marginBottom: '8px', fontSize: '0.9rem', color: 'var(--color-text-primary)' }}>
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Right Column: Skills Bar Comparison & Embedded PDF Viewer Mockup */}
                  <div className="flex-column gap-6">
                    {/* Skills Comparison */}
                    <div className="glass-panel">
                      <h4 className="report-section-title">Required vs. Possessed Skills</h4>
                      <div className="match-skills-grid" style={{ gridTemplateColumns: '1fr', gap: '12px' }}>
                        {matchAnalysis.skills_comparison.map((skill, idx) => (
                          <div className="skill-bar-card" key={idx} style={{ padding: '12px' }}>
                            <div className="skill-info">
                              <span className="skill-name">{skill.required_skill}</span>
                              <span 
                                className="badge" 
                                style={{
                                  backgroundColor: skill.possessed ? 'var(--color-primary-glow)' : 'rgba(244, 63, 94, 0.1)',
                                  color: skill.possessed ? 'var(--color-primary)' : 'var(--color-accent)'
                                }}
                              >
                                {skill.possessed ? 'Possessed' : 'Missing'}
                              </span>
                            </div>
                            <div className="skill-status-track">
                              <div 
                                className="skill-status-fill"
                                style={{
                                  width: skill.possessed ? '100%' : '15%',
                                  backgroundColor: skill.possessed ? 'var(--color-primary)' : 'var(--color-accent)'
                                }}
                              ></div>
                            </div>
                            <span className="skill-details-text">{skill.details}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* PDF Mockup Section */}
                    <div className="glass-panel flex-column">
                      <h4 className="report-section-title" style={{ marginBottom: '12px' }}>
                        <span>📁</span> Match Report Document Preview
                      </h4>
                      <div className="pdf-viewer-container">
                        <div className="pdf-page-mock">
                          <div className="pdf-page-header">
                            <span className="pdf-page-title">Fit Report</span>
                            <span className="pdf-page-subtitle">ResumeForge Systems</span>
                          </div>
                          
                          <div style={{ fontSize: '0.75rem', fontWeight: 'bold', marginBottom: '12px' }}>
                            Target: {matchAnalysis.target_job_title}
                          </div>

                          <div className="pdf-score-badges">
                            <div className="pdf-score-item">
                              <div className="pdf-score-num">{matchAnalysis.match_score}%</div>
                              <div className="pdf-score-lbl">Fit Score</div>
                            </div>
                            <div className="pdf-score-item">
                              <div className="pdf-score-num">{matchAnalysis.strong_matches.length}</div>
                              <div className="pdf-score-lbl">Strengths</div>
                            </div>
                            <div className="pdf-score-item">
                              <div className="pdf-score-num">{matchAnalysis.required_improvements.length}</div>
                              <div className="pdf-score-lbl">Gaps</div>
                            </div>
                          </div>

                          <div className="pdf-section-title">Core Strengths</div>
                          {matchAnalysis.strong_matches.map((item, idx) => (
                            <div className="pdf-bullet" key={idx}>{item}</div>
                          ))}

                          <div className="pdf-section-title">Identified Gaps</div>
                          {matchAnalysis.required_improvements.map((item, idx) => (
                            <div className="pdf-bullet" key={idx}>{item}</div>
                          ))}

                          <div className="pdf-watermark">FORGE-VERIFIED</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Interview Prep Accordion */}
                <div className="glass-panel mt-6">
                  <h4 className="report-section-title" style={{ color: 'var(--color-primary)' }}>
                    <span>✦</span> Custom Interview Prep Assistant (5 Tailored Questions)
                  </h4>
                  <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', marginBottom: '20px' }}>
                    Based on the skills gaps between your CV and the JD, here are questions the interviewer may ask, and how you should answer.
                  </p>
                  
                  <div>
                    {matchAnalysis.interview_questions.map((item, index) => (
                      <div className="qa-card" key={index}>
                        <div className="qa-question">
                          <span className="qa-number">Q{index + 1}:</span>
                          <span>{item.question}</span>
                        </div>
                        <div className="qa-talking-points">
                          {item.talking_points.map((tp, idx) => (
                            <li className="talking-point-item" key={idx}>{tp}</li>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="d-flex justify-between mt-6">
                  <button className="btn-secondary" onClick={handleBackToEditor}>
                    ◀ Edit CV Details
                  </button>
                  <button className="btn-primary" onClick={handleApproveAndGenerate}>
                    <span>Approve & Optimize Resume</span>
                    <span>✓</span>
                  </button>
                </div>
              </div>
            )}

            {/* STEP 4: FINAL REFINED OUTPUTS */}
            {step === 4 && finalOutputs && (
              <div className="animate-fade-in">
                <div className="text-center mb-6">
                  <h2>Optimized Files Compiled Successfully!</h2>
                  <div className="d-flex align-center justify-between" style={{ maxWidth: '400px', margin: '12px auto' }}>
                    <span className="badge badge-success" style={{ padding: '6px 14px', fontSize: '0.85rem' }}>
                      ATS Score: {finalOutputs.ats_score}/100
                    </span>
                    <span style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
                      Requirements satisfied (Score &gt;= 90)
                    </span>
                  </div>
                </div>

                <div className="final-tab-layout">
                  {/* Left Column: File Switchers & Actions */}
                  <div className="final-side-panel">
                    <div 
                      className={`output-file-card ${activeFinalTab === 'cv' ? 'active' : ''}`}
                      onClick={() => setActiveFinalTab('cv')}
                    >
                      <div className="output-file-icon">📄</div>
                      <div className="output-file-info">
                        <p className="output-file-name">CV_Optimized.pdf</p>
                        <span className="output-file-size">148 KB</span>
                      </div>
                    </div>

                    <div 
                      className={`output-file-card ${activeFinalTab === 'cl' ? 'active' : ''}`}
                      onClick={() => setActiveFinalTab('cl')}
                    >
                      <div className="output-file-icon">✉</div>
                      <div className="output-file-info">
                        <p className="output-file-name">Cover_Letter.pdf</p>
                        <span className="output-file-size">84 KB</span>
                      </div>
                    </div>

                    {/* Download Buttons */}
                    <div className="glass-panel flex-column gap-2 mt-4" style={{ padding: '16px' }}>
                      <a 
                        href={`#download-${activeFinalTab}`} 
                        className="btn-primary"
                        style={{ width: '100%' }}
                        onClick={(e) => { e.preventDefault(); alert(`Downloading final_${activeFinalTab === 'cv' ? 'cv' : 'cover_letter'}.pdf...`); }}
                      >
                        <span>Download {activeFinalTab === 'cv' ? 'CV' : 'Cover Letter'}</span>
                        <span>↓</span>
                      </a>
                      
                      <button 
                        className="btn-secondary" 
                        style={{ width: '100%', padding: '10px' }}
                        onClick={() => { alert("Downloading both files in a zip package..."); }}
                      >
                        Download All (ZIP)
                      </button>
                    </div>

                    <button className="btn-secondary mt-4" onClick={handleReset}>
                      ◀ Start New Profile
                    </button>
                  </div>

                  {/* Right Column: PDF Preview Mock */}
                  <div className="glass-panel pdf-preview-box">
                    <div className="d-flex justify-between align-center" style={{ borderBottom: '1px solid var(--color-border-glass)', paddingBottom: '12px' }}>
                      <h4 style={{ margin: 0 }}>
                        {activeFinalTab === 'cv' ? 'Optimized Resume Document' : 'Tailored Cover Letter'}
                      </h4>
                      <span className="badge badge-success">LaTeX-compiled</span>
                    </div>

                    {activeFinalTab === 'cv' ? (
                      /* Resume preview mock */
                      <div className="cv-a4-page animate-fade-in">
                        <div className="cv-a4-name">John Doe</div>
                        <div className="cv-a4-pos">Senior Python Developer</div>
                        <div className="cv-a4-contact">
                          john.doe@example.com | +1-555-0199 | Austin, TX | github.com/johndoe
                        </div>

                        <div className="cv-a4-section">
                          <div className="cv-a4-section-title">Professional Summary</div>
                          <div style={{ color: '#444', lineHeight: '1.4', fontSize: '0.8rem' }}>
                            Detail-oriented and results-driven Senior Python Developer with a strong track record of designing, building, and maintaining scalable web applications. Proficient in **Python**, **FastAPI**, **Docker**, and cloud technologies. Strong background in microservices architectures and database design.
                          </div>
                        </div>

                        <div className="cv-a4-section">
                          <div className="cv-a4-section-title">Work Experience</div>
                          <div className="cv-a4-entry-header">
                            <span>Senior Python Developer</span>
                            <span>2024 – Present</span>
                          </div>
                          <div className="cv-a4-entry-org">TechInnovate Corp — Austin, TX</div>
                          <div className="cv-a4-bullet">
                            Led technology implementation for a real-time data analysis platform, integrating **FastAPI** web framework to handle 10k+ concurrent requests.
                          </div>
                          <div className="cv-a4-bullet">
                            Optimized third-party API analytical loops, increasing customer conversion and sales metrics by 22% over six months.
                          </div>
                          <div className="cv-a4-bullet">
                            Managed a core team of 5 backend developers, overseeing deployment pipelines and container testing configurations.
                          </div>

                          <div className="cv-a4-entry-header" style={{ marginTop: '12px' }}>
                            <span>Software Developer</span>
                            <span>2022 – 2024</span>
                          </div>
                          <div className="cv-a4-entry-org">DevSystems Inc — Boston, MA</div>
                          <div className="cv-a4-bullet">
                            Built, tested, and containerized Python web services using **Docker** and **Kubernetes** to achieve 99.9% uptime.
                          </div>
                          <div className="cv-a4-bullet">
                            Implemented rigorous testing patterns using **pytest** and mock fixtures, elevating total **Unit Testing** coverage from 60% to 92%.
                          </div>
                        </div>

                        <div className="cv-a4-section">
                          <div className="cv-a4-section-title">Education</div>
                          <div className="cv-a4-entry-header">
                            <span>Bachelor of Science in Computer Science</span>
                            <span>2018 – 2022</span>
                          </div>
                          <div className="cv-a4-entry-org">University of Engineering (GPA: 3.8/4.0, Cum Laude)</div>
                        </div>

                        <div className="cv-a4-section">
                          <div className="cv-a4-section-title">Skills</div>
                          <div className="cv-a4-skills-list">
                            <span className="cv-a4-skills-cat">Languages:</span> Python, JavaScript, SQL, Bash. <br />
                            <span className="cv-a4-skills-cat">Frameworks & tools:</span> FastAPI, React, Node.js, Docker, Kubernetes, AWS, pytest.
                          </div>
                        </div>
                      </div>
                    ) : (
                      /* Cover letter preview mock */
                      <div className="cv-a4-page animate-fade-in" style={{ padding: '50px 45px', fontSize: '0.85rem', color: '#333' }}>
                        <div style={{ float: 'right', textAlign: 'right', fontSize: '0.75rem', color: '#7f8c8d' }}>
                          July 1, 2026 <br />
                          Austin, Texas
                        </div>
                        <div style={{ fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '24px' }}>John Doe</div>

                        <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '24px' }}>
                          To, <br />
                          Hiring Manager <br />
                          Apex Solutions <br />
                        </div>

                        <div style={{ fontWeight: 'bold', marginBottom: '14px' }}>
                          RE: Application for Senior Python Developer position
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.8rem', lineHeight: '1.5', color: '#444' }}>
                          <p>Dear Hiring Team,</p>
                          <p>
                            I am writing to express my strong interest in the Senior Python Developer position at Apex Solutions. With a solid foundation in software development and containerized cloud systems, along with my hands-on experience in building microservices, I am confident in my ability to make an immediate impact on your technical initiatives.
                          </p>
                          <p>
                            During my tenure at TechInnovate Corp, I led key developments using FastAPI and Python to structure our analytical platform services, supporting a large scale of requests with low latency. Containerization using Docker and orchestrating services with Kubernetes has been a core pillar of my design philosophy. Additionally, I prioritize code quality, having led testing audits using pytest to maintain unit testing coverage above 90%.
                          </p>
                          <p>
                            Apex Solutions' focus on highly reliable cloud platforms aligns perfectly with my professional background. I would welcome the opportunity to discuss how my skill set and experiences match your team's requirements in more detail. Thank you for your time and consideration.
                          </p>
                          <p style={{ marginTop: '20px' }}>
                            Sincerely, <br />
                            <strong>John Doe</strong>
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
