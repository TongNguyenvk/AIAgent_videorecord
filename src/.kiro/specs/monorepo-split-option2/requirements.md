# Feature Requirements: Monorepo Split - Option 2 (Separate Repositories)

## Overview

This feature implements the separation of the current Webreel monorepo into two independent repositories: one for the TypeScript core library and one for the Python AI agent application. This addresses the technology stack mismatch and improves developer experience by creating clear boundaries between the two distinct projects.

## Requirements

### Requirement 1: Repository Structure Separation

**User Story:** As a developer, I want the TypeScript core library and Python AI agent in separate repositories, so that I can work with only the technology stack I need.

#### Acceptance Criteria

1. WHEN the split is complete THEN the system SHALL have two independent Git repositories: `webreel` and `webreel-ai-agent`
2. WHEN viewing the `webreel` repository THEN the system SHALL contain only TypeScript/JavaScript code, packages, and related tooling
3. WHEN viewing the `webreel-ai-agent` repository THEN the system SHALL contain only Python code, backend, frontend, and related tooling
4. WHEN examining either repository THEN the system SHALL have a complete, self-contained project structure with all necessary configuration files

### Requirement 2: File Migration Without Modification

**User Story:** As a repository maintainer, I want files to be copied without content modifications during migration, so that I can verify the split was performed correctly and maintain code integrity.

#### Acceptance Criteria

1. WHEN copying files from the monorepo to the new repositories THEN the system SHALL preserve exact file contents without modifications
2. WHEN copying directories THEN the system SHALL maintain the directory structure and file organization
3. WHEN the migration is complete THEN the system SHALL allow verification that all files match their source exactly
4. WHEN handling binary files THEN the system SHALL preserve file integrity and checksums

### Requirement 3: Git History Preservation

**User Story:** As a developer, I want to preserve relevant Git history in each repository, so that I can understand the evolution of the codebase and maintain attribution.

#### Acceptance Criteria

1. WHEN creating the `webreel` repository THEN the system SHALL preserve Git history for all TypeScript/JavaScript files and related directories
2. WHEN creating the `webreel-ai-agent` repository THEN the system SHALL preserve Git history for all Python files and the `webreel-ai-agent/` directory
3. WHEN examining commit history THEN the system SHALL maintain original commit messages, authors, and timestamps
4. WHEN viewing file history THEN the system SHALL show the complete evolution of each file from the original monorepo

### Requirement 4: TypeScript Repository Structure

**User Story:** As a TypeScript developer, I want a clean repository structure for the core library, so that I can easily navigate and contribute to the project.

#### Acceptance Criteria

1. WHEN the `webreel` repository is created THEN the system SHALL include the `packages/` directory with `@webreel/core`
2. WHEN the `webreel` repository is created THEN the system SHALL include the `apps/docs/` directory for documentation
3. WHEN the `webreel` repository is created THEN the system SHALL include `examples/` directory with TypeScript examples
4. WHEN the `webreel` repository is created THEN the system SHALL include all root-level configuration files (package.json, pnpm-workspace.yaml, turbo.json, tsconfig.json)
5. WHEN the `webreel` repository is created THEN the system SHALL include appropriate .gitignore for TypeScript projects
6. WHEN the `webreel` repository is created THEN the system SHALL exclude all Python-related files and directories

### Requirement 5: Python Repository Structure

**User Story:** As a Python developer, I want a clean repository structure for the AI agent, so that I can easily navigate and contribute to the project.

#### Acceptance Criteria

1. WHEN the `webreel-ai-agent` repository is created THEN the system SHALL include the `backend/` directory with FastAPI application
2. WHEN the `webreel-ai-agent` repository is created THEN the system SHALL include the `frontend/` directory with Streamlit application
3. WHEN the `webreel-ai-agent` repository is created THEN the system SHALL include the `src/` directory with pipeline logic
4. WHEN the `webreel-ai-agent` repository is created THEN the system SHALL include the `tests/` directory with all test files
5. WHEN the `webreel-ai-agent` repository is created THEN the system SHALL include all Python configuration files (requirements.txt, pyproject.toml, Dockerfile, docker-compose.yml)
6. WHEN the `webreel-ai-agent` repository is created THEN the system SHALL include appropriate .gitignore for Python projects
7. WHEN the `webreel-ai-agent` repository is created THEN the system SHALL exclude all TypeScript-related files and directories

### Requirement 6: Documentation Migration

**User Story:** As a user, I want documentation to be properly distributed between repositories, so that I can find relevant information in the appropriate location.

#### Acceptance Criteria

1. WHEN the `webreel` repository is created THEN the system SHALL include general Webreel documentation from `docs/` directory
2. WHEN the `webreel` repository is created THEN the system SHALL include the documentation website in `apps/docs/`
3. WHEN the `webreel-ai-agent` repository is created THEN the system SHALL include AI agent-specific documentation from `webreel-ai-agent/docs/`
4. WHEN the `webreel-ai-agent` repository is created THEN the system SHALL include a comprehensive README.md with setup instructions
5. WHEN viewing either repository THEN the system SHALL provide cross-references to the other repository where appropriate

