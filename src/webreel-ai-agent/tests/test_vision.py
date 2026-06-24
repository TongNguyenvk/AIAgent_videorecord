"""
Integration tests for src.vision - screenshot + Vision AI coordinate detection.

Requires GITHUB_TOKEN and a live internet connection.
Run: pytest tests/test_vision.py -v
"""
import os
import pytest
from dotenv import load_dotenv

load_dotenv()

pytestmark = pytest.mark.skipif(
    not os.environ.get("GITHUB_TOKEN"),
    reason="GITHUB_TOKEN not set",
)

from src.vision import VisionLocator, locate_element_by_vision


def test_screenshot_returns_bytes():
    with VisionLocator() as locator:
        locator.navigate("https://www.google.com")
        data = locator.screenshot()
    assert isinstance(data, bytes)
    assert len(data) > 1000  # valid PNG has a minimum size


def test_screenshot_base64_is_string():
    with VisionLocator() as locator:
        locator.navigate("https://www.google.com")
        b64 = locator.screenshot_base64()
    assert isinstance(b64, str)
    assert len(b64) > 100


def test_vision_finds_google_search_box():
    with VisionLocator() as locator:
        locator.navigate("https://www.google.com")
        b64 = locator.screenshot_base64()

    coords = locate_element_by_vision(b64, "o tim kiem Google")
    assert coords.x > 0
    assert coords.y > 0
    assert coords.confidence > 0.5


def test_vision_returns_minus_one_for_missing_element():
    with VisionLocator() as locator:
        locator.navigate("https://www.google.com")
        b64 = locator.screenshot_base64()

    coords = locate_element_by_vision(b64, "nut khong ton tai xyz_abc_123")
    # Confidence should be low or coordinates should be -1
    assert coords.x == -1 or coords.confidence < 0.4
