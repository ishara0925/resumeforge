import os
import shutil
import uuid
import subprocess
import json
from typing import List, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Imports from existing agents
from agents.cv_parser import (
    parse_cv_to_markdown_async,
    extract_cv_variables_from_markdown,
    extract_text_from_file
)
from agents.jd_parser import (
    parse_jd_async,
    scrape_url
)
from agents.match_maker import (
    match_cv_and_jd_async,
    generate_match_chart
)
from agents.cv_writer import write_cv_async
from agents.cover_letter_agent import generate_cover_letter_async
from agents.verification_agent import (
    verify_ats_async,
    generate_match_report_pdf
)

app = FastAPI(title="ResumeForge API", description="API backend for ResumeForge CV tailoring agent workflow.")

# CORS settings to allow frontend development server to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants & Paths
UPLOAD_DIR = os.path.join("data", "uploads")
OUTPUT_DIR = os.path.join("data", "output")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Mount static files to serve the output PDFs and match charts
app.mount("/static", StaticFiles(directory="data/output"), name="static")

import re

def escape_raw_ampersands(latex_code: str) -> str:
    """Escapes any raw '&' character that is not already escaped as '\&'."""
    return re.sub(r'(?<!\\)&', r'\&', latex_code)

def compile_latex(tex_path):
    """Compiles a LaTeX document twice to resolve links, using xelatex if available."""
    xelatex_path = shutil.which("xelatex")
    if not xelatex_path:
        # Check standard Windows paths
        possible_paths = [
            r"C:\Program Files\MiKTeX\miktex\bin\x64\xelatex.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\xelatex.exe")
        ]
        for p in possible_paths:
            if os.path.exists(p):
                xelatex_path = p
                break
                
    if not xelatex_path:
        print(f"[Warning] 'xelatex' command not found on system PATH or default MiKTeX paths. Skipping compilation for: {tex_path}")
        return False
        
    out_dir = os.path.dirname(tex_path) or "."
    
    # Copy awesome-cv.cls to out_dir so that standard compilation works out-of-the-box
    cls_src = os.path.join("templates", "awesome-cv.cls")
    if os.path.exists(cls_src):
        os.makedirs(out_dir, exist_ok=True)
        shutil.copy2(cls_src, os.path.join(out_dir, "awesome-cv.cls"))
        
    print(f"Compiling {tex_path} to PDF using: {xelatex_path}...")
    try:
        # Prepend the directory of the resolved xelatex to environment PATH
        xelatex_dir = os.path.dirname(xelatex_path)
        env = os.environ.copy()
        if xelatex_dir:
            env["PATH"] = xelatex_dir + os.pathsep + env.get("PATH", "")
            
        # Add templates folder to TEXINPUTS for safety
        path_sep = ";" if os.name == "nt" else ":"
        env["TEXINPUTS"] = f".{path_sep}{os.path.abspath('templates')}{path_sep}" + env.get("TEXINPUTS", "")
            
        # Run twice to resolve references/elements
        for i in range(2):
            subprocess.run(
                [xelatex_path, "-interaction=nonstopmode", f"-output-directory={out_dir}", tex_path],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
        print(f"Successfully compiled: {os.path.splitext(tex_path)[0]}.pdf")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[Error] Failed compiling {tex_path}. Exit code: {e.returncode}")
        print(f"STDOUT excerpt:\n{e.stdout[:800]}\n")
        return False

# Pydantic Request Models
class ParseJdRequest(BaseModel):
    jdInput: str
    isUrl: bool = False

class MatchReportRequest(BaseModel):
    cvMarkdown: str
    jdDetails: dict

class GenerateFinalRequest(BaseModel):
    cvMarkdown: str
    matchAnalysis: dict

# Endpoints
@app.post("/api/upload-cv")
async def upload_cv(file: UploadFile = File(...)):
    # Save the file temporarily
    file_ext = os.path.splitext(file.filename)[1]
    temp_filename = f"{uuid.uuid4()}{file_ext}"
    temp_file_path = os.path.join(UPLOAD_DIR, temp_filename)
    
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Parse CV using agent logic
        cv_markdown = await parse_cv_to_markdown_async(temp_file_path)
        return {
            "success": True,
            "cvMarkdown": cv_markdown,
            "filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse CV: {str(e)}")
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.post("/api/parse-jd")
async def parse_jd(request: ParseJdRequest):
    try:
        if request.isUrl:
            print(f"[API] Scraping Job Description URL: {request.jdInput}")
            raw_text = scrape_url(request.jdInput)
            if not raw_text:
                raise HTTPException(status_code=400, detail="Failed to scrape Job Description from URL")
        else:
            raw_text = request.jdInput
            
        print("[API] Parsing Job Description text using agent...")
        jd_details = await parse_jd_async(raw_text)
        
        # Format the response matching what frontend api.js expects:
        # jdDetails: { company_name, position, required_skills, preferred_experience, raw_text }
        formatted_jd = {
            "company_name": jd_details.company_name,
            "position": jd_details.position,
            "required_skills": jd_details.skills,
            "preferred_experience": ", ".join(jd_details.experience_requirements),
            "raw_text": raw_text
        }
        
        return {
            "success": True,
            "jdDetails": formatted_jd
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse JD: {str(e)}")

@app.post("/api/get-match-report")
async def get_match_report(request: MatchReportRequest):
    try:
        # Convert jdDetails back to the JSON format expected by match_cv_and_jd_async
        jd_details_json = json.dumps(request.jdDetails)
        
        print("[API] Running Match Maker agent...")
        match_analysis = await match_cv_and_jd_async(request.cvMarkdown, jd_details_json)
        
        # Save a comparison chart to data/output/match_chart.png
        chart_path = os.path.join(OUTPUT_DIR, "match_chart.png")
        generate_match_chart(match_analysis.skills_comparison, chart_path)
        
        # Convert response to dictionary structure matching MatchAnalysis
        analysis_dict = match_analysis.model_dump()
        
        # Inject company_name and raw_text from jdDetails so they are preserved
        analysis_dict["company_name"] = request.jdDetails.get("company_name") or "Company"
        analysis_dict["raw_text"] = request.jdDetails.get("raw_text") or ""
        
        return {
            "success": True,
            "matchAnalysis": analysis_dict
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run Match Maker: {str(e)}")

@app.post("/api/generate-final")
async def generate_final(request: GenerateFinalRequest):
    try:
        cv_markdown = request.cvMarkdown
        match_analysis = request.matchAnalysis
        
        # Extract candidate details for file naming
        user_name, user_name_with_initials = extract_cv_variables_from_markdown(cv_markdown)
        
        # Extract company and job details
        company_name = match_analysis.get("company_name") or "Company"
        position = match_analysis.get("target_job_title") or "Position"
        
        # Create a unique output directory for this run
        job_dir_name = f"{user_name}_{company_name}_{position}".replace(" ", "_")
        job_dir_path = os.path.join(OUTPUT_DIR, job_dir_name)
        os.makedirs(job_dir_path, exist_ok=True)
        
        # Save edited CV Markdown to job-specific directory
        cv_md_path = os.path.join(job_dir_path, "cv_markdown.md")
        with open(cv_md_path, "w", encoding="utf-8") as f:
            f.write(cv_markdown)
            
        # ATS Loop setup
        loop_count = 0
        max_loops = 3
        feedback_str = ""
        ats_score = 0
        latex_cv = ""
        
        # Target file names
        cv_filename = f"CV_{user_name}_{company_name}_{position}.tex"
        cv_tex_path = os.path.join(job_dir_path, cv_filename)
        cv_pdf_path = cv_tex_path.replace(".tex", ".pdf")
        
        # Extract target job description text for verification agent
        jd_text = match_analysis.get("raw_text") or ""
        
        # Write & Compile CV, Verify and loop to optimize
        print("[API] Starting ATS Optimization Loop...")
        while loop_count <= max_loops:
            print(f"[API] Loop {loop_count}: Generating LaTeX CV...")
            latex_cv = await write_cv_async(cv_markdown, feedback_str)
            latex_cv = escape_raw_ampersands(latex_cv)
            
            with open(cv_tex_path, "w", encoding="utf-8") as f:
                f.write(latex_cv)
                
            # Compile to PDF
            compilation_success = compile_latex(cv_tex_path)
            if not compilation_success:
                print(f"[API Warning] LaTeX compilation failed at loop {loop_count}")
                break
                
            # Extract text from compiled PDF
            cv_extracted_text = extract_text_from_file(cv_pdf_path)
            
            # Verify ATS compatibility
            print("[API] Running simulated ATS verification on compiled text...")
            verification = await verify_ats_async(cv_extracted_text, jd_text)
            ats_score = verification.ats_score
            missing_exact_keywords = verification.missing_exact_keywords or []
            formatting_errors = verification.formatting_errors or []
            
            if ats_score >= 90 or loop_count == max_loops:
                print(f"[API] Optimization completed. Score: {ats_score}/100")
                break
                
            loop_count += 1
            print(f"[API] Score {ats_score}/100 is below 90. Refining CV (Iteration {loop_count} of {max_loops})...")
            
            # Construct strict instructions with missing_exact_keywords and formatting_errors
            feedback_str = "Refine the LaTeX formatting and keywords to address the following issues:\n"
            if missing_exact_keywords:
                feedback_str += "Inject the following exact missing keywords/phrases into the CV: " + ", ".join([f"'{kw}'" for kw in missing_exact_keywords]) + "\n"
            if formatting_errors:
                feedback_str += "Fix the following ATS formatting/parsing errors:\n" + "\n".join([f"- {err}" for err in formatting_errors]) + "\n"
        
        # Generate Cover Letter
        print("[API] Generating Cover Letter...")
        jd_details_json = json.dumps(match_analysis)
        cover_letter = await generate_cover_letter_async(cv_markdown, jd_details_json)
        cover_letter = escape_raw_ampersands(cover_letter)
        
        # Save Cover Letter
        cl_filename = f"COVER_{user_name_with_initials}_{company_name}_{position}.tex"
        cl_tex_path = os.path.join(job_dir_path, cl_filename)
        cl_pdf_path = cl_tex_path.replace(".tex", ".pdf")
        
        with open(cl_tex_path, "w", encoding="utf-8") as f:
            f.write(cover_letter)
            
        compile_latex(cl_tex_path)
        
        # Map file paths to URLs relative to /static prefix
        cv_pdf_url = f"http://localhost:8000/static/{job_dir_name}/{cv_filename.replace('.tex', '.pdf')}"
        cl_pdf_url = f"http://localhost:8000/static/{job_dir_name}/{cl_filename.replace('.tex', '.pdf')}"
        
        return {
            "success": True,
            "cvPdfUrl": cv_pdf_url,
            "coverLetterPdfUrl": cl_pdf_url,
            "atsScore": ats_score,
            "cvMarkdown": cv_markdown,
            "latexCv": latex_cv,
            "coverLetter": cover_letter
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate final outputs: {str(e)}")
