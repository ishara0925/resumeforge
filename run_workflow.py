import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import os
import json
import asyncio
import subprocess
import shutil
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types
from main import app
from contextlib import aclosing
from google.adk.utils._debug_output import print_event

# Load environment
load_dotenv()

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
        
    print(f"Compiling {tex_path} to PDF using: {xelatex_path}...")
    try:
        out_dir = os.path.dirname(tex_path) or "."
        # Prepend the directory of the resolved xelatex to environment PATH
        xelatex_dir = os.path.dirname(xelatex_path)
        env = os.environ.copy()
        if xelatex_dir:
            env["PATH"] = xelatex_dir + os.pathsep + env.get("PATH", "")
            
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

async def run_automated_workflow():
    cv_file = "CV_HI_KULATHILAKA_2026_07.pdf"
    jd_file = "jd.txt"
    
    if not os.path.exists(cv_file):
        print(f"Error: CV file not found at {cv_file}")
        return
        
    if not os.path.exists(jd_file):
        print(f"Error: JD file not found at {jd_file}")
        return

    with open(jd_file, "r", encoding="utf-8") as f:
        jd_text = f.read().strip()

    input_payload = {
        "cv_file_path": cv_file,
        "jd_string": jd_text
    }

    runner = InMemoryRunner(app=app)
    import time
    session_id = f"auto_session_{int(time.time())}"
    user_id = "auto_user"

    print("--- STARTING WORKFLOW ---")
    print(f"CV File: {cv_file}")
    print(f"JD File: {jd_file} ({len(jd_text)} chars)")
    
    events = await runner.run_debug(json.dumps(input_payload), user_id=user_id, session_id=session_id)
    
    while True:
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
            msg = hitl_pause.args.get("message") or ""
            print("\n[HITL Pause Encountered]")
            print(msg[:500] + ("..." if len(msg) > 500 else ""))
            
            # Determine automated response
            if "CV MARKDOWN REVIEW" in msg:
                user_val = "proceed"
                print("-> Auto-responding: 'proceed'")
            elif "LOW MATCH APPROVAL" in msg:
                user_val = "yes"
                print("-> Auto-responding: 'yes'")
            else:
                user_val = "proceed"
                print("-> Auto-responding default: 'proceed'")

            response_part = types.Part(
                function_response=types.FunctionResponse(
                    id=hitl_pause.id,
                    name="adk_request_input",
                    response={"result": user_val}
                )
            )
            resume_message = types.Content(role="user", parts=[response_part])
            
            # Collect and print events from resume run manually to avoid run_debug type limitations
            collected_events = []
            async with aclosing(
                runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=resume_message,
                )
            ) as agen:
                async for event in agen:
                    print_event(event)
                    collected_events.append(event)
            events = collected_events
        else:
            # Done! Get the final response
            final_report = None
            for event in events:
                if event.is_final_response():
                    if event.output:
                        final_report = event.output
                    elif event.content and event.content.parts:
                        final_report = event.content.parts[0].text
            
            print("\n--- WORKFLOW COMPLETED ---")
            if final_report:
                try:
                    report = json.loads(final_report)
                    results = report.get("results", [])
                    if not results:
                        # Fallback for single-report format
                        results = [report]
                    
                    for res in results:
                        idx = res.get("index", 1)
                        print(f"\n[JD {idx}] Match Score: {res.get('match_score')}/100")
                        print(f"[JD {idx}] ATS Score: {res.get('ats_score')}/100")
                        print(f"[JD {idx}] Skills Chart: {res.get('chart_path')}")
                        
                        # Write results to output files
                        os.makedirs("data/output", exist_ok=True)
                        
                        # 1. Save CV Markdown (.md)
                        cv_md_path = f"data/output/cv_markdown_{idx}.md"
                        with open(cv_md_path, "w", encoding="utf-8") as f:
                            f.write(res.get("cv_markdown", ""))
                        
                        # 2. Save LaTeX CV (.tex)
                        latex_cv_path = f"data/output/cv_final_{idx}.tex"
                        with open(latex_cv_path, "w", encoding="utf-8") as f:
                            f.write(res.get("latex_cv", ""))
                        print(f"[JD {idx}] LaTeX CV written to: {latex_cv_path}")

                        # 3. Save LaTeX/Markdown Cover Letter (.md)
                        cover_letter_path = f"data/output/cover_letter_{idx}.md"
                        with open(cover_letter_path, "w", encoding="utf-8") as f:
                            f.write(res.get("cover_letter", ""))
                        print(f"[JD {idx}] Cover Letter written to: {cover_letter_path}")
                        
                        # 4. Compile CV to PDF
                        compile_latex(latex_cv_path)
                        
                        # 5. Compile Cover Letter to PDF if it is LaTeX
                        if "\\documentclass" in res.get("cover_letter", ""):
                            cl_tex_path = f"data/output/cover_letter_{idx}.tex"
                            with open(cl_tex_path, "w", encoding="utf-8") as f:
                                f.write(res.get("cover_letter", ""))
                            compile_latex(cl_tex_path)
                            
                except Exception as e:
                    print("Failed to parse report or write output files:", e)
                    print(final_report)
            else:
                print("No final report was returned by the workflow.")
            break

if __name__ == "__main__":
    asyncio.run(run_automated_workflow())
