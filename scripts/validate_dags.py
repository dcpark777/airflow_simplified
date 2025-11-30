#!/usr/bin/env python3
"""
DAG Validation Script

Validates DAG files for syntax errors and import issues.
Can be used as a pre-commit hook or standalone script.

Usage:
    python scripts/validate_dags.py
    python scripts/validate_dags.py dags/my_team/my_dag.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'plugins'))

# Set Airflow environment
os.environ.setdefault('AIRFLOW_HOME', str(project_root))
os.environ.setdefault('AIRFLOW__CORE__EXECUTOR', 'SequentialExecutor')
os.environ.setdefault('AIRFLOW__DATABASE__SQL_ALCHEMY_CONN', 'sqlite:////tmp/validate_airflow.db')
os.environ.setdefault('AIRFLOW__CORE__LOAD_EXAMPLES', 'false')

from airflow.models import DagBag


from typing import Tuple, List

def validate_dag_file(dag_file: Path) -> Tuple[bool, List[str]]:
    """Validate a single DAG file."""
    errors = []
    
    if not dag_file.exists():
        return False, [f"DAG file not found: {dag_file}"]
    
    # Load DAG
    dag_bag = DagBag(
        dag_folder=str(dag_file.parent),
        include_examples=False,
    )
    
    # Check for import errors
    if dag_bag.import_errors:
        for file_path, error in dag_bag.import_errors.items():
            if str(dag_file) in file_path or dag_file.name in file_path:
                errors.append(f"Import error in {dag_file.name}: {error}")
    
    # Check if DAG was loaded
    dag_id = None
    for loaded_dag_id, dag in dag_bag.dags.items():
        if hasattr(dag, 'fileloc') and str(dag_file) in dag.fileloc:
            dag_id = loaded_dag_id
            break
    
    if not dag_id and not errors:
        errors.append(f"DAG not found in {dag_file.name} - check for DAG definition")
    
    return len(errors) == 0, errors


def validate_all_dags(dags_dir: Path = None) -> Tuple[bool, dict]:
    """Validate all DAGs in the dags directory."""
    if dags_dir is None:
        dags_dir = project_root / 'dags'
    
    all_errors = {}
    
    # Find all Python files in dags directory
    dag_files = list(dags_dir.rglob('*.py'))
    
    # Filter out __init__.py and files in examples if .airflowignore excludes them
    dag_files = [
        f for f in dag_files
        if f.name != '__init__.py'
        and not f.name.startswith('test_')
    ]
    
    for dag_file in dag_files:
        is_valid, errors = validate_dag_file(dag_file)
        if not is_valid:
            all_errors[str(dag_file.relative_to(project_root))] = errors
    
    return len(all_errors) == 0, all_errors


def main():
    """Main validation function."""
    if len(sys.argv) > 1:
        # Validate specific files (from pre-commit hook)
        files_to_check = [Path(f) for f in sys.argv[1:]]
        all_valid = True
        all_errors = {}
        
        for dag_file in files_to_check:
            # Convert to absolute path if needed
            if not dag_file.is_absolute():
                dag_file = project_root / dag_file
            
            is_valid, errors = validate_dag_file(dag_file)
            if not is_valid:
                all_valid = False
                all_errors[str(dag_file.relative_to(project_root))] = errors
        
        if not all_valid:
            print("❌ DAG validation failed:")
            for file_path, errors in all_errors.items():
                print(f"\n  {file_path}:")
                for error in errors:
                    print(f"    - {error}")
            return 1
        
        print("✅ All DAGs are valid")
        return 0
    else:
        # Validate all DAGs
        is_valid, all_errors = validate_all_dags()
        
        if not is_valid:
            print("❌ DAG validation failed:")
            for file_path, errors in all_errors.items():
                print(f"\n  {file_path}:")
                for error in errors:
                    print(f"    - {error}")
            return 1
        
        print("✅ All DAGs are valid")
        return 0


if __name__ == '__main__':
    exit(main())

