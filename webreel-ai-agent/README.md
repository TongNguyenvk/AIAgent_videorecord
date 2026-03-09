# webreel-ai-agent

Natural language to webreel demo video generator, powered by **Llama 4 Scout 17B** Vision AI via GitHub Models.

## How it works

```
User input (Vietnamese / English)
        |
        v
   NL Parser (Llama 4 Scout text)
        |  "navigate, click, type, scroll..."
        v
   Vision AI (Llama 4 Scout vision)
        |  screenshot -> pixel (x, y)
        v
   DOM Selector (document.elementFromPoint)
        |  CSS selector
        v
   Config Generator
        |  webreel.config.json
        v
   npx webreel record <name>
        |
        v
   videos/<name>.mp4
```

## Setup

### 1. Prerequisites

- Python 3.11+
- Node.js 18+ (for webreel CLI)
- A GitHub account with a personal access token

### 2. Install Python dependencies

```bash
cd webreel-ai-agent
python -m venv venv
venv\Scripts\activate   # Windows
# or: source venv/bin/activate  (Linux/macOS)

pip install -r requirements.txt
playwright install chromium
```

### 3. Install webreel CLI

```bash
npm install -g webreel
```

### 4. Configure environment

```bash
copy .env.example .env
```

Edit `.env` and set your GitHub personal access token:

```
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

Get a token at <https://github.com/settings/tokens> (no special scopes needed for GitHub Models).

## Usage

```bash
# Basic
python -m src.main "Mo vnexpress.net, click bai viet dau tien, cuon xuong"

# Custom video name
python -m src.main "Open github.com and click Sign in" --name github-login

# Quiet mode (no step-by-step logs)
python -m src.main "Mo google.com, go Python vao o tim kiem" --name google-search --quiet
```

The generated `webreel.config.json` and the output video appear in the current directory and `videos/` respectively.

## Run tests

```bash
pytest tests/ -v
```

Tests require `GITHUB_TOKEN` to be set and a live internet connection.

## Project structure

```
webreel-ai-agent/
├── src/
│   ├── models.py       # Pydantic data models
│   ├── parser.py       # NL -> actions (Llama text mode)
│   ├── vision.py       # Screenshot + Vision AI coordinates
│   ├── locator.py      # Coords -> CSS selector via DOM
│   ├── generator.py    # Build webreel.config.json
│   └── main.py         # CLI orchestrator
├── tests/
│   ├── test_parser.py
│   └── test_vision.py
├── requirements.txt
├── pyproject.toml
└── .env.example
```
