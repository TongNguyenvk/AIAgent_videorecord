# Design Document: Monorepo Split - Option 2 (Separate Repositories)

## Overview

This design document details the implementation strategy for splitting the current Webreel monorepo into two independent repositories: `webreel` (TypeScript core library) and `webreel-ai-agent` (Python AI agent application). The split addresses the technology stack mismatch identified in the monorepo structure analysis and improves developer experience by creating clear boundaries between distinct projects.

The migration will preserve Git history, maintain file integrity, and ensure both repositories are independently functional with appropriate CI/CD configurations. No code modifications will be made during the split, only file and directory reorganization.

## Architecture

### High-Level Strategy

The split follows a three-phase approach:

1. **Preparation Phase**: Analyze current structure, identify files for each repository, create migration scripts
2. **Execution Phase**: Use Git filter-repo or git filter-branch to create new repositories with preserved history
3. **Verification Phase**: Validate file integrity, test builds, verify CI/CD, and confirm completeness

### Repository Separation Model

```
Current Monorepo (webreel)
├── TypeScript/JavaScript files → New webreel repository
├── Python files (webreel-ai-agent/) → New webreel-ai-agent repository
└── Shared docs → Distributed appropriately
```

### Git History Preservation Strategy

We will use `git filter-repo` (preferred) or `git filter-branch` to create filtered copies of the repository:

- **webreel repository**: Filter to keep only TypeScript/JavaScript related paths
- **webreel-ai-agent repository**: Filter to keep only the `webreel-ai-agent/` directory and move it to root

This approach preserves:
- Commit history for relevant files
- Author attribution
- Timestamps
- Commit messages


## Components and Interfaces

### Migration Script Components

#### 1. File Classifier

**Purpose**: Categorize files into TypeScript repository, Python repository, or shared files

**Interface**:
```python
class FileClassifier:
    def classify_file(self, file_path: str) -> RepositoryTarget
    def get_typescript_files(self) -> List[str]
    def get_python_files(self) -> List[str]
    def get_shared_files(self) -> List[str]
```

**Classification Rules**:
- TypeScript repository: `packages/`, `apps/docs/`, `examples/`, TypeScript config files, pnpm files
- Python repository: `webreel-ai-agent/` (entire directory)
- Shared: Root `docs/`, LICENSE, some root documentation files

#### 2. Git History Filter

**Purpose**: Create filtered repository copies with preserved history

**Interface**:
```python
class GitHistoryFilter:
    def filter_repository(self, source_repo: str, target_repo: str, paths: List[str]) -> bool
    def verify_history_preservation(self, original_repo: str, filtered_repo: str) -> bool
```

**Implementation Options**:
- Primary: `git filter-repo` (faster, more reliable)
- Fallback: `git filter-branch` (if filter-repo unavailable)

#### 3. File Integrity Verifier

**Purpose**: Ensure files are copied without modification

**Interface**:
```python
class FileIntegrityVerifier:
    def compute_checksum(self, file_path: str) -> str
    def verify_file_integrity(self, source: str, target: str) -> bool
    def generate_integrity_report(self) -> IntegrityReport
```

**Verification Method**: SHA-256 checksums for all files


#### 4. Repository Structure Builder

**Purpose**: Create proper directory structure in new repositories

**Interface**:
```python
class RepositoryStructureBuilder:
    def create_typescript_structure(self, target_dir: str) -> None
    def create_python_structure(self, target_dir: str) -> None
    def validate_structure(self, repo_dir: str, expected_structure: Dict) -> bool
```

**Structure Definitions**:

TypeScript Repository Structure:
```
webreel/
├── .github/workflows/          # CI/CD for TypeScript
├── .changeset/                 # Changesets configuration
├── packages/
│   ├── @webreel/core/         # Core library
│   └── webreel/               # CLI package
├── apps/
│   └── docs/                  # Documentation site
├── examples/                   # TypeScript examples
├── scripts/                    # Build scripts
├── docs/                       # General documentation
├── .gitignore                 # TypeScript-specific ignores
├── .prettierrc
├── eslint.config.js
├── package.json               # Root package.json
├── pnpm-workspace.yaml
├── pnpm-lock.yaml
├── turbo.json
├── tsconfig.json
├── LICENSE
└── README.md
```

Python Repository Structure:
```
webreel-ai-agent/
├── .github/workflows/          # CI/CD for Python
├── backend/                    # FastAPI backend
│   ├── api/
│   ├── models/
│   ├── services/
│   └── tests/
├── frontend/                   # Streamlit frontend
│   ├── components/
│   ├── pages/
│   └── tests/
├── src/                        # Pipeline logic
│   ├── pipeline/
│   └── utils/
├── tests/                      # Integration tests
├── docs/                       # AI agent documentation
├── output/                     # Generated videos (gitignored)
├── test-cases/                 # Test configurations
├── scripts/                    # Utility scripts
├── .gitignore                 # Python-specific ignores
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── LICENSE
└── README.md
```


#### 5. CI/CD Configuration Generator

**Purpose**: Create appropriate CI/CD configurations for each repository

**Interface**:
```python
class CICDConfigGenerator:
    def generate_typescript_workflows(self, target_dir: str) -> None
    def generate_python_workflows(self, target_dir: str) -> None
    def validate_workflow_syntax(self, workflow_file: str) -> bool
```

**TypeScript CI/CD Workflows**:
- `ci.yml`: Build, test, lint, type-check for all packages
- `release.yml`: Changesets-based release workflow
- `docs.yml`: Deploy documentation site to Vercel

