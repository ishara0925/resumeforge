import os
import json
import asyncio
import shutil
import subprocess
from typing import Optional, List
from dotenv import load_dotenv
from google.adk import Context, Workflow
from google.adk.workflow import node
from google.adk.events import RequestInput, Event
from google.adk.runners import InMemoryRunner
from google.adk.apps import App
from google.genai import types

# Load API keys from environment/dotenv
load_dotenv()

# Import our custom agents (async versions to avoid nesting event loop issues)
from agents.cv_parser import (
    parse_cv_to_details_async,
    cv_details_to_markdown,
    parse_cv_to_markdown_async,
    get_parsed_cv_path,
    list_parsed_cv_files,
    extract_cv_variables_from_markdown
)
from agents.jd_parser import (
    parse_jd_async,
    process_jds_step1_scrape,
    check_for_scraping_failures,
    process_jds_step2_parse,
    read_jd_links
)
from agents.match_maker import match_cv_and_jd_async, generate_match_chart, generate_match_report_pdf
from agents.cv_writer import write_cv_async
from agents.cover_letter_agent import generate_cover_letter_async
from agents.verification_agent import verify_ats_async, ATSVerificationResult

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

# --- ADK Workflow Node Definitions ---

@node(name="parse_cv_node")
async def parse_cv_node(cv_file_path: str) -> str:
    """Extracts CV text and formats it into Markdown, respecting cache."""
    print(f"[Node: CV Parser] Extracting & parsing CV from: {cv_file_path}")
    return await parse_cv_to_markdown_async(cv_file_path)

@node(name="select_cv_node", rerun_on_resume=False)
async def select_cv_node(ctx: Context, options: List[str]):
    """Pauses execution and requests the user to select from available parsed CVs."""
    options_str = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
    yield RequestInput(
        message=(
            "=== HUMAN-IN-THE-LOOP: SELECT PARSED CV ===\n"
            "Multiple parsed CV files were found in the input folder. Please select one:\n"
            f"{options_str}\n"
            "Enter the number or filename of the CV to use: "
        ),
    )

@node(name="handle_scraping_failures_node", rerun_on_resume=False)
async def handle_scraping_failures_node(ctx: Context, failed_indices: List[int]):
    """Pauses execution and asks the user to manually copy and paste the JD text."""
    indices_str = ", ".join([f"jd_raw_{idx}.md" for idx in failed_indices])
    yield RequestInput(
        message=(
            "=== HUMAN-IN-THE-LOOP: SCRAPING FAILURES ===\n"
            f"WARNING: Scraping failed or returned empty results for the following files: {indices_str}\n"
            "Please manually copy and paste the job description text into the respective empty files inside 'data/input/'.\n"
            "Once you have updated the files, press Enter/send empty here to proceed."
        ),
        payload={"failed_indices": failed_indices}
    )

@node(name="edit_cv_markdown_node", rerun_on_resume=False)
async def edit_cv_markdown_node(ctx: Context, initial_markdown: str):
    """Pauses execution and requests the user to review/edit the CV Markdown."""
    yield RequestInput(
        message=(
            "=== HUMAN-IN-THE-LOOP: CV MARKDOWN REVIEW ===\n"
            "Review the parsed CV markdown below. If it looks correct, press Enter/send empty to proceed.\n"
            "Otherwise, edit it and submit your revised Markdown CV:\n\n"
            f"{initial_markdown}\n"
        ),
        payload={"markdown": initial_markdown}
    )

@node(name="parse_jd_node")
async def parse_jd_node(jd_string: str):
    """Extracts required skills and experience from the Job Description."""
    print("[Node: JD Parser] Parsing Job Description details...")
    return await parse_jd_async(jd_string)

@node(name="match_maker_node")
async def match_maker_node(ctx: Context, cv_markdown: str, jd_details_json: str):
    """Compares CV and Job Description to output strong matches, gaps, and a match score."""
    print("[Node: Match Maker] Matching candidate CV against JD requirements...")
    match_result = await match_cv_and_jd_async(cv_markdown, jd_details_json)
    
    # Save the match report and chart inside the match maker agent/node using the state variables
    directory_path = ctx.state.get("directory_path", "data/output")
    os.makedirs(directory_path, exist_ok=True)
    
    chart_path = os.path.join(directory_path, "match_chart.png")
    generate_match_chart(match_result.skills_comparison, chart_path)
    
    report_pdf_path = os.path.join(directory_path, "Match_Report.pdf")
    generate_match_report_pdf(match_result, chart_path, report_pdf_path)
    
    ctx.state["chart_path"] = chart_path
    ctx.state["report_pdf_path"] = report_pdf_path
    
    return match_result

