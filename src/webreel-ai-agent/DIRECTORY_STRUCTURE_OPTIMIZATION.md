# Directory Structure Optimization Plan

## Current Issues

1. **Root directory clutter**: Too many test files, config files, and scripts at root level
2. **Duplicate/old code**: `v3/` folder contains duplicate pipeline code, `old/` folder with outdated files
3. **Mixed concerns**: Test files, documentation, and source code mixed together
4. **Unclear organization**: Hard to find specific files quickly

## Proposed Structure

```
webreel-ai-agent/
├── backend/                    # FastAPI backend (KEEP AS IS - well organized)
│   ├── main.py
│   ├── models.py
│   ├── tasks.py
│   ├── websocket.py
│   ├── shutdown.py
│   ├── logging_config.py
│   ├── middleware.py
│   ├── requirements.txt
│   └── tests/                  # Move all backend tests here
│       ├── test_main.py
│       ├── test_websocket.py
│       ├── test_shutdown.py
│       └── ...
│
├── frontend/                   # Streamlit frontend (KEEP AS IS)
│   ├── api_client.py
│   ├── websocket_client.py
│   └── tests/
│       └── test_api_client.py
│
├── src/                        # Core pipeline logic
│   ├── __init__.py
│   ├── app.py                  # Streamlit UI
│   ├── pipeline/               # NEW: Pipeline modules
│   │   ├── __init__.py
│   │   ├── runner.py           # Main pipeline runner (from webreel_runner.py)
│   │   ├── scout.py            # Phase 1: browser-use
│   │   ├── parser.py           # Phase 2: bu_to_webreel
│   │   ├── tts.py              # Phase 3: TTS generation
│   │   ├── injector.py         # Phase 4: audio_injector
│   │   ├── executor.py         # Phase 5: webreel execution
│   │   └── composer.py         # Phase 6: trace_composer
│   └── models.py               # Shared data models
│
├── tests/                      # Integration and E2E tests
│   ├── integration/
│   │   ├── test_full_pipeline.py
│   │   └── test_backend_api.py
│   ├── unit/
│   │   ├── test_parser.py
│   │   └── test_vision.py
│   └── fixtures/
│       └── test-cases/         # Move from root
│
├── scripts/                    # Utility scripts
│   ├── setup/
│   │   ├── setup_auth.py
│   │   ├── setup_real_chrome.py
│   │   └── start_chrome_debug.py
│   ├── dev/
│   │   ├── clean_sessions.py
│   │   ├── regenerate_config.py
│   │   └── debug_timeline.py
│   └── deployment/
│       ├── start_backend.bat
│       ├── start_frontend.bat
│       └── restart_streamlit.bat
│
├── docs/                       # Documentation (consolidate)
│   ├── README.md               # Main documentation
│   ├── MIGRATION_GUIDE.md
│   ├── TESTING_GUIDE.md
│   ├── architecture/
│   │   ├── PIPELINE_V3_SUMMARY.md
│   │   └── TECHSTACK_REPORT.md
│   ├── guides/
│   │   ├── DEMO_SETUP.md
│   │   ├── FORM_ELEMENTS_GUIDE.md
│   │   └── WEBREEL_RULES.md
│   └── archive/                # Move old docs here
│       └── WEEK1_COMMIT_GUIDE.md
│
├── output/                     # Generated videos (KEEP AS IS)
│
├── config/                     # NEW: Configuration files
│   ├── .env.example
│   ├── test_configs/           # Move all *.config.json here
│   │   ├── test_form.config.json
│   │   ├── test_select.config.json
│   │   └── ...
│   └── docker/
│       ├── Dockerfile
│       ├── Dockerfile.simple
│       └── docker-compose.yml
│
├── archive/                    # OLD CODE (for reference only)
│   ├── old/                    # Keep old implementations
│   ├── v3/                     # Deprecated v3 code
│   └── browser-use/            # Submodule (consider removing if not needed)
│
├── .env                        # Environment variables
├── .gitignore
├── requirements.txt            # Main dependencies
├── pyproject.toml
├── README.md                   # Project overview
└── run_pipeline.py             # Main entry point (keep at root for convenience)
```