**Python CI/CD Workflows**:
- `ci.yml`: Test, lint, type-check with pytest and mypy
- `docker.yml`: Build and publish Docker images
- `release.yml`: PyPI package publishing (optional)

#### 6. Documentation Distributor

**Purpose**: Distribute documentation appropriately between repositories

**Interface**:
```python
class DocumentationDistributor:
    def distribute_docs(self, source_repo: str, ts_repo: str, py_repo: str) -> None
    def create_cross_references(self, ts_repo: str, py_repo: str) -> None
    def update_readme_files(self, ts_repo: str, py_repo: str) -> None
```

**Distribution Strategy**:
- General Webreel docs → TypeScript repository
- AI agent-specific docs → Python repository
- Cross-references added to both README files

### Cross-Repository Integration Points

#### 1. Package References

The Python AI agent uses the TypeScript core library:
- Current: Local monorepo reference
- After split: npm package reference (`@webreel/core`)

**Integration Documentation Required**:
- How to install `@webreel/core` in Python project
- Version compatibility matrix
- Example integration code

#### 2. Shared Documentation

Both repositories will link to each other:
- TypeScript README: Link to AI agent repository
- Python README: Link to core library repository
- Documentation site: Links to both repositories


## Data Models

### File Classification Model

```python
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

class RepositoryTarget(Enum):
    TYPESCRIPT = "typescript"
    PYTHON = "python"
    BOTH = "both"
    EXCLUDE = "exclude"

@dataclass
class FileEntry:
    path: str
    target: RepositoryTarget
    checksum: str
    size: int
    is_binary: bool
```

### Migration Configuration Model

```python
@dataclass
class MigrationConfig:
    source_repo_path: str
    typescript_repo_path: str
    python_repo_path: str
    preserve_history: bool = True
    verify_checksums: bool = True
    dry_run: bool = False
    
    typescript_paths: List[str] = None
    python_paths: List[str] = None
    exclude_paths: List[str] = None
```

### Verification Report Model

```python
@dataclass
class IntegrityReport:
    total_files: int
    verified_files: int
    failed_files: List[str]
    missing_files: List[str]
    checksum_mismatches: List[tuple[str, str, str]]  # (file, expected, actual)
    
    def is_valid(self) -> bool:
        return len(self.failed_files) == 0 and len(self.missing_files) == 0

@dataclass
class HistoryReport:
    repository: str
    total_commits: int
    preserved_commits: int
    missing_commits: List[str]
    files_with_history: int
    files_without_history: List[str]
    
    def is_valid(self) -> bool:
        return len(self.missing_commits) == 0 and len(self.files_without_history) == 0
```

### Repository Structure Model

