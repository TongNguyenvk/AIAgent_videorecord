"""
Unit tests for src.parser - NL to structured actions.

These tests call the real Azure AI API, so GITHUB_TOKEN must be set.
Run: pytest tests/test_parser.py -v
"""
import os
import pytest
from dotenv import load_dotenv

load_dotenv()

# Skip all tests in this module if GITHUB_TOKEN is not configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("GITHUB_TOKEN"),
    reason="GITHUB_TOKEN not set",
)

from src.parser import parse_natural_language
from src.models import ActionType


def test_parse_simple_navigate():
    actions = parse_natural_language("Mo trang google.com")
    assert len(actions) >= 1
    navigate = next((a for a in actions if a.action == ActionType.NAVIGATE), None)
    assert navigate is not None
    assert navigate.url is not None
    assert "google" in navigate.url


def test_parse_navigate_and_click():
    actions = parse_natural_language(
        "Mo vnexpress.net, click bai viet dau tien"
    )
    types = [a.action for a in actions]
    assert ActionType.NAVIGATE in types
    assert ActionType.CLICK in types


def test_parse_type_action():
    actions = parse_natural_language(
        "Mo google.com, go 'hello world' vao o tim kiem, nhan nut Tim kiem"
    )
    type_action = next((a for a in actions if a.action == ActionType.TYPE), None)
    assert type_action is not None
    assert type_action.text is not None
    assert "hello" in type_action.text.lower() or "world" in type_action.text.lower()


def test_parse_scroll_action():
    actions = parse_natural_language(
        "Mo vnexpress.net, cuon xuong de xem them"
    )
    scroll = next((a for a in actions if a.action == ActionType.SCROLL), None)
    assert scroll is not None
    assert scroll.direction == "down"


def test_parse_url_adds_scheme():
    actions = parse_natural_language("Mo github.com")
    navigate = next((a for a in actions if a.action == ActionType.NAVIGATE), None)
    assert navigate is not None
    assert navigate.url.startswith("http")
