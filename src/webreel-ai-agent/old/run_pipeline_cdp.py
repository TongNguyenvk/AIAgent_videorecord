"""
Pipeline với Chrome CDP - Sử dụng Chrome đang chạy của user
Giải pháp "ký sinh" để bypass Google anti-bot
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from chrome_cdp_wrapper import ChromeCDPWrapper, patch_browser_use_with_cdp

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()


async def run_pipeline_with_cdp(
    task: str,
    output_dir: str = "output",
    cdp_url: str = "http://localhost:9222"
):
    """
    Chạy pipeline với Chrome CDP connection
    
    Args:
        task: Task description cho AI agent
        output_dir: Thư mục output
        cdp_url: Chrome CDP endpoint
    """
    
    logger.info("=" * 80)
    logger.info("Starting Pipeline with Chrome CDP")
    logger.info("=" * 80)
    
    # Check if Chrome is running with debug port
    import requests
    try:
        response = requests.get(f"{cdp_url}/json/version", timeout=2)
        chrome_info = response.json()
        logger.info(f"✓ Chrome detected: {chrome_info.get('Browser', 'Unknown')}")
    except Exception as e:
        logger.error("❌ Cannot connect to Chrome debug port")
        logger.error("Please run start_chrome_debug.bat first!")
        logger.error(f"Error: {e}")
        return None
    
    # Import browser-use
    try:
        from browser_use import Agent
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        logger.error(f"Failed to import browser-use: {e}")
        logger.error("Make sure browser-use is installed")
        return None
    
    # Setup LLM
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create agent
    logger.info(f"\nTask: {task}")
    agent = Agent(
        task=task,
        llm=llm
    )
    
    # Patch agent to use existing Chrome
    logger.info("\nPatching agent to use existing Chrome...")
    wrapper = None
    
    try:
        wrapper, automation_page = await patch_browser_use_with_cdp(agent, cdp_url)
        logger.info("✓ Agent patched successfully")
        
        # Run agent
        logger.info("\nRunning agent...")
        result = await agent.run()
        
        logger.info("\n" + "=" * 80)
        logger.info("Agent Result:")
        logger.info("=" * 80)
        logger.info(result)
        
        # Extract actions for webreel
        logger.info("\nExtracting actions for webreel...")
        
        # Get history from agent
        if hasattr(agent, 'history') and agent.history:
            actions = []
            for item in agent.history:
                if hasattr(item, 'action') and item.action:
                    actions.append({
                        'type': item.action.get('type'),
                        'data': item.action
                    })
            
            logger.info(f"Extracted {len(actions)} actions")
            
            # Convert to webreel format
            from bu_to_webreel import BrowserUseToWebreel
            
            converter = BrowserUseToWebreel()
            webreel_config = converter.convert_history_to_webreel(
                agent.history,
                output_dir=output_dir
            )
            
            if webreel_config:
                logger.info(f"✓ Webreel config generated: {webreel_config}")
                
                # Render video
                logger.info("\nRendering video with webreel...")
                from render_video import render_video
                
                video_path = render_video(webreel_config)
                
                if video_path:
                    logger.info(f"✓ Video rendered: {video_path}")
                    return {
                        'success': True,
                        'config': webreel_config,
                        'video': video_path,
                        'actions': actions
                    }
        
        return {
            'success': True,
            'result': result
        }
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        # Cleanup
        if wrapper:
            logger.info("\nDisconnecting from Chrome...")
            await wrapper.disconnect()
            logger.info("✓ Disconnected (Chrome still running)")


async def test_google_drive():
    """Test case: Access Google Drive"""
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Google Drive Access")
    logger.info("=" * 80)
    
    task = """
    Go to Google Drive (drive.google.com).
    If not logged in, wait for manual login.
    Once logged in, list the files in My Drive.
    Take a screenshot.
    """
    
    result = await run_pipeline_with_cdp(
        task=task,
        output_dir="output/test-google-drive-cdp"
    )
    
    if result and result.get('success'):
        logger.info("\n✓ Test passed!")
    else:
        logger.error("\n❌ Test failed!")
    
    return result


async def test_simple_navigation():
    """Test case: Simple navigation"""
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Simple Navigation")
    logger.info("=" * 80)
    
    task = """
    1. Go to google.com
    2. Search for "playwright automation"
    3. Click on the first result
    4. Take a screenshot
    """
    
    result = await run_pipeline_with_cdp(
        task=task,
        output_dir="output/test-simple-nav-cdp"
    )
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run pipeline with Chrome CDP")
    parser.add_argument(
        "--test",
        choices=["google-drive", "simple-nav"],
        help="Run test case"
    )
    parser.add_argument(
        "--task",
        type=str,
        help="Custom task description"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/cdp-test",
        help="Output directory"
    )
    parser.add_argument(
        "--cdp-url",
        type=str,
        default="http://localhost:9222",
        help="Chrome CDP endpoint URL"
    )
    
    args = parser.parse_args()
    
    if args.test == "google-drive":
        asyncio.run(test_google_drive())
    elif args.test == "simple-nav":
        asyncio.run(test_simple_navigation())
    elif args.task:
        asyncio.run(run_pipeline_with_cdp(
            task=args.task,
            output_dir=args.output,
            cdp_url=args.cdp_url
        ))
    else:
        print("Usage:")
        print("  python run_pipeline_cdp.py --test google-drive")
        print("  python run_pipeline_cdp.py --test simple-nav")
        print("  python run_pipeline_cdp.py --task 'Your task here' --output output/my-test")
