import json
from pathlib import Path

from .models import ResolvedAction, WebreelConfig, WebreelVideo, WebreelStep


def generate_webreel_config(
    video_name: str,
    start_url: str,
    actions: list[ResolvedAction],
) -> WebreelConfig:
    """
    Build a WebreelConfig from a list of resolved actions.

    Args:
        video_name: Key name for the video in the config.
        start_url: URL webreel opens at the start of the recording.
        actions: Actions with selectors already resolved.

    Returns:
        WebreelConfig ready to serialize to JSON.
    """
    steps: list[WebreelStep] = []

    # Opening pause so the recording starts with a settled page
    steps.append(WebreelStep(action="pause", ms=1000))

    for action in actions:
        if action.action == "navigate":
            # The start URL is handled by webreel's "url" field.
            # Only add a navigate step if it points to a different page.
            if action.url and action.url.rstrip("/") != start_url.rstrip("/"):
                steps.append(WebreelStep(action="navigate", url=action.url))
                steps.append(WebreelStep(action="pause", ms=800))

        elif action.action == "click":
            # Add pause before click to show cursor movement clearly
            steps.append(WebreelStep(action="pause", ms=500))
            
            if action.selector:
                # Move cursor to element first (makes click target visible)
                steps.append(WebreelStep(action="moveTo", selector=action.selector))
                steps.append(WebreelStep(action="pause", ms=400))  # Pause to show cursor on target
                steps.append(WebreelStep(action="click", selector=action.selector, delay=600))
            elif action.target:
                # Fallback to text matching that webreel can resolve directly.
                text = action.target[:60]
                steps.append(WebreelStep(action="moveTo", text=text))
                steps.append(WebreelStep(action="pause", ms=400))
                steps.append(WebreelStep(action="click", text=text, delay=600))
            steps.append(WebreelStep(action="pause", ms=600))  # Pause after click to show result

        elif action.action == "type":
            # Add pause before typing
            steps.append(WebreelStep(action="pause", ms=400))

            if action.selector:
                # 1. moveTo: visual cursor animation to the input
                # 2. pause: wait for cursor animation to finish (800ms)
                # 3. type WITHOUT selector and WITHOUT click:
                #    Clicking on elements like Google search box triggers
                #    autocomplete overlays that steal focus. Instead we just
                #    type directly — most pages auto-focus relevant inputs
                #    or CDP key events reach the active element anyway.
                steps.append(WebreelStep(action="moveTo", selector=action.selector))
                steps.append(WebreelStep(action="pause", ms=1500))
                steps.append(WebreelStep(
                    action="type",
                    text=action.text,
                    charDelay=70,
                    delay=400,
                ))
            elif action.target and action.text:
                steps.append(WebreelStep(action="moveTo", text=action.target[:60]))
                steps.append(WebreelStep(action="pause", ms=1500))
                steps.append(WebreelStep(action="type", text=action.text, charDelay=70, delay=400))
            elif action.text:
                steps.append(WebreelStep(action="type", text=action.text, charDelay=70, delay=400))
            steps.append(WebreelStep(action="pause", ms=600))  # Pause after typing

        elif action.action == "key":
            # Key press action (e.g., Enter, Escape)
            steps.append(WebreelStep(action="pause", ms=400))
            steps.append(WebreelStep(action="key", key=action.key or "Enter", delay=500))
            steps.append(WebreelStep(action="pause", ms=5000))  # Wait for page load after key press

        elif action.action == "scroll":
            y_px = 500 if action.direction == "down" else -500
            steps.append(WebreelStep(action="scroll", y=y_px, delay=500))
            steps.append(WebreelStep(action="pause", ms=600))

        elif action.action == "pause":
            steps.append(WebreelStep(action="pause", ms=action.ms or 1000))

    # Closing pause so the last action is fully visible in the video
    steps.append(WebreelStep(action="pause", ms=1500))

    video = WebreelVideo(
        url=start_url,
        viewport={"width": 1920, "height": 1080},
        defaultDelay=400,
        steps=steps,
    )

    return WebreelConfig(videos={video_name: video})


def save_config(config: WebreelConfig, output_path: str = "webreel.config.json") -> Path:
    """
    Serialize a WebreelConfig to a JSON file.

    Args:
        config: The config to write.
        output_path: Target file path (default: webreel.config.json in cwd).

    Returns:
        Resolved Path of the written file.
    """
    path = Path(output_path).resolve()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

    return path