```python
@dataclass
class RepositoryStructure:
    required_files: List[str]
    required_directories: List[str]
    forbidden_patterns: List[str]  # File patterns that shouldn't exist
    
    def validate(self, repo_path: str) -> List[str]:
        """Returns list of validation errors"""
        pass

# TypeScript repository structure
TYPESCRIPT_STRUCTURE = RepositoryStructure(
    required_files=[
        "package.json",
        "pnpm-workspace.yaml",
        "turbo.json",
        "tsconfig.json",
        "README.md",
        "LICENSE",
        ".gitignore"
    ],
    required_directories=[
        "packages/@webreel/core",
        "apps/docs",
        "examples",
        ".github/workflows"
    ],
    forbidden_patterns=[
        "**/*.py",
        "**/requirements.txt",
        "**/pyproject.toml",
        "webreel-ai-agent/**"
    ]
)

# Python repository structure
PYTHON_STRUCTURE = RepositoryStructure(
    required_files=[
        "requirements.txt",
        "pyproject.toml",
        "Dockerfile",
        "docker-compose.yml",
        "README.md",
        "LICENSE",
        ".gitignore"
    ],
    required_directories=[
        "backend",
        "frontend",
        "src",
        "tests",
        ".github/workflows"
    ],
    forbidden_patterns=[
        "**/*.ts",
        "**/package.json",
        "**/pnpm-workspace.yaml",
        "**/turbo.json",
        "packages/**",
        "apps/**"
    ]
)
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system, essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing the acceptance criteria, several properties were identified as redundant or combinable:

**Redundancies Identified**:
1. Properties 2.1 and 2.3 both test file integrity through checksums (combined into Property 1)
2. Properties 1.2 and 4.6 both test TypeScript repository file type exclusion (combined into Property 2)
3. Properties 1.3 and 5.6 both test Python repository file type exclusion (combined into Property 3)
4. Properties 3.1 and 3.2 both test Git history preservation (combined into Property 5)
5. Multiple structural requirements (4.1-4.5, 5.1-5.5) are better tested as examples rather than properties

**Final Property Set**: After eliminating redundancies, we have 6 core properties that provide unique validation value.

### Property 1: File Integrity Preservation

*For any* file copied from the source monorepo to either target repository, the SHA-256 checksum of the file in the target repository must match the checksum of the file in the source repository.

**Validates: Requirements 2.1, 2.3, 2.4**

**Rationale**: This is a round-trip property that ensures no file corruption or modification occurs during migration. Binary files are included as an edge case.

### Property 2: TypeScript Repository File Type Purity

*For any* file in the TypeScript repository (excluding .gitignore and documentation), the file must match TypeScript/JavaScript ecosystem patterns (*.ts, *.js, *.json, *.md, *.yaml, *.yml, *.html, *.css) and must not match Python patterns (*.py, requirements.txt, pyproject.toml).

**Validates: Requirements 1.2, 4.6**

**Rationale**: This ensures clean separation of technology stacks. The TypeScript repository should not contain Python code.

### Property 3: Python Repository File Type Purity

*For any* file in the Python repository (excluding .gitignore and documentation), the file must match Python ecosystem patterns (*.py, *.txt, *.toml, *.yml, *.yaml, *.md, *.json, *.html) and must not match TypeScript-specific patterns (*.ts, package.json, pnpm-workspace.yaml, turbo.json).

**Validates: Requirements 1.3, 5.6**

**Rationale**: This ensures clean separation of technology stacks. The Python repository should not contain TypeScript code.


### Property 4: Directory Structure Preservation

*For any* file in the source repository that is copied to a target repository, the relative path structure from its classification root must be preserved in the target repository (e.g., `packages/@webreel/core/src/index.ts` maintains the same relative path in the TypeScript repository).

**Validates: Requirements 2.2**

**Rationale**: This is an invariant property that ensures the directory organization is maintained during migration, which is critical for imports and references to continue working.

### Property 5: Git History Completeness

*For any* file in a target repository, all commits from the source monorepo that modified that file must be present in the target repository's Git history with matching commit messages, authors, and timestamps.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

**Rationale**: This ensures complete history preservation. For every file, the evolution history should be traceable back to the original monorepo.

### Property 6: Repository Self-Containment

*For any* target repository (TypeScript or Python), all files referenced by configuration files (package.json dependencies, import statements, etc.) must either exist within the repository or be external dependencies, not references to the other repository.

**Validates: Requirements 1.4**

**Rationale**: This ensures each repository is independently functional. No broken internal references should exist after the split.

### Example-Based Validation

The following requirements are better validated through specific examples rather than properties:

**TypeScript Repository Structure** (Requirements 4.1-4.5):
- Verify `packages/@webreel/core` exists
- Verify `apps/docs` exists
- Verify `examples/` exists
- Verify required config files exist (package.json, pnpm-workspace.yaml, turbo.json, tsconfig.json)
- Verify .gitignore contains TypeScript-appropriate patterns

**Python Repository Structure** (Requirements 5.1-5.7):
- Verify `backend/` exists
- Verify `frontend/` exists
- Verify `src/` exists
- Verify `tests/` exists
- Verify required config files exist (requirements.txt, pyproject.toml, Dockerfile, docker-compose.yml)
- Verify .gitignore contains Python-appropriate patterns

**Documentation Distribution** (Requirements 6.1-6.5):
- Verify TypeScript repository contains `docs/` directory
- Verify TypeScript repository contains `apps/docs/`
- Verify Python repository contains `docs/` directory
- Verify both README files contain cross-references

**CI/CD Configuration** (Requirements 7.1-7.5):
- Verify TypeScript repository has `.github/workflows/ci.yml` with TypeScript jobs
- Verify TypeScript repository has `.github/workflows/release.yml` with changesets
- Verify Python repository has `.github/workflows/ci.yml` with Python jobs
- Verify Python repository has `.github/workflows/docker.yml`

**Output Directory Organization** (Requirements 10.1-10.4):
- Verify Python repository contains `output/` directory
- Verify TypeScript repository does not contain `output/` directory
- Verify .gitignore files properly exclude output directories


## Error Handling

### Migration Errors

**File Not Found Errors**:
- **Scenario**: Expected file missing during migration
- **Handling**: Log error, add to missing files report, continue with other files
- **Recovery**: Manual review of missing files list, determine if intentional or error

**Checksum Mismatch Errors**:
- **Scenario**: File checksum doesn't match after copy
- **Handling**: Log error with both checksums, mark file as failed, halt migration
- **Recovery**: Investigate cause (corruption, modification), re-run migration for affected files

**Git History Errors**:
- **Scenario**: Git filter operation fails or produces incomplete history
- **Handling**: Log detailed error, preserve original repository, halt migration
- **Recovery**: Review git filter-repo/filter-branch logs, adjust path filters, retry

**Permission Errors**:
- **Scenario**: Insufficient permissions to read source or write target
- **Handling**: Log error with specific file/directory, halt migration
- **Recovery**: Adjust file permissions, verify user has necessary access rights

### Validation Errors

**Structure Validation Failures**:
- **Scenario**: Required files or directories missing in target repository
- **Handling**: Generate detailed validation report, list all missing items
- **Recovery**: Review classification rules, ensure all required files are included in migration

**File Type Contamination**:
- **Scenario**: Python files found in TypeScript repository or vice versa
- **Handling**: List all contaminated files, halt deployment
- **Recovery**: Review and fix file classification rules, re-run migration

**Broken References**:
- **Scenario**: Import statements or configuration references point to non-existent files
- **Handling**: Scan for broken references, generate report
- **Recovery**: Update references to use external packages or fix paths

### CI/CD Errors

**Workflow Syntax Errors**:
- **Scenario**: Generated GitHub Actions workflows have syntax errors
- **Handling**: Validate YAML syntax before committing, report errors
- **Recovery**: Fix workflow templates, regenerate workflows

**Build Failures**:
- **Scenario**: Initial build fails in new repository
- **Handling**: Capture build logs, identify missing dependencies or configuration
- **Recovery**: Update configuration files, install missing dependencies


## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests to ensure comprehensive validation:

**Unit Tests**: Verify specific examples, edge cases, and error conditions
- Specific directory structure validation
- Configuration file presence checks
- CI/CD workflow syntax validation
- Cross-reference documentation checks

**Property Tests**: Verify universal properties across all inputs
- File integrity preservation across all files
- File type purity across all files in each repository
- Directory structure preservation for all copied files
- Git history completeness for all files
- Repository self-containment for all references

Both testing approaches are complementary and necessary. Unit tests catch concrete structural issues, while property tests verify general correctness across the entire migration.

### Property-Based Testing Configuration

**Testing Library**: Use `hypothesis` for Python property-based testing

**Test Configuration**:
- Minimum 100 iterations per property test (due to randomization)
- Each property test must reference its design document property
- Tag format: `# Feature: monorepo-split-option2, Property {number}: {property_text}`