@node(name="generate_chart_node")
def generate_chart_node(skills_comparison: list, chart_path: str):
    """Saves a visual bar chart comparing required vs possessed skills."""
    print(f"[Node: Chart Generator] Saving comparison chart to {chart_path}...")
    generate_match_chart(skills_comparison, chart_path)
    return True

@node(name="ask_match_approval", rerun_on_resume=False)
async def ask_match_approval(ctx: Context, score: int, chart_path: str, report_pdf_path: str = ""):
    """Pauses execution if match score is below 70 to request user's approval to proceed."""
    msg = (
        f"=== HUMAN-IN-THE-LOOP: LOW MATCH APPROVAL ===\n"
        f"WARNING: The calculated match score is {score}/100 (below threshold of 70).\n"
    )
    if report_pdf_path:
        msg += f"A detailed match report has been generated at {report_pdf_path}. Please review it before proceeding.\n"
    msg += f"A visual breakdown has been saved to: {chart_path}\n"
    msg += "Do you want to proceed with this candidate anyway? (Type 'yes' or 'no'): "
    
    yield RequestInput(
        message=msg,
        payload={"score": score, "chart_path": chart_path, "report_pdf_path": report_pdf_path}
    )

@node(name="cv_writer_node")
async def cv_writer_node(ctx: Context, cv_markdown: str, feedback_str: str) -> str:
    """Generates LaTeX CV using cv_writer agent."""
    print("[Node: CV Writer] Drafting LaTeX CV...")
    latex_cv = await write_cv_async(cv_markdown, feedback_str)
    
    # Save raw LaTeX file to job-specific directory
    user_name = ctx.state.get("USER_NAME", "Candidate")
    company_name = ctx.state.get("COMPANY_NAME", "Company")
    position = ctx.state.get("POSITION", "Position")
    directory_path = ctx.state.get("directory_path", "data/output")
    
    if directory_path:
        os.makedirs(directory_path, exist_ok=True)
        filename = f"CV_{user_name}_{company_name}_{position}.tex"
        filepath = os.path.join(directory_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(latex_cv)
        print(f"[Node: CV Writer] Saved raw LaTeX CV to: {filepath}")
        
    return latex_cv

@node(name="verification_node")
async def verification_node(latex_cv: str, jd_text: str):
    """Simulates ATS compatibility check and returns verification results."""
    print("[Node: Verification] Running simulated ATS compatibility check with TF-IDF keyword check...")
    return await verify_ats_async(latex_cv, jd_text)

@node(name="cover_letter_node")
async def cover_letter_node(ctx: Context, cv_markdown: str, jd_details_json: str) -> str:
    """Generates a tailored cover letter."""
    print("[Node: Cover Letter] Drafting cover letter...")
    cover_letter = await generate_cover_letter_async(cv_markdown, jd_details_json)
    
    # Save cover letter to job-specific directory
    user_name_with_initials = ctx.state.get("USER_NAME_WITH_INITIALS", "Candidate")
    company_name = ctx.state.get("COMPANY_NAME", "Company")
    position = ctx.state.get("POSITION", "Position")
    directory_path = ctx.state.get("directory_path", "data/output")
    
    if directory_path:
        os.makedirs(directory_path, exist_ok=True)
        filename = f"COVER_{user_name_with_initials}_{company_name}_{position}.tex"
        filepath = os.path.join(directory_path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(cover_letter)
        print(f"[Node: Cover Letter] Saved cover letter LaTeX to: {filepath}")
        
    return cover_letter

# --- Main ADK Orchestrator Workflow ---

class SafeAccess:
    def __init__(self, data):
        self._data = data if isinstance(data, dict) else {}
        self._obj = data
    def __getattr__(self, name):
        if hasattr(self._obj, name):
            return getattr(self._obj, name)
        return self._data.get(name)
    def model_dump_json(self):
        if hasattr(self._obj, "model_dump_json"):
            return self._obj.model_dump_json()
        return json.dumps(self._data)

@node(name="kero_cv_workflow", rerun_on_resume=True)
async def kero_cv_workflow(ctx: Context, node_input: str) -> str:
    """Main dynamic workflow coordinating the CV / JD parsing, matching, visual generation, and ATS iteration loop."""
    # 1. Parse Input
    try:
        data = json.loads(node_input)
        cv_file_path = data.get("cv_file_path", "")
        jd_string = data.get("jd_string", "")
        ctx.state["cv_file_path"] = cv_file_path
        ctx.state["jd_string"] = jd_string
        ctx.state["jd_text"] = jd_string
    except Exception as e:
        raise ValueError(
            "Workflow input must be a JSON-formatted string with optional 'cv_file_path' and 'jd_string' keys. "
            f"Parsing Error: {e}"
        )

    # STEP 1: Parse CV
    if cv_file_path and cv_file_path.strip():
        # User provided the CV file path: use parse_cv_node (which handles cache/LLM)
        raw_md = await ctx.run_node(parse_cv_node)
    else:
        # User did not provide the CV file path: check data/input directory
        input_dir = os.path.join("data", "input")
        os.makedirs(input_dir, exist_ok=True)
        parsed_files = list_parsed_cv_files(input_dir)
        if not parsed_files:
            raise ValueError(
                "No parsed CV files (.md) found in data/input/ directory, and no CV file path was provided. "
                "Please place a parsed CV markdown file in data/input/ or provide a CV file path."
            )
        
        if len(parsed_files) == 1:
            selected_file = parsed_files[0]
            selected_path = os.path.join(input_dir, selected_file)
            print(f"[Workflow] Single parsed CV found: {selected_path}. Proceeding with it.")
            with open(selected_path, "r", encoding="utf-8") as f:
                raw_md = f.read()
        else:
            # Multiple parsed CVs are available! Ask user to select.
            selection = await ctx.run_node(select_cv_node, options=parsed_files)
            
            selected_index = 0
            try:
                val = selection.strip()
                if val.isdigit():
                    idx = int(val) - 1
                    if 0 <= idx < len(parsed_files):
                        selected_index = idx
                else:
                    if val in parsed_files:
                        selected_index = parsed_files.index(val)
            except Exception:
                pass
            
            selected_file = parsed_files[selected_index]
            selected_path = os.path.join(input_dir, selected_file)
            print(f"[Workflow] Selected CV file: {selected_path}")
            with open(selected_path, "r", encoding="utf-8") as f:
                raw_md = f.read()

    # STEP 2: HITL Pause - CV Markdown Review
    ctx.state["initial_markdown"] = raw_md
    user_edited_cv = await ctx.run_node(edit_cv_markdown_node)
    if user_edited_cv and user_edited_cv.strip() and user_edited_cv.strip().lower() not in ("yes", "y", "proceed", "ok"):
        cv_markdown = user_edited_cv.strip()
    else:
        cv_markdown = raw_md
    ctx.state["cv_markdown"] = cv_markdown

    # STEP 3: Parse Job Descriptions (Scraping and Requirements Extraction)
    links = read_jd_links()
    if not links:
        if jd_string and jd_string.strip():
            print("[Workflow] No links in jd_links.md but jd_string was provided. Using jd_string as fallback.")
            raw_path = os.path.join("data", "input", "jd_raw_1.md")
            os.makedirs(os.path.dirname(raw_path), exist_ok=True)
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(jd_string)
            results = [{
                "index": 1,
                "url": "local_fallback",
                "raw_path": raw_path,
                "success": True
            }]
        else:
            raise ValueError(
                "No JD links found in data/input/jd_links.md and no JD string was provided. "
                "Please add a URL to data/input/jd_links.md or provide a JD string."
            )
    else:
        # Run scraping step
        results = process_jds_step1_scrape()
        failed_indices = check_for_scraping_failures(results)
        
        while failed_indices:
            print(f"[Workflow] Scraping failures detected for indices: {failed_indices}")
            # Pause and request manual copy-paste
            await ctx.run_node(handle_scraping_failures_node, failed_indices=failed_indices)
            
            # Recheck if they are still failing/empty
            rechecked_failures = check_for_scraping_failures(results)
            if rechecked_failures == failed_indices:
                # If they didn't modify anything but pressed proceed, check if we have a fallback jd_string
                if jd_string and jd_string.strip():
                    print("[Workflow] Manual pasting skipped. Filling empty JD files with fallback jd_string.")
                    for idx in failed_indices:
                        raw_path = os.path.join("data", "input", f"jd_raw_{idx}.md")
                        with open(raw_path, "w", encoding="utf-8") as f:
                            f.write(jd_string)
                    break
                else:
                    raise ValueError(
                        f"Scraping failed for JDs: {failed_indices} and no content was pasted. "
                        "Please fill the empty files or provide a fallback JD string."
                    )
            failed_indices = rechecked_failures
            
    # Now run step 2: LLM parsing
    parsed_jd_paths = await process_jds_step2_parse(results)

    batch_results = []
    
    # Process each Job Description in a loop
    for idx, parsed_path in enumerate(parsed_jd_paths, start=1):
        print(f"\n==================================================")
        print(f" Processing Job Description {idx}/{len(parsed_jd_paths)}")
        print(f"==================================================")
        
        with open(parsed_path, "r", encoding="utf-8") as f:
            jd_details_dict = json.load(f)
            
        jd_details_json = json.dumps(jd_details_dict)
        ctx.state["jd_details_json"] = jd_details_json
        
        # Extract job-specific variables
        company_name = jd_details_dict.get("company_name", "UnknownCompany")
        position = jd_details_dict.get("position", "UnknownPosition")
        
        # Extract candidate names
        user_name, user_name_with_initials = extract_cv_variables_from_markdown(cv_markdown)
        
        # Output directory formatting
        directory_path = f"data/output/{company_name}_{position}"
        os.makedirs(directory_path, exist_ok=True)
        
        # Pass variables down in the state object to the Match Maker, CV Writer, and Cover Letter agents
        ctx.state["USER_NAME"] = user_name
        ctx.state["USER_NAME_WITH_INITIALS"] = user_name_with_initials
        ctx.state["COMPANY_NAME"] = company_name
        ctx.state["POSITION"] = position
        ctx.state["directory_path"] = directory_path
        
        # Get raw JD text for ATS verification
        raw_jd_path = os.path.join("data", "input", f"jd_raw_{idx}.md")
        with open(raw_jd_path, "r", encoding="utf-8") as f:
            current_jd_text = f.read()
        ctx.state["jd_text"] = current_jd_text
        
        # STEP 4: Match Making (this will also generate chart and Match_Report.pdf inside directory_path)
        match_result = SafeAccess(await ctx.run_node(match_maker_node))
        chart_path = ctx.state["chart_path"]
        report_pdf_path = ctx.state["report_pdf_path"]
        
        # STEP 5: HITL Pause - Low score check (< 70)
        if match_result.match_score < 70:
            ctx.state["score"] = match_result.match_score
            ctx.state["chart_path"] = chart_path
            ctx.state["report_pdf_path"] = report_pdf_path
            approval = await ctx.run_node(ask_match_approval)
            if approval.strip().lower() not in ("yes", "y", "approve", "proceed", "ok"):
                print(f"[Workflow] Aborted by user for JD {idx} due to low match score.")
                continue
                
        # STEP 6 & 8: CV Writer & ATS Verification Loop (Score < 90)
        loop_count = 0
        max_loops = 2
        latex_cv = ""
        ats_score = 0
        
        # Initial draft
        feedback_str = "Initial draft based on CV parser and match analysis."
        ctx.state["feedback_str"] = feedback_str
        latex_cv = await ctx.run_node(cv_writer_node)
        ctx.state["latex_cv"] = latex_cv
        
        # Simulated ATS Check
        verification = SafeAccess(await ctx.run_node(verification_node))
        ats_score = verification.ats_score
        missing_exact_keywords = verification.missing_exact_keywords or []
        formatting_errors = verification.formatting_errors or []
        
        # ATS improvement loop
        while ats_score < 90 and loop_count < max_loops:
            loop_count += 1
            print(f"[Workflow] ATS score {ats_score}/100 is below 90. Refining LaTeX CV (Iteration {loop_count} of {max_loops})...")
            
            # Construct strict instructions with missing_exact_keywords and formatting_errors
            feedback_str = "Refine the LaTeX formatting and keywords to address the following issues:\n"
            if missing_exact_keywords:
                feedback_str += "Inject the following exact missing keywords/phrases into the CV: " + ", ".join([f"'{kw}'" for kw in missing_exact_keywords]) + "\n"
            if formatting_errors:
                feedback_str += "Fix the following ATS formatting/parsing errors:\n" + "\n".join([f"- {err}" for err in formatting_errors]) + "\n"
                
            ctx.state["feedback_str"] = feedback_str
            
            # Regenerate LaTeX CV with accumulated feedback
            latex_cv = await ctx.run_node(cv_writer_node)
            ctx.state["latex_cv"] = latex_cv
            
            # Re-verify
            verification = SafeAccess(await ctx.run_node(verification_node))
            ats_score = verification.ats_score
            missing_exact_keywords = verification.missing_exact_keywords or []
            formatting_errors = verification.formatting_errors or []
            
        if ats_score < 90:
            print(f"[Workflow] Warning: CV generation completed for JD {idx}. Reached max iterations ({max_loops}) but ATS score is {ats_score}/100.")
        else:
            print(f"[Workflow] ATS score requirement satisfied for JD {idx}: {ats_score}/100.")
            
        # STEP 7: Generate Cover Letter
        cover_letter = await ctx.run_node(cover_letter_node)
        
        # Compile CV LaTeX to PDF inside the new directory
        cv_tex_path = os.path.join(directory_path, f"CV_{user_name}_{company_name}_{position}.tex")
        compile_latex(cv_tex_path)
        
        # Compile Cover Letter LaTeX to PDF inside the new directory
        cl_tex_path = os.path.join(directory_path, f"COVER_{user_name_with_initials}_{company_name}_{position}.tex")
        compile_latex(cl_tex_path)
        
        print(f"[Workflow] Finalized CV and Cover Letter files saved and compiled in: {directory_path}")
        
        batch_results.append({
            "index": idx,
            "company_name": company_name,
            "position": position,
            "user_name": user_name,
            "user_name_with_initials": user_name_with_initials,
            "directory_path": directory_path,
            "match_score": match_result.match_score,
            "ats_score": ats_score,
            "chart_path": chart_path,
            "match_report_path": report_pdf_path,
            "cv_markdown": cv_markdown,
            "latex_cv": latex_cv,
            "cover_letter": cover_letter
        })
        
    # Return batch report as JSON
    report = {"results": batch_results}
    if batch_results:
        # Keep backward compatibility for single results checks in runner
        last_res = batch_results[-1]
        report["company_name"] = last_res.get("company_name", "UnknownCompany")
        report["position"] = last_res.get("position", "UnknownPosition")
        report["user_name"] = last_res.get("user_name", "Candidate")
        report["user_name_with_initials"] = last_res.get("user_name_with_initials", "Candidate")
        report["directory_path"] = last_res.get("directory_path", "")
        report["match_score"] = last_res["match_score"]
        report["ats_score"] = last_res["ats_score"]
        report["chart_path"] = last_res["chart_path"]
        report["match_report_path"] = last_res.get("match_report_path", "")
        report["cv_markdown"] = last_res["cv_markdown"]
        report["latex_cv"] = last_res["latex_cv"]
        report["cover_letter"] = last_res["cover_letter"]
        
    return json.dumps(report, indent=2)

# --- Workflow Setup ---

root_agent = Workflow(
    name="kero_cv_root",
    edges=[("START", kero_cv_workflow)]
)

app = App(
    name="kero_cv_app",
    root_agent=root_agent
)

# --- Interactive Standalone Script Executer ---

async def run_interactive_workflow():
    """Runs the workflow in the terminal with interactive human-in-the-loop triggers."""
    print("==================================================")
    print("         Kero-CV Agent Workflow Console           ")
    print("==================================================")

    # Get inputs
    cv_file = input("Enter path to CV file (PDF, DOCX, TXT, MD): ").strip()
    if not cv_file:
        # Check if there are any parsed CVs in data/input
        input_dir = os.path.join("data", "input")
        parsed_files = []
        if os.path.exists(input_dir):
            parsed_files = [f for f in os.listdir(input_dir) if f.endswith(".md")]
        
        if parsed_files:
            print("No CV file path provided. Checking data/input for parsed CVs...")
            cv_file = ""
        else:
            cv_file = "data/sample_cv.txt"
            print(f"No cached parsed CVs found and no CV path provided. Using default dummy CV path: {cv_file}")
            os.makedirs("data", exist_ok=True)
            with open(cv_file, "w", encoding="utf-8") as f:
                f.write("Candidate: John Doe\nContact: john.doe@example.com\nSkills: Python, SQL, C++, Docker\nExperience: 3 years Python Developer.")

    jd_text = input("Enter Job Description string (or press enter for default): ").strip()
    if not jd_text:
        jd_text = "Looking for a Software Engineer with Python experience, Docker skills, and SQL knowledge."
        print(f"Using default JD: '{jd_text}'")

    input_payload = {
        "cv_file_path": cv_file,
        "jd_string": jd_text
    }

    # Initialize runner
    runner = InMemoryRunner(app=app)
    session_id = "cli_session"
    user_id = "cli_user"

    print("\nStarting Kero-CV workflow...")
    
    # Start the execution
    events = await runner.run_debug(json.dumps(input_payload), user_id=user_id, session_id=session_id)
    
    while True:
        # Check for HITL pauses in events
        hitl_pause = None
        for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call and part.function_call.name == "adk_request_input":
                        hitl_pause = part.function_call
                        break
                if hitl_pause:
                    break

        if hitl_pause:
            # We hit a human-in-the-loop pause!
            msg = hitl_pause.args.get("message") or "Input requested:"
            print("\n" + msg)
            
            # For multiline Markdown CV editing support
            if "CV MARKDOWN REVIEW" in msg:
                print("Enter your revised Markdown CV text below. Type 'DONE' on a new line when finished (or just type 'proceed' to keep current):")
                lines = []
                while True:
                    line = input()
                    if line.strip() == "DONE":
                        break
                    lines.append(line)
                user_val = "\n".join(lines)
                if not user_val.strip() or user_val.strip().lower() == "proceed":
                    user_val = "proceed"
            else:
                user_val = input("Your response: ")

            # Build resume message
            response_part = types.Part(
                function_response=types.FunctionResponse(
                    id=hitl_pause.id,
                    name="adk_request_input",
                    response={"result": user_val}
                )
            )
            resume_message = types.Content(role="user", parts=[response_part])
            
            # Resume run
            print("\nResuming workflow...")
            events = await runner.run_debug(resume_message, user_id=user_id, session_id=session_id)
        else:
            # Execution finished (no more pause requests)
            # Find and display final result
            final_report = None
            for event in events:
                if event.is_final_response():
                    if event.output:
                        final_report = event.output
                    elif event.content and event.content.parts:
                        final_report = event.content.parts[0].text
            
            print("\n==================================================")
            print("         Workflow Completed Successfully!         ")
            print("==================================================")
            if final_report:
                try:
                    # Pretty print final JSON report
                    parsed_report = json.loads(final_report)
                    print(f"Match Score: {parsed_report.get('match_score')}/100")
                    print(f"ATS Score: {parsed_report.get('ats_score')}/100")
                    print(f"Skills Chart saved to: {parsed_report.get('chart_path')}")
                    print("\n--- Final LaTeX CV (Excerpt) ---")
                    print(parsed_report.get('latex_cv', '')[:300] + "\n...")
                    print("\n--- Final Cover Letter (Excerpt) ---")
                    print(parsed_report.get('cover_letter', '')[:300] + "\n...")
                except Exception:
                    print(final_report)
            break

if __name__ == "__main__":
    if "GOOGLE_API_KEY" not in os.environ and "GEMINI_API_KEY" not in os.environ:
        print("WARNING: GOOGLE_API_KEY or GEMINI_API_KEY is not set in environment.")
        print("Please configure your Gemini API Key in a .env file or environment variable to run the models.\n")
    
    asyncio.run(run_interactive_workflow())