### Requirement 7: CI/CD Configuration

**User Story:** As a DevOps engineer, I want separate CI/CD configurations for each repository, so that builds and tests run efficiently for each technology stack.

#### Acceptance Criteria

1. WHEN the `webreel` repository is created THEN the system SHALL include GitHub Actions workflows for TypeScript (build, test, lint, type-check)
2. WHEN the `webreel` repository is created THEN the system SHALL include workflows for npm package publishing
3. WHEN the `webreel-ai-agent` repository is created THEN the system SHALL include GitHub Actions workflows for Python (test, lint, type-check)
4. WHEN the `webreel-ai-agent` repository is created THEN the system SHALL include workflows for Docker image building and publishing
5. WHEN CI/CD runs in either repository THEN the system SHALL only execute tests and checks relevant to that repository's technology stack

### Requirement 8: Dependency Management

**User Story:** As a developer, I want clear dependency management in each repository, so that I can install and manage dependencies without conflicts.

#### Acceptance Criteria

1. WHEN the `webreel` repository is created THEN the system SHALL use pnpm for package management with a valid pnpm-workspace.yaml
2. WHEN the `webreel` repository is created THEN the system SHALL have a root package.json with workspace configuration
3. WHEN the `webreel-ai-agent` repository is created THEN the system SHALL use pip/poetry for package management with requirements.txt or pyproject.toml
4. WHEN installing dependencies in either repository THEN the system SHALL not require the other repository's package manager

### Requirement 9: Cross-Repository Integration

**User Story:** As a developer, I want clear documentation on how the two repositories integrate, so that I can use them together effectively.

#### Acceptance Criteria

1. WHEN the split is complete THEN the system SHALL provide documentation on how to use `@webreel/core` with the AI agent
2. WHEN the split is complete THEN the system SHALL include examples of integration between the two projects
3. WHEN the split is complete THEN the system SHALL document the relationship between the repositories in both README files
4. WHEN issues span both repositories THEN the system SHALL provide guidance on cross-repository issue linking

### Requirement 10: Output Directory Cleanup

**User Story:** As a developer, I want output directories to be properly organized, so that generated files are stored in the correct location.

#### Acceptance Criteria

1. WHEN the `webreel-ai-agent` repository is created THEN the system SHALL include the `output/` directory for generated videos
2. WHEN the `webreel` repository is created THEN the system SHALL NOT include any output directories from the AI agent
3. WHEN the split is complete THEN the system SHALL have removed duplicate or unclear output directories
4. WHEN the split is complete THEN the system SHALL update .gitignore files to properly exclude output directories

### Requirement 11: Migration Verification

**User Story:** As a repository maintainer, I want to verify the migration was successful, so that I can ensure no files were lost or corrupted.

#### Acceptance Criteria

1. WHEN the migration is complete THEN the system SHALL provide a verification script or checklist
2. WHEN running verification THEN the system SHALL confirm all expected files are present in each repository
3. WHEN running verification THEN the system SHALL confirm no unexpected files are present in each repository
4. WHEN running verification THEN the system SHALL confirm file checksums match the original monorepo
5. WHEN running verification THEN the system SHALL confirm Git history is preserved correctly

### Requirement 12: Rollback Strategy

**User Story:** As a repository maintainer, I want a rollback strategy, so that I can revert the split if issues are discovered.

#### Acceptance Criteria

1. WHEN planning the migration THEN the system SHALL document a rollback procedure
2. WHEN the migration is complete THEN the system SHALL maintain the original monorepo as a backup until verification is complete
3. WHEN issues are discovered THEN the system SHALL provide clear steps to restore the monorepo state
4. WHEN the split is verified THEN the system SHALL document the process for archiving the old monorepo

## Non-Functional Requirements

### Performance

1. The migration process SHALL complete within a reasonable timeframe (target: < 1 hour for full migration)
2. Git history preservation SHALL not significantly increase repository size beyond the relevant files

### Maintainability

1. Each repository SHALL be independently maintainable without requiring the other
2. Documentation SHALL be comprehensive enough for new contributors to understand the split

### Compatibility

1. Existing integrations with the TypeScript core SHALL continue to work after the split
2. Existing AI agent deployments SHALL be able to migrate to the new repository structure

## Success Criteria

The monorepo split is considered successful when:

1. Two independent repositories exist with complete, working codebases
2. All tests pass in both repositories
3. CI/CD pipelines run successfully in both repositories
4. Documentation is complete and accurate in both repositories
5. Git history is preserved appropriately in both repositories
6. No files are lost or corrupted during the migration
7. Developers can clone and work with either repository independently

## Out of Scope

The following are explicitly out of scope for this feature:

1. Modifying code functionality during the split
2. Refactoring code structure beyond the repository separation
3. Updating dependencies or package versions
4. Implementing new features in either repository
5. Changing build systems or tooling configurations (beyond what's necessary for the split)
