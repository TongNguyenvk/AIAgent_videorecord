# Implementation Plan: Monorepo Split - Option 2

## Overview

This plan implements the separation of the Webreel monorepo into two independent repositories: `webreel` (TypeScript core library) and `webreel-ai-agent` (Python AI agent). The implementation follows a phased approach with preparation, execution, verification, and documentation stages. Git history will be preserved using `git filter-repo`, and all files will be verified for integrity using SHA-256 checksums.

## Tasks

### Phase 1: Preparation

- [-] 1. Install migration tools and create backup
  - Install `git-filter-repo` using pip
  - Create full backup of current monorepo to `webreel-backup/`
  - Verify backup integrity by checking `.git` directory exists
  - _Requirements: Migration tooling setup_

- [ ] 2. Create file classification configuration
  - Create `migration_config.py` with path definitions for TypeScript and Python repositories
  - Define `TYPESCRIPT_PATHS` list (packages/, apps/docs/, examples/, config files)
  - Define `PYTHON_PATHS` list (webreel-ai-agent/)
  - Define `EXCLUDE_PATHS` list (node_modules/, .venv/, output/, etc.)
  - _Requirements: File classification for repository separation_

- [ ] 3. Implement file classifier component
  - Create `FileClassifier` class with classification logic
  - Implement `classify_file()` method using path pattern matching
  - Implement `get_typescript_files()`, `get_python_files()`, `get_shared_files()` methods
  - _Requirements: Automated file categorization_

- [ ]* 3.1 Write property test for file classifier
  - **Property 2: TypeScript Repository File Type Purity**
  - **Property 3: Python Repository File Type Purity**
  - **Validates: Requirements for clean technology stack separation**
  - Generate random file paths and verify classification rules
  - Test that TypeScript files don't match Python patterns and vice versa

### Phase 2: Execution

- [ ] 4. Create TypeScript repository with filtered history
  - [ ] 4.1 Clone monorepo to `webreel-typescript/`
    - Use `git clone` to create working copy
    - _Requirements: Repository creation_
  
  - [ ] 4.2 Run git filter-repo for TypeScript paths
    - Execute `git filter-repo` with all TypeScript paths from config
    - Use `--force` flag to allow filtering
    - Preserve commit history for TypeScript-related files
    - _Requirements: Git history preservation_
  
  - [ ] 4.3 Update TypeScript repository configuration
    - Update README.md with reference to Python repository
    - Clean .gitignore to remove Python-specific patterns
    - Verify package.json workspace configuration is correct
    - _Requirements: Repository configuration_

- [ ] 5. Create Python repository with filtered history
  - [ ] 5.1 Clone monorepo to `webreel-python/`
    - Use `git clone` to create working copy
    - _Requirements: Repository creation_
  
  - [ ] 5.2 Run git filter-repo for Python paths
    - Execute `git filter-repo --path webreel-ai-agent/`
    - Use `--path-rename webreel-ai-agent/:''` to move to root
    - Use `--force` flag to allow filtering
    - Preserve commit history for Python-related files
    - _Requirements: Git history preservation, directory restructuring_
  
  - [ ] 5.3 Update Python repository configuration
    - Update README.md with reference to TypeScript repository
    - Clean .gitignore to remove TypeScript-specific patterns
    - Verify requirements.txt and pyproject.toml are correct
    - Update Dockerfile paths if needed
    - _Requirements: Repository configuration_

- [ ] 6. Create CI/CD workflows for both repositories
  - [ ] 6.1 Create TypeScript CI/CD workflows
    - Create `.github/workflows/ci.yml` for build, test, lint, type-check
    - Create `.github/workflows/release.yml` for changesets-based releases
    - Create `.github/workflows/docs.yml` for documentation deployment
    - _Requirements: TypeScript CI/CD automation_
  
  - [ ]* 6.2 Validate TypeScript workflow syntax
    - Use YAML linter to verify workflow syntax
    - Test workflow locally if possible
  
  - [ ] 6.3 Create Python CI/CD workflows
    - Create `.github/workflows/ci.yml` for pytest, mypy, linting
    - Create `.github/workflows/docker.yml` for Docker image builds
    - _Requirements: Python CI/CD automation_
  
  - [ ]* 6.4 Validate Python workflow syntax
    - Use YAML linter to verify workflow syntax
    - Test workflow locally if possible

### Phase 3: Verification

- [ ] 7. Implement file integrity verification
  - Create `FileIntegrityVerifier` class
  - Implement `compute_checksum()` method using SHA-256
  - Implement `verify_file_integrity()` method to compare source and target
  - Implement `generate_integrity_report()` method
  - _Requirements: File integrity validation_