## Migration Steps

### Phase 1: Organize Tests (Priority: HIGH)
1. Create `backend/tests/` directory
2. Move all `backend/test_*.py` to `backend/tests/`
3. Create `tests/integration/` directory
4. Move integration tests to `tests/integration/`
5. Update import paths in test files

### Phase 2: Consolidate Pipeline Code (Priority: HIGH)
1. Create `src/pipeline/` directory
2. Move pipeline modules:
   - `src/webreel_runner.py` → `src/pipeline/runner.py`
   - `src/bu_to_webreel.py` → `src/pipeline/parser.py`
   - `src/audio_injector.py` → `src/pipeline/injector.py`
   - `src/trace_composer.py` → `src/pipeline/composer.py`
   - `src/tts_edge.py` → `src/pipeline/tts.py`
3. Update imports in `run_pipeline.py` and `backend/tasks.py`
4. Delete duplicate code in `v3/` folder

### Phase 3: Organize Scripts (Priority: MEDIUM)
1. Create `scripts/setup/`, `scripts/dev/`, `scripts/deployment/`
2. Move scripts to appropriate subdirectories
3. Move `.bat` files to `scripts/deployment/`
4. Update documentation with new script paths

### Phase 4: Consolidate Documentation (Priority: MEDIUM)
1. Create `docs/architecture/` and `docs/guides/`
2. Move relevant docs to subdirectories
3. Create main `docs/README.md` with index
4. Move old/deprecated docs to `docs/archive/`

### Phase 5: Clean Up Root Directory (Priority: MEDIUM)
1. Create `config/test_configs/`
2. Move all `*.config.json` files to `config/test_configs/`
3. Move `test-cases/` to `tests/fixtures/`
4. Move Docker files to `config/docker/`
5. Delete temporary files (*.log, *.mp3, *.png at root)

### Phase 6: Archive Old Code (Priority: LOW)
1. Create `archive/` directory
2. Move `old/` folder to `archive/old/`
3. Move `v3/` folder to `archive/v3/`
4. Consider removing `browser-use/` submodule if not actively used
5. Add README in `archive/` explaining what's there

## Benefits

1. **Clearer organization**: Easy to find files by purpose
2. **Better maintainability**: Logical grouping of related code
3. **Easier onboarding**: New developers can understand structure quickly
4. **Reduced clutter**: Root directory only has essential files
5. **Better testing**: Tests organized by type (unit, integration, E2E)
6. **Scalability**: Structure supports future growth

## Breaking Changes

### Import Path Changes
```python
# OLD
from src.webreel_runner import run_pipeline_v3
from src.bu_to_webreel import convert_to_webreel
from src.audio_injector import inject_audio

# NEW
from src.pipeline.runner import run_pipeline_v3
from src.pipeline.parser import convert_to_webreel
from src.pipeline.injector import inject_audio
```

### Script Path Changes
```bash
# OLD
.\start_backend.bat
.\start_frontend.bat

# NEW
.\scripts\deployment\start_backend.bat
.\scripts\deployment\start_frontend.bat
```

### Config Path Changes
```python
# OLD
config_path = "test_form.config.json"

# NEW
config_path = "config/test_configs/test_form.config.json"
```

## Implementation Priority

1. **HIGH**: Phase 1 (Tests) and Phase 2 (Pipeline) - Core functionality
2. **MEDIUM**: Phase 3 (Scripts), Phase 4 (Docs), Phase 5 (Root cleanup)
3. **LOW**: Phase 6 (Archive) - Can be done gradually

## Recommendation

Start with Phase 1 and Phase 2 to organize the core codebase. This will make the most immediate impact on code maintainability without breaking existing functionality.

The other phases can be done incrementally as time permits.