**Property Test Implementation**:

Each correctness property must be implemented by a single property-based test:

1. **Property 1 Test**: File Integrity Preservation
   - Generate random sample of files from migration
   - Compute checksums for source and target
   - Assert all checksums match

2. **Property 2 Test**: TypeScript Repository File Type Purity
   - Generate list of all files in TypeScript repository
   - For each file, verify it matches allowed patterns
   - Assert no Python-specific files exist

3. **Property 3 Test**: Python Repository File Type Purity
   - Generate list of all files in Python repository
   - For each file, verify it matches allowed patterns
   - Assert no TypeScript-specific files exist

4. **Property 4 Test**: Directory Structure Preservation
   - Generate random sample of files from migration
   - For each file, verify relative path is preserved
   - Assert directory structure matches source

5. **Property 5 Test**: Git History Completeness
   - Generate random sample of files from target repositories
   - For each file, get commit history from source and target
   - Assert all source commits exist in target with matching metadata

6. **Property 6 Test**: Repository Self-Containment
   - Parse all configuration files and import statements
   - Generate list of all file references
   - Assert all references either exist in repository or are external dependencies


### Unit Testing Strategy

**Test Organization**:
```
tests/
├── test_file_classifier.py          # File classification logic
├── test_git_history_filter.py       # Git history preservation
├── test_file_integrity.py           # Checksum verification
├── test_structure_builder.py        # Directory structure creation
├── test_cicd_generator.py           # CI/CD configuration generation
├── test_documentation.py            # Documentation distribution
└── test_integration.py              # End-to-end migration test
```

**Unit Test Coverage**:

1. **File Classification Tests**:
   - Test TypeScript file patterns are correctly identified
   - Test Python file patterns are correctly identified
   - Test shared files are correctly identified
   - Test edge cases (mixed extensions, hidden files)

2. **Git History Tests**:
   - Test git filter-repo command generation
   - Test history verification logic
   - Test commit metadata extraction
   - Test handling of merge commits

3. **File Integrity Tests**:
   - Test checksum computation for text files
   - Test checksum computation for binary files
   - Test checksum comparison logic
   - Test handling of large files

4. **Structure Builder Tests**:
   - Test TypeScript repository structure creation
   - Test Python repository structure creation
   - Test structure validation logic
   - Test handling of missing directories

5. **CI/CD Generator Tests**:
   - Test TypeScript workflow generation
   - Test Python workflow generation
   - Test YAML syntax validation
   - Test workflow customization

6. **Documentation Tests**:
   - Test documentation distribution logic
   - Test cross-reference generation
   - Test README updates
   - Test link validation

7. **Integration Tests**:
   - Test complete migration workflow on test repository
   - Test rollback procedure
   - Test verification scripts
   - Test error recovery scenarios

### Manual Testing Checklist

After automated tests pass, perform manual verification:

**TypeScript Repository**:
- [ ] Clone repository and run `pnpm install`
- [ ] Run `pnpm build` and verify all packages build successfully
- [ ] Run `pnpm test` and verify all tests pass
- [ ] Run `pnpm type-check` and verify no type errors
- [ ] Verify documentation site builds and deploys
- [ ] Check GitHub Actions workflows run successfully
- [ ] Verify examples work correctly

**Python Repository**:
- [ ] Clone repository and create virtual environment
- [ ] Run `pip install -r requirements.txt`
- [ ] Run `pytest` and verify all tests pass
- [ ] Run `mypy` and verify type checking passes
- [ ] Build Docker image and verify it runs
- [ ] Check GitHub Actions workflows run successfully
- [ ] Verify backend and frontend start correctly

**Cross-Repository Integration**:
- [ ] Install `@webreel/core` from npm in Python project
- [ ] Verify integration examples work
- [ ] Check cross-references in documentation are valid
- [ ] Verify both repositories can be developed independently


## Implementation Details

### Phase 1: Preparation

**Step 1.1: Install Git Filter-Repo**
```bash
pip install git-filter-repo
```

**Step 1.2: Create File Classification Map**

Create a configuration file that defines which paths go to which repository:

```python
# migration_config.py
TYPESCRIPT_PATHS = [
    "packages/",
    "apps/docs/",
    "examples/",
    "scripts/",
    "docs/",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
    ".changeset/",
    ".husky/",
    "package.json",
    "pnpm-workspace.yaml",
    "pnpm-lock.yaml",
    "turbo.json",
    "tsconfig.json",
    "eslint.config.js",
    ".prettierrc",
    ".prettierignore",
    ".gitignore",
    ".gitattributes",
    "LICENSE",
    "README.md"
]

PYTHON_PATHS = [
    "webreel-ai-agent/"
]

EXCLUDE_PATHS = [
    "node_modules/",
    ".venv/",
    "venv/",
    ".git/",
    ".turbo/",
    "output/",
    "videos/",
    ".webreel/",
    "__pycache__/",
    "*.pyc",
    ".pytest_cache/"
]
```

**Step 1.3: Create Backup**
```bash
# Create backup of original monorepo
cp -r webreel webreel-backup
```

### Phase 2: Execution

**Step 2.1: Create TypeScript Repository**