- [ ]* 7.1 Write property test for file integrity
  - **Property 1: File Integrity Preservation**
  - **Validates: Requirements for no file corruption during migration**
  - Generate random sample of migrated files
  - Compute and compare checksums between source and target
  - Assert all checksums match exactly

- [ ] 8. Implement Git history verification
  - Create `GitHistoryFilter` class
  - Implement `verify_history_preservation()` method
  - Compare commit counts and metadata between source and target
  - Generate history report with missing commits
  - _Requirements: Git history completeness_

- [ ]* 8.1 Write property test for Git history
  - **Property 5: Git History Completeness**
  - **Validates: Requirements for complete history preservation**
  - Generate random sample of files from target repositories
  - Extract commit history from source and target
  - Assert all source commits exist in target with matching metadata

- [ ] 9. Implement repository structure verification
  - Create `RepositoryStructureBuilder` class
  - Define `TYPESCRIPT_STRUCTURE` and `PYTHON_STRUCTURE` models
  - Implement `validate_structure()` method
  - Check for required files, directories, and forbidden patterns
  - _Requirements: Repository structure validation_

- [ ]* 9.1 Write property test for directory structure
  - **Property 4: Directory Structure Preservation**
  - **Validates: Requirements for maintaining relative paths**
  - Generate random sample of migrated files
  - Verify relative path structure is preserved
  - Assert directory organization matches source

- [ ]* 9.2 Write property test for repository self-containment
  - **Property 6: Repository Self-Containment**
  - **Validates: Requirements for independent functionality**
  - Parse configuration files and import statements
  - Generate list of all file references
  - Assert all references exist in repository or are external dependencies

- [ ] 10. Run complete verification script
  - Execute verification script on both repositories
  - Generate integrity reports for all files
  - Generate history reports for sample files
  - Generate structure validation reports
  - _Requirements: Comprehensive verification_

- [ ] 11. Checkpoint - Review verification results
  - Review all verification reports for failures
  - If any failures exist, investigate and fix before proceeding
  - Ensure all tests pass, ask the user if questions arise

- [ ] 12. Test builds in both repositories
  - [ ] 12.1 Test TypeScript repository build
    - Run `pnpm install` in TypeScript repository
    - Run `pnpm build` and verify success
    - Run `pnpm test` and verify all tests pass
    - Run `pnpm type-check` and verify no type errors
    - _Requirements: TypeScript build validation_
  
  - [ ] 12.2 Test Python repository build
    - Create virtual environment in Python repository
    - Run `pip install -r requirements.txt`
    - Run `pytest` and verify all tests pass
    - Run `mypy .` and verify type checking passes
    - Build Docker image and verify it runs
    - _Requirements: Python build validation_

- [ ] 13. Verify CI/CD pipelines
  - Push both repositories to GitHub (test branches)
  - Monitor CI workflow runs
  - Verify all jobs complete successfully
  - Check build artifacts are created correctly
  - _Requirements: CI/CD validation_

### Phase 4: Documentation and Finalization

- [ ] 14. Update repository documentation
  - [ ] 14.1 Update TypeScript repository README
    - Add "Related Projects" section linking to Python repository
    - Add installation instructions for npm package
    - Add integration guide for AI agent
    - _Requirements: Cross-repository documentation_
  
  - [ ] 14.2 Update Python repository README
    - Add "Related Projects" section linking to TypeScript repository
    - Add prerequisites including Node.js for @webreel/core
    - Add installation instructions including npm install
    - Add integration guide for core library
    - _Requirements: Cross-repository documentation_
  
  - [ ] 14.3 Create migration documentation
    - Create `MIGRATION.md` in both repositories
    - Document migration date, method, and verification
    - Add instructions for viewing complete history
    - Add links to related repositories
    - _Requirements: Migration documentation_

- [ ] 15. Archive original monorepo
  - Create archive notice branch in original monorepo
  - Update README.md with archive notice and links to new repositories
  - Commit and push archive notice
  - Archive repository on GitHub via settings
  - _Requirements: Monorepo archival_

- [ ] 16. Final checkpoint - Verify complete migration
  - Confirm both repositories are accessible on GitHub
  - Confirm all verification scripts pass
  - Confirm builds succeed in both repositories
  - Confirm CI/CD pipelines run successfully
  - Confirm documentation is complete and accurate
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional property-based tests that can be skipped for faster completion
- Each verification task includes specific property tests that validate correctness properties from the design
- Checkpoints ensure incremental validation before proceeding to next phase
- The migration preserves Git history using `git filter-repo` for both repositories
- All files are verified using SHA-256 checksums to ensure integrity
- Both repositories will be independently functional after the split
- Original monorepo will be archived with clear notices pointing to new repositories
