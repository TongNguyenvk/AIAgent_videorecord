"""
Regenerate webreel config from browser_use_history.json using updated parser.
"""
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from src.bu_to_webreel import convert_history_to_config_and_script

def main():
    history_path = Path("output/test/browser_use_history.json")
    output_dir = Path("output/test")
    
    with open(history_path, "r", encoding="utf-8") as f:
        history = json.load(f)
    
    logger.info(f"Loaded history from: {history_path}")
    
    config, tts_script = convert_history_to_config_and_script(
        history,
        video_name="test",
        cdp_url="http://localhost:9222"
    )
    
    config_path = output_dir / "webreel_pipeline.config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Regenerated config: {config_path}")
    logger.info(f"Total steps: {len(config['videos']['test']['steps'])}")
    
    # Show first few input actions
    for i, step in enumerate(config['videos']['test']['steps']):
        if step.get('action') == 'click' and 'Focus input' in step.get('description', ''):
            logger.info(f"Step {i}: {step['action']} - selector: {step.get('selector')}")
        if step.get('action') == 'type':
            logger.info(f"Step {i}: {step['action']} - text: {step.get('text')[:30]}")

if __name__ == "__main__":
    main()