```bash
# Clone the monorepo
git clone webreel webreel-typescript
cd webreel-typescript

# Filter to keep only TypeScript-related paths
git filter-repo --path packages/ \
                --path apps/docs/ \
                --path examples/ \
                --path scripts/ \
                --path docs/ \
                --path .github/workflows/ci.yml \
                --path .github/workflows/release.yml \
                --path .changeset/ \
                --path .husky/ \
                --path package.json \
                --path pnpm-workspace.yaml \
                --path pnpm-lock.yaml \
                --path turbo.json \
                --path tsconfig.json \
                --path eslint.config.js \
                --path .prettierrc \
                --path .prettierignore \
                --path LICENSE \
                --path README.md \
                --force

# Update remote
git remote add origin git@github.com:your-org/webreel.git
```

**Step 2.2: Create Python Repository**

```bash
# Clone the monorepo
git clone webreel webreel-python
cd webreel-python

# Filter to keep only Python-related paths and move to root
git filter-repo --path webreel-ai-agent/ \
                --path-rename webreel-ai-agent/:'' \
                --force

# Update remote
git remote add origin git@github.com:your-org/webreel-ai-agent.git
```


**Step 2.3: Update Configuration Files**

TypeScript Repository Updates:
```bash
cd webreel-typescript

# Update README.md to add reference to Python repository
# Update .gitignore to remove Python-specific patterns
# Verify package.json workspace configuration
# Update documentation to reflect new structure
```

Python Repository Updates:
```bash
cd webreel-python

# Update README.md to add reference to TypeScript repository
# Update .gitignore to remove TypeScript-specific patterns
# Update requirements.txt if needed
# Update Dockerfile paths if needed
# Update documentation to reflect new structure
```

**Step 2.4: Create CI/CD Workflows**

TypeScript Repository (`.github/workflows/ci.yml`):
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
        with:
          version: 8
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'pnpm'
      - run: pnpm install
      - run: pnpm build
      - run: pnpm test
      - run: pnpm type-check
```

Python Repository (`.github/workflows/ci.yml`):
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest
      - run: mypy .
```

### Phase 3: Verification

**Step 3.1: Run Verification Script**

```python
# verify_migration.py
import hashlib
import os
from pathlib import Path

def verify_file_integrity(source_repo: str, target_repo: str, file_list: list[str]):
    """Verify all files have matching checksums"""
    mismatches = []
    
    for file_path in file_list:
        source_file = Path(source_repo) / file_path
        target_file = Path(target_repo) / file_path
        
        if not target_file.exists():
            mismatches.append(f"Missing: {file_path}")
            continue
            
        source_hash = hashlib.sha256(source_file.read_bytes()).hexdigest()
        target_hash = hashlib.sha256(target_file.read_bytes()).hexdigest()
        
        if source_hash != target_hash:
            mismatches.append(f"Checksum mismatch: {file_path}")
    
    return mismatches

def verify_git_history(repo_path: str, file_path: str):
    """Verify Git history exists for file"""
    import subprocess
    
    result = subprocess.run(
        ["git", "log", "--oneline", file_path],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    return len(result.stdout.strip().split('\n')) if result.stdout else 0

def verify_structure(repo_path: str, required_items: list[str]):
    """Verify required files and directories exist"""
    missing = []
    
    for item in required_items:
        if not (Path(repo_path) / item).exists():
            missing.append(item)
    
    return missing

# Run verification
print("Verifying TypeScript repository...")
ts_missing = verify_structure("webreel-typescript", TYPESCRIPT_STRUCTURE.required_files)
print(f"Missing files: {ts_missing}")

print("\nVerifying Python repository...")
py_missing = verify_structure("webreel-python", PYTHON_STRUCTURE.required_files)
print(f"Missing files: {py_missing}")

print("\nVerifying file integrity...")
# Add file integrity checks here
```

**Step 3.2: Test Builds**

```bash
# Test TypeScript repository
cd webreel-typescript
pnpm install
pnpm build
pnpm test
pnpm type-check

# Test Python repository
cd webreel-python
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
pytest
mypy .
```

**Step 3.3: Verify CI/CD**

- Push both repositories to GitHub
- Verify CI workflows run successfully
- Check that all tests pass
- Verify build artifacts are created correctly


### Phase 4: Documentation and Finalization

**Step 4.1: Update README Files**

TypeScript Repository README additions:
```markdown
## Related Projects

This repository contains the core Webreel library. For the AI-powered agent that uses Webreel, see:
- [webreel-ai-agent](https://github.com/your-org/webreel-ai-agent) - Python-based AI agent for automated video generation

## Installation

```bash
npm install @webreel/core
# or
pnpm add @webreel/core
```

## Integration with AI Agent

The Webreel AI agent uses this core library. To integrate:

1. Install the core library: `npm install @webreel/core`
2. Follow the AI agent setup instructions in the [webreel-ai-agent repository](https://github.com/your-org/webreel-ai-agent)
```

Python Repository README additions:
```markdown
## Related Projects

This repository contains the Webreel AI agent. It uses the core Webreel library:
- [@webreel/core](https://github.com/your-org/webreel) - TypeScript core library for browser automation

## Prerequisites

- Python 3.12+
- Node.js 20+ (for @webreel/core dependency)

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Webreel core library
npm install @webreel/core
```

## Integration with Core Library

This project uses `@webreel/core` for browser automation. The core library is installed via npm and used through the pipeline.
```

**Step 4.2: Create Migration Documentation**

Create `MIGRATION.md` in both repositories:

```markdown
# Migration from Monorepo

