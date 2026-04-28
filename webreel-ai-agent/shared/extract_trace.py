import json
import base64
import sys

trace_path = r"f:\==HK1-2526==\ThucTap\webreel\webreel-ai-agent\output\docker_pres_test\.webreel\traces\docker_pres_test.trace.json"

try:
    with open(trace_path, 'r', encoding='utf-8') as f:
        trace = json.load(f)
    
    # If trace is a dict that contains history, extract it. Otherwise, assume trace is the history list.
    history = trace.get("history", []) if isinstance(trace, dict) else trace
    
    if isinstance(history, list) and len(history) > 0:
        last_step = history[-1]
        state = last_step.get("state", {}) if isinstance(last_step, dict) else {}
        b64img = state.get("pixels") or state.get("screenshot")
        
        if b64img:
            # save to artifacts dir
            out_img = r"C:\Users\admin\.gemini\antigravity\brain\07e8d2db-711e-4e69-b233-d9feac446ec6\access_denied.png"
            with open(out_img, "wb") as img_f:
                img_f.write(base64.b64decode(b64img))
            print(f"Saved screenshot to {out_img}")
        else:
            print("No screenshot found in the last step.")
    else:
        print("Trace history is empty.")

except Exception as e:
    print(f"Error reading trace: {e}")
