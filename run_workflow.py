import os
import json
import asyncio
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types
from main import app
from contextlib import aclosing
from google.adk.utils._debug_output import print_event

# Load environment
load_dotenv()

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
    session_id = "auto_session"
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
                    print(f"Match Score: {report.get('match_score')}/100")
                    print(f"ATS Score: {report.get('ats_score')}/100")
                    print(f"Skills Chart: {report.get('chart_path')}")
                    
                    # Write results to output files
                    os.makedirs("data", exist_ok=True)
                    
                    latex_cv_path = "data/output_cv.tex"
                    with open(latex_cv_path, "w", encoding="utf-8") as f:
                        f.write(report.get("latex_cv", ""))
                    print(f"LaTeX CV written to: {latex_cv_path}")

                    cover_letter_path = "data/output_cover_letter.txt"
                    with open(cover_letter_path, "w", encoding="utf-8") as f:
                        f.write(report.get("cover_letter", ""))
                    print(f"Cover Letter written to: {cover_letter_path}")
                    
                except Exception as e:
                    print("Failed to parse report or write output files:", e)
                    print(final_report)
            else:
                print("No final report was returned by the workflow.")
            break

if __name__ == "__main__":
    asyncio.run(run_automated_workflow())
