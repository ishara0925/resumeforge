import os
import json
import asyncio
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
from agents.cv_parser import parse_cv_to_details_async, cv_details_to_markdown
from agents.jd_parser import parse_jd_async
from agents.match_maker import match_cv_and_jd_async, generate_match_chart
from agents.cv_writer import write_cv_async
from agents.cover_letter_agent import generate_cover_letter_async
from agents.verification_agent import verify_ats_async, ATSVerificationResult

# --- ADK Workflow Node Definitions ---

@node(name="parse_cv_node")
async def parse_cv_node(cv_file_path: str) -> str:
    """Extracts CV text and formats it into Markdown."""
    print(f"[Node: CV Parser] Extracting & parsing CV from: {cv_file_path}")
    details = await parse_cv_to_details_async(cv_file_path)
    return cv_details_to_markdown(details)

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
async def match_maker_node(cv_markdown: str, jd_details_json: str):
    """Compares CV and Job Description to output strong matches, gaps, and a match score."""
    print("[Node: Match Maker] Matching candidate CV against JD requirements...")
    return await match_cv_and_jd_async(cv_markdown, jd_details_json)

@node(name="generate_chart_node")
def generate_chart_node(skills_comparison: list, chart_path: str):
    """Saves a visual bar chart comparing required vs possessed skills."""
    print(f"[Node: Chart Generator] Saving comparison chart to {chart_path}...")
    generate_match_chart(skills_comparison, chart_path)
    return True

@node(name="ask_match_approval", rerun_on_resume=False)
async def ask_match_approval(ctx: Context, score: int, chart_path: str):
    """Pauses execution if match score is below 70 to request user's approval to proceed."""
    yield RequestInput(
        message=(
            f"=== HUMAN-IN-THE-LOOP: LOW MATCH APPROVAL ===\n"
            f"WARNING: The calculated match score is {score}/100 (below threshold of 70).\n"
            f"A visual breakdown has been saved to: {chart_path}\n"
            "Do you want to proceed with this candidate anyway? (Type 'yes' or 'no'): "
        ),
        payload={"score": score, "chart_path": chart_path}
    )

@node(name="cv_writer_node")
async def cv_writer_node(cv_markdown: str, feedback_str: str) -> str:
    """Generates LaTeX CV using cv_writer agent."""
    print("[Node: CV Writer] Drafting LaTeX CV...")
    return await write_cv_async(cv_markdown, feedback_str)

@node(name="verification_node")
async def verification_node(latex_cv: str, jd_text: str):
    """Simulates ATS compatibility check and returns verification results."""
    print("[Node: Verification] Running simulated ATS compatibility check with TF-IDF keyword check...")
    return await verify_ats_async(latex_cv, jd_text)

@node(name="cover_letter_node")
async def cover_letter_node(cv_markdown: str, jd_details_json: str) -> str:
    """Generates a tailored cover letter."""
    print("[Node: Cover Letter] Drafting cover letter...")
    return await generate_cover_letter_async(cv_markdown, jd_details_json)

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
        cv_file_path = data["cv_file_path"]
        jd_string = data["jd_string"]
        ctx.state["cv_file_path"] = cv_file_path
        ctx.state["jd_string"] = jd_string
        ctx.state["jd_text"] = jd_string
    except Exception as e:
        raise ValueError(
            "Workflow input must be a JSON-formatted string with 'cv_file_path' and 'jd_string' keys. "
            f"Parsing Error: {e}"
        )

    # STEP 1: Parse CV
    raw_md = await ctx.run_node(parse_cv_node)

    # STEP 2: HITL Pause - CV Markdown Review
    ctx.state["initial_markdown"] = raw_md
    user_edited_cv = await ctx.run_node(edit_cv_markdown_node)
    if user_edited_cv and user_edited_cv.strip() and user_edited_cv.strip().lower() not in ("yes", "y", "proceed", "ok"):
        cv_markdown = user_edited_cv.strip()
    else:
        cv_markdown = raw_md
    ctx.state["cv_markdown"] = cv_markdown

    # STEP 3: Parse JD
    jd_details = SafeAccess(await ctx.run_node(parse_jd_node))
    jd_details_json = jd_details.model_dump_json()
    ctx.state["jd_details_json"] = jd_details_json

    # STEP 4: Match Making
    match_result = SafeAccess(await ctx.run_node(match_maker_node))

    # Generate Matplotlib chart
    chart_path = "data/match_chart.png"
    ctx.state["skills_comparison"] = match_result.skills_comparison
    ctx.state["chart_path"] = chart_path
    await ctx.run_node(generate_chart_node)

    # STEP 5: HITL Pause - Low score check (< 70)
    if match_result.match_score < 70:
        ctx.state["score"] = match_result.match_score
        approval = await ctx.run_node(ask_match_approval)
        if approval.strip().lower() not in ("yes", "y", "approve", "proceed", "ok"):
            raise ValueError(f"Workflow aborted by user. Low match score: {match_result.match_score}/100")

    # STEP 6 & 8: CV Writer & ATS Verification Loop (Score < 90)
    loop_count = 0
    max_loops = 3
    feedback_log = []
    latex_cv = ""
    ats_score = 0

    # Initial draft
    feedback_str = "Initial draft based on CV parser and match analysis."
    ctx.state["feedback_str"] = feedback_str
    latex_cv = await ctx.run_node(cv_writer_node)
    ctx.state["latex_cv"] = latex_cv

    # Simulated ATS Check
    verification = SafeAccess(await ctx.run_node(verification_node))
    ats_score = verification.score
    feedback_log.extend(verification.feedback)

    # ATS improvement loop
    while ats_score < 90 and loop_count < max_loops:
        loop_count += 1
        print(f"[Workflow] ATS score {ats_score}/100 is below 90. Refining LaTeX CV (Iteration {loop_count} of {max_loops})...")
        
        feedback_str = "Refine the LaTeX formatting to address the following feedback:\n" + "\n".join([f"- {fb}" for fb in feedback_log])
        ctx.state["feedback_str"] = feedback_str
        
        # Regenerate LaTeX CV with accumulated feedback
        latex_cv = await ctx.run_node(cv_writer_node)
        ctx.state["latex_cv"] = latex_cv
        
        # Re-verify
        verification = SafeAccess(await ctx.run_node(verification_node))
        ats_score = verification.score
        feedback_log = list(verification.feedback)

    if ats_score < 90:
        print(f"[Workflow] Warning: CV generation completed. Reached max iterations ({max_loops}) but ATS score is {ats_score}/100.")
    else:
        print(f"[Workflow] ATS score requirement satisfied: {ats_score}/100.")

    # STEP 7: Generate Cover Letter
    cover_letter = await ctx.run_node(cover_letter_node)

    # Final Output Report
    report = {
        "match_score": match_result.match_score,
        "ats_score": ats_score,
        "chart_path": chart_path,
        "cv_markdown": cv_markdown,
        "latex_cv": latex_cv,
        "cover_letter": cover_letter
    }
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
        cv_file = "data/sample_cv.txt"
        print(f"Using default dummy CV path: {cv_file}")
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