This repository was split from the original Webreel monorepo on [DATE].

## History Preservation

Git history has been preserved for all files in this repository. To view the complete history including the monorepo period:

```bash
git log --follow <file-path>
```

## Original Monorepo

The original monorepo is archived at: [link to archived monorepo]

## Related Repositories

- [webreel](https://github.com/your-org/webreel) - TypeScript core library
- [webreel-ai-agent](https://github.com/your-org/webreel-ai-agent) - Python AI agent

## Migration Details

- Migration date: [DATE]
- Migration method: git filter-repo
- Verification: All files verified with SHA-256 checksums
```

**Step 4.3: Archive Original Monorepo**

```bash
# Add archive notice to original monorepo README
cd webreel-original
git checkout -b archive-notice

# Update README.md
cat >> README.md << 'EOF'

---

## ⚠️ Repository Archived

This monorepo has been split into separate repositories:

- **TypeScript Core Library**: [webreel](https://github.com/your-org/webreel)
- **Python AI Agent**: [webreel-ai-agent](https://github.com/your-org/webreel-ai-agent)

Please use the new repositories for all future development.

This repository is maintained for historical reference only.
EOF

git add README.md
git commit -m "Add archive notice"
git push origin archive-notice

# Archive the repository on GitHub (via Settings > Archive this repository)
```


## Rollback Strategy

### Rollback Triggers

Rollback should be initiated if:
- File integrity verification fails (checksums don't match)
- Critical files are missing in target repositories
- Git history is incomplete or corrupted
- Builds fail in both target repositories
- CI/CD pipelines cannot be configured correctly

### Rollback Procedure

**Step 1: Preserve Current State**
```bash
# Rename failed migration attempts
mv webreel-typescript webreel-typescript-failed
mv webreel-python webreel-python-failed
```

**Step 2: Restore from Backup**
```bash
# Restore original monorepo from backup
cp -r webreel-backup webreel
cd webreel

# Verify backup integrity
git status
git log --oneline -10
```

**Step 3: Analyze Failure**
```bash
# Review migration logs
cat migration.log

# Compare failed repositories with backup
diff -r webreel-backup webreel-typescript-failed
diff -r webreel-backup/webreel-ai-agent webreel-python-failed
```

**Step 4: Document Issues**

Create an issue documenting:
- What triggered the rollback
- Which verification checks failed
- Error messages and logs
- Proposed fixes for next attempt

**Step 5: Fix and Retry**

Based on the analysis:
- Update file classification rules
- Fix git filter-repo commands
- Adjust verification scripts
- Re-run migration with fixes

### Partial Rollback

If only one repository has issues:

**TypeScript Repository Issues**:
```bash
# Keep Python repository, recreate TypeScript repository
rm -rf webreel-typescript
git clone webreel-backup webreel-typescript
# Re-run TypeScript filtering with fixes
```

**Python Repository Issues**:
```bash
# Keep TypeScript repository, recreate Python repository
rm -rf webreel-python
git clone webreel-backup webreel-python
# Re-run Python filtering with fixes
```

## Risk Mitigation

### Pre-Migration Risks

**Risk**: Incomplete file classification
- **Mitigation**: Review file classification map with team
- **Validation**: Run dry-run migration and review file lists

**Risk**: Git history corruption
- **Mitigation**: Test git filter-repo on small test repository first
- **Validation**: Verify history on sample files before full migration

**Risk**: Broken dependencies after split
- **Mitigation**: Document all cross-repository dependencies
- **Validation**: Test builds immediately after split

### During Migration Risks

**Risk**: Data loss during file copying
- **Mitigation**: Use checksums for all files, maintain backup
- **Validation**: Verify checksums after each copy operation

**Risk**: Incomplete Git history
- **Mitigation**: Use --force flag carefully, verify history preservation
- **Validation**: Check commit counts and history depth

**Risk**: Configuration file errors
- **Mitigation**: Validate all configuration files before committing
- **Validation**: Run syntax checkers and linters

### Post-Migration Risks

**Risk**: Broken CI/CD pipelines
- **Mitigation**: Test workflows locally before pushing
- **Validation**: Monitor first CI runs closely

**Risk**: Integration issues between repositories
- **Mitigation**: Create integration examples and test them
- **Validation**: Verify examples work with published packages

**Risk**: Documentation gaps
- **Mitigation**: Review all documentation for accuracy
- **Validation**: Have team members follow setup instructions


## Migration Timeline

### Estimated Duration: 4-6 hours

**Phase 1: Preparation (1-2 hours)**
- Install tools and dependencies: 15 minutes
- Create file classification map: 30 minutes
- Review and validate classification: 30 minutes
- Create backup: 15 minutes

**Phase 2: Execution (1-2 hours)**
- Create TypeScript repository: 30 minutes
- Create Python repository: 30 minutes
- Update configuration files: 30 minutes
- Create CI/CD workflows: 30 minutes

**Phase 3: Verification (1-2 hours)**
- Run verification scripts: 30 minutes
- Test builds in both repositories: 30 minutes
- Verify CI/CD pipelines: 30 minutes
- Manual testing: 30 minutes

**Phase 4: Documentation and Finalization (1 hour)**
- Update README files: 20 minutes
- Create migration documentation: 20 minutes
- Archive original monorepo: 20 minutes

### Critical Path

The following steps must be completed in order:
1. Backup creation (cannot proceed without backup)
2. Git filtering (must complete before verification)
3. File integrity verification (must pass before proceeding)
4. Build testing (must pass before pushing to GitHub)
5. CI/CD verification (must pass before archiving monorepo)

### Parallel Work Opportunities

These tasks can be done in parallel:
- TypeScript and Python repository creation (after backup)
- Documentation updates for both repositories
- CI/CD workflow creation for both repositories
- Verification scripts for both repositories

## Success Metrics

### Quantitative Metrics

1. **File Integrity**: 100% of files must have matching checksums
2. **Git History**: 100% of relevant commits must be preserved
3. **Build Success**: Both repositories must build without errors
4. **Test Success**: All tests must pass in both repositories
5. **CI/CD Success**: All workflows must run successfully

### Qualitative Metrics

1. **Developer Experience**: Developers can clone and work with either repository independently
2. **Documentation Quality**: Setup instructions are clear and complete
3. **Integration Clarity**: Cross-repository integration is well-documented
4. **Maintainability**: Each repository is independently maintainable

### Acceptance Criteria

The migration is considered successful when:
- [ ] Both repositories exist and are accessible on GitHub
- [ ] All verification scripts pass without errors
- [ ] Builds succeed in both repositories
- [ ] All tests pass in both repositories
- [ ] CI/CD pipelines run successfully
- [ ] Documentation is complete and accurate
- [ ] Team members can follow setup instructions successfully
- [ ] Integration examples work correctly
- [ ] No files are missing or corrupted
- [ ] Git history is complete and accurate


## Appendix A: File Classification Reference

### TypeScript Repository Files

**Core Packages**:
- `packages/@webreel/core/` - Core library
- `packages/webreel/` - CLI package

**Applications**:
- `apps/docs/` - Documentation website (Next.js)

**Examples**:
- `examples/custom-theme/`
- `examples/drag-and-drop/`
- `examples/form-filling/`
- `examples/gif-output/`
- `examples/hello-world/`
- `examples/keyboard-shortcuts/`
- `examples/mobile-viewport/`
- `examples/modifier-clicks/`
- `examples/multi-demo/`
- `examples/page-scrolling/`
- `examples/screenshots/`
- `examples/shared-steps/`
- `examples/webm-output/`

**Configuration Files**:
- `package.json` - Root package configuration
- `pnpm-workspace.yaml` - pnpm workspace configuration
- `pnpm-lock.yaml` - Dependency lock file
- `turbo.json` - Turborepo configuration
- `tsconfig.json` - TypeScript configuration
- `eslint.config.js` - ESLint configuration
- `.prettierrc` - Prettier configuration
- `.prettierignore` - Prettier ignore patterns

**CI/CD**:
- `.github/workflows/ci.yml` - Continuous integration
- `.github/workflows/release.yml` - Release workflow
- `.changeset/` - Changesets configuration
- `.husky/` - Git hooks

**Documentation**:
- `docs/` - General documentation
- `README.md` - Repository README
- `LICENSE` - License file

**Other**:
- `scripts/` - Build and utility scripts
- `.gitignore` - Git ignore patterns
- `.gitattributes` - Git attributes

### Python Repository Files

**Application Code**:
- `backend/` - FastAPI backend application
- `frontend/` - Streamlit frontend application
- `src/` - Pipeline logic and utilities
- `v3/` - Version 3 pipeline implementation

**Tests**:
- `tests/` - Integration tests
- `backend/tests/` - Backend unit tests
- `frontend/tests/` - Frontend unit tests

**Configuration Files**:
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Python project configuration
- `Dockerfile` - Docker image definition
- `docker-compose.yml` - Docker Compose configuration
- `.dockerignore` - Docker ignore patterns

**Documentation**:
- `docs/` - AI agent documentation
- `README.md` - Repository README
- `README_PIPELINE.md` - Pipeline documentation
- `MIGRATION_GUIDE.md` - Migration guide
- `TESTING_GUIDE.md` - Testing guide
- Various other .md files

**Test Cases and Scripts**:
- `test-cases/` - Test HTML files and configurations
- `scripts/` - Utility scripts
- Various test configuration files (*.config.json)
- Various test scripts (test_*.py)

**Output Directories** (gitignored):
- `output/` - Generated videos
- `videos/` - Test videos
- `.webreel/` - Webreel cache

**Other**:
- `.gitignore` - Git ignore patterns
- `.env.example` - Environment variables example
- `LICENSE` - License file

### Excluded Files (Not in Either Repository)

**Build Artifacts**:
- `node_modules/` - Node.js dependencies
- `.venv/`, `venv/` - Python virtual environments
- `__pycache__/` - Python bytecode cache
- `.pytest_cache/` - Pytest cache
- `.turbo/` - Turborepo cache

**Generated Files**:
- `output/` (root level) - Old output directory
- `videos/` (root level) - Old videos directory
- `.webreel/` (root level) - Old cache directory

**Temporary Files**:
- `*.pyc` - Python bytecode
- `*.log` - Log files
- `.DS_Store` - macOS metadata


## Appendix B: Git Filter-Repo Commands

### Complete TypeScript Repository Filter Command

```bash
git filter-repo \
  --path packages/ \
  --path apps/docs/ \
  --path examples/ \
  --path scripts/ \
  --path docs/ \
  --path .github/workflows/ci.yml \
  --path .github/workflows/release.yml \
  --path .changeset/ \
  --path .husky/ \
  --path package.json \
  --path pnpm-workspace.yaml \
  --path pnpm-lock.yaml \
  --path turbo.json \
  --path tsconfig.json \
  --path eslint.config.js \
  --path .prettierrc \
  --path .prettierignore \
  --path .gitignore \
  --path .gitattributes \
  --path LICENSE \
  --path README.md \
  --force
```

### Complete Python Repository Filter Command

```bash
git filter-repo \
  --path webreel-ai-agent/ \
  --path-rename webreel-ai-agent/:'' \
  --force
```

### Alternative: Using Path File

Create `typescript-paths.txt`:
```
packages/
apps/docs/
examples/
scripts/
docs/
.github/workflows/ci.yml
.github/workflows/release.yml
.changeset/
.husky/
package.json
pnpm-workspace.yaml
pnpm-lock.yaml
turbo.json
tsconfig.json
eslint.config.js
.prettierrc
.prettierignore
.gitignore
.gitattributes
LICENSE
README.md
```

Then run:
```bash
git filter-repo --paths-from-file typescript-paths.txt --force
```

## Appendix C: Verification Scripts

### Complete Verification Script

```python
#!/usr/bin/env python3
"""
Migration verification script for monorepo split.
Verifies file integrity, Git history, and repository structure.
"""

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

def compute_checksum(file_path: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def verify_file_integrity(source_repo: Path, target_repo: Path, 
                         relative_paths: List[str]) -> Tuple[int, List[str]]:
    """Verify file integrity between source and target repositories."""
    passed = 0
    failed = []
    
    for rel_path in relative_paths:
        source_file = source_repo / rel_path
        target_file = target_repo / rel_path
        
        if not source_file.exists():
            continue
            
        if not target_file.exists():
            failed.append(f"Missing: {rel_path}")
            continue
        
        source_hash = compute_checksum(source_file)
        target_hash = compute_checksum(target_file)
        
        if source_hash == target_hash:
            passed += 1
        else:
            failed.append(f"Checksum mismatch: {rel_path}")
    
    return passed, failed

def verify_git_history(repo_path: Path, file_path: str) -> int:
    """Count commits in Git history for a file."""
    result = subprocess.run(
        ["git", "log", "--oneline", "--", file_path],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        return 0
    
    lines = result.stdout.strip().split('\n')
    return len(lines) if lines[0] else 0

def verify_structure(repo_path: Path, required_items: List[str]) -> Tuple[int, List[str]]:
    """Verify required files and directories exist."""
    passed = 0
    missing = []
    
    for item in required_items:
        if (repo_path / item).exists():
            passed += 1
        else:
            missing.append(item)
    
    return passed, missing

def main():
    print("=" * 60)
    print("Monorepo Split Verification")
    print("=" * 60)
    
    # Configuration
    source_repo = Path("webreel-backup")
    ts_repo = Path("webreel-typescript")
    py_repo = Path("webreel-python")
    
    # TypeScript repository verification
    print(f"\n{Colors.YELLOW}Verifying TypeScript Repository...{Colors.RESET}")
    
    ts_required = [
        "package.json",
        "pnpm-workspace.yaml",
        "turbo.json",
        "tsconfig.json",
        "packages/@webreel/core",
        "apps/docs",
        "examples"
    ]
    
    ts_passed, ts_missing = verify_structure(ts_repo, ts_required)
    print(f"Structure: {ts_passed}/{len(ts_required)} items present")
    
    if ts_missing:
        print(f"{Colors.RED}Missing items:{Colors.RESET}")
        for item in ts_missing:
            print(f"  - {item}")
    else:
        print(f"{Colors.GREEN}✓ All required items present{Colors.RESET}")
    
    # Python repository verification
    print(f"\n{Colors.YELLOW}Verifying Python Repository...{Colors.RESET}")
    
    py_required = [
        "requirements.txt",
        "pyproject.toml",
        "Dockerfile",
        "docker-compose.yml",
        "backend",
        "frontend",
        "src"
    ]
    
    py_passed, py_missing = verify_structure(py_repo, py_required)
    print(f"Structure: {py_passed}/{len(py_required)} items present")
    
    if py_missing:
        print(f"{Colors.RED}Missing items:{Colors.RESET}")
        for item in py_missing:
            print(f"  - {item}")
    else:
        print(f"{Colors.GREEN}✓ All required items present{Colors.RESET}")
    
    # Summary
    print(f"\n{'=' * 60}")
    print("Verification Summary")
    print("=" * 60)
    
    all_passed = len(ts_missing) == 0 and len(py_missing) == 0
    
    if all_passed:
        print(f"{Colors.GREEN}✓ All verifications passed!{Colors.RESET}")
        return 0
    else:
        print(f"{Colors.RED}✗ Some verifications failed{Colors.RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

## Appendix D: Post-Migration Checklist

### Immediate Post-Migration (Day 1)

- [ ] Both repositories pushed to GitHub
- [ ] CI/CD workflows running successfully
- [ ] All tests passing in both repositories
- [ ] Documentation reviewed and updated
- [ ] Team notified of new repository structure

### Short-Term (Week 1)

- [ ] Integration examples tested and verified
- [ ] Developer setup instructions validated by team
- [ ] Cross-repository references working correctly
- [ ] Original monorepo archived with notice
- [ ] Migration documentation complete

### Medium-Term (Month 1)

- [ ] All team members using new repositories
- [ ] No issues reported with repository structure
- [ ] CI/CD pipelines stable and reliable
- [ ] Documentation feedback incorporated
- [ ] Release process tested in both repositories

### Long-Term (Quarter 1)

- [ ] Independent development workflows established
- [ ] Cross-repository integration patterns documented
- [ ] Version compatibility matrix maintained
- [ ] Community feedback incorporated
- [ ] Migration considered successful and complete

---

**Document Version**: 1.0  
**Last Updated**: [DATE]  
**Status**: Draft  
**Reviewers**: [NAMES]
