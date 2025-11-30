#!/usr/bin/env python3
"""
DAG Resource Limits Checker

Validates that DAGs have proper resource limits configured to prevent resource exhaustion.

Usage:
    python scripts/check_dag_resources.py
    python scripts/check_dag_resources.py dags/my_team/my_dag.py
"""

import sys
import os
import ast
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'plugins'))

# Set Airflow environment
os.environ.setdefault('AIRFLOW_HOME', str(project_root))
os.environ.setdefault('AIRFLOW__CORE__EXECUTOR', 'SequentialExecutor')
os.environ.setdefault('AIRFLOW__DATABASE__SQL_ALCHEMY_CONN', 'sqlite:////tmp/check_resources_airflow.db')
os.environ.setdefault('AIRFLOW__CORE__LOAD_EXAMPLES', 'false')

from airflow.models import DagBag


# Default resource limits (recommended values)
DEFAULT_MAX_ACTIVE_RUNS = 1
DEFAULT_MAX_ACTIVE_TASKS = 3
MAX_ALLOWED_ACTIVE_RUNS = 5  # Hard limit
MAX_ALLOWED_ACTIVE_TASKS = 10  # Hard limit


def extract_dag_config_from_file(dag_file: Path) -> dict:
    """Extract DAG configuration from a Python file by parsing the AST."""
    config = {
        'max_active_runs': None,
        'max_active_tasks': None,
        'dag_id': None,
    }
    
    try:
        with open(dag_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            # Look for DAG() constructor calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'DAG':
                    # Extract arguments
                    for keyword in node.keywords:
                        if keyword.arg == 'dag_id':
                            if isinstance(keyword.value, ast.Constant):
                                config['dag_id'] = keyword.value.value
                            elif isinstance(keyword.value, ast.Str):
                                config['dag_id'] = keyword.value.s
                        elif keyword.arg == 'max_active_runs':
                            if isinstance(keyword.value, ast.Constant):
                                config['max_active_runs'] = keyword.value.value
                            elif isinstance(keyword.value, ast.Num):  # Python < 3.8
                                config['max_active_runs'] = keyword.value.n
                        elif keyword.arg == 'max_active_tasks':
                            if isinstance(keyword.value, ast.Constant):
                                config['max_active_tasks'] = keyword.value.value
                            elif isinstance(keyword.value, ast.Num):
                                config['max_active_tasks'] = keyword.value.n
    except Exception:
        pass
    
    return config


from typing import Tuple, List

def check_dag_resources(dag_file: Path) -> Tuple[bool, List[str], List[str]]:
    """Check resource limits for a single DAG file."""
    errors = []
    warnings = []
    
    # Try to extract config from file
    config = extract_dag_config_from_file(dag_file)
    
    # Also try loading via DagBag
    try:
        dag_bag = DagBag(
            dag_folder=str(dag_file.parent),
            include_examples=False,
        )
        
        for dag_id, dag in dag_bag.dags.items():
            if hasattr(dag, 'fileloc') and str(dag_file) in dag.fileloc:
                if not config['dag_id']:
                    config['dag_id'] = dag_id
                if config['max_active_runs'] is None:
                    config['max_active_runs'] = getattr(dag, 'max_active_runs', None)
                if config['max_active_tasks'] is None:
                    config['max_active_tasks'] = getattr(dag, 'max_active_tasks', None)
    except Exception:
        pass
    
    dag_id = config['dag_id'] or dag_file.stem
    
    # Check max_active_runs
    if config['max_active_runs'] is None:
        warnings.append(f"{dag_id}: max_active_runs not set (recommended: {DEFAULT_MAX_ACTIVE_RUNS})")
    elif config['max_active_runs'] > MAX_ALLOWED_ACTIVE_RUNS:
        errors.append(
            f"{dag_id}: max_active_runs={config['max_active_runs']} exceeds maximum allowed ({MAX_ALLOWED_ACTIVE_RUNS})"
        )
    elif config['max_active_runs'] > DEFAULT_MAX_ACTIVE_RUNS:
        warnings.append(
            f"{dag_id}: max_active_runs={config['max_active_runs']} is higher than recommended ({DEFAULT_MAX_ACTIVE_RUNS})"
        )
    
    # Check max_active_tasks
    if config['max_active_tasks'] is None:
        warnings.append(f"{dag_id}: max_active_tasks not set (recommended: {DEFAULT_MAX_ACTIVE_TASKS})")
    elif config['max_active_tasks'] > MAX_ALLOWED_ACTIVE_TASKS:
        errors.append(
            f"{dag_id}: max_active_tasks={config['max_active_tasks']} exceeds maximum allowed ({MAX_ALLOWED_ACTIVE_TASKS})"
        )
    elif config['max_active_tasks'] > DEFAULT_MAX_ACTIVE_TASKS:
        warnings.append(
            f"{dag_id}: max_active_tasks={config['max_active_tasks']} is higher than recommended ({DEFAULT_MAX_ACTIVE_TASKS})"
        )
    
    return len(errors) == 0, errors, warnings


def check_all_dags(dags_dir: Path = None) -> Tuple[bool, dict, dict]:
    """Check resource limits for all DAGs."""
    if dags_dir is None:
        dags_dir = project_root / 'dags'
    
    all_errors = {}
    all_warnings = {}
    
    # Find all Python files
    dag_files = list(dags_dir.rglob('*.py'))
    dag_files = [
        f for f in dag_files
        if f.name != '__init__.py'
        and not f.name.startswith('test_')
    ]
    
    for dag_file in dag_files:
        is_valid, errors, warnings = check_dag_resources(dag_file)
        if errors:
            all_errors[str(dag_file.relative_to(project_root))] = errors
        if warnings:
            all_warnings[str(dag_file.relative_to(project_root))] = warnings
    
    return len(all_errors) == 0, all_errors, all_warnings


def main():
    """Main function."""
    if len(sys.argv) > 1:
        # Check specific files
        files_to_check = [Path(f) for f in sys.argv[1:]]
        all_valid = True
        all_errors = {}
        all_warnings = {}
        
        for dag_file in files_to_check:
            if not dag_file.is_absolute():
                dag_file = project_root / dag_file
            
            is_valid, errors, warnings = check_dag_resources(dag_file)
            if not is_valid:
                all_valid = False
            if errors:
                rel_path = str(dag_file.relative_to(project_root))
                all_errors[rel_path] = errors
            if warnings:
                rel_path = str(dag_file.relative_to(project_root))
                all_warnings[rel_path] = warnings
        
        if all_warnings:
            print("⚠️  Resource limit warnings:")
            for file_path, warnings in all_warnings.items():
                print(f"\n  {file_path}:")
                for warning in warnings:
                    print(f"    - {warning}")
        
        if not all_valid:
            print("\n❌ Resource limit violations:")
            for file_path, errors in all_errors.items():
                print(f"\n  {file_path}:")
                for error in errors:
                    print(f"    - {error}")
            print(f"\nRecommended limits:")
            print(f"  - max_active_runs: {DEFAULT_MAX_ACTIVE_RUNS} (max: {MAX_ALLOWED_ACTIVE_RUNS})")
            print(f"  - max_active_tasks: {DEFAULT_MAX_ACTIVE_TASKS} (max: {MAX_ALLOWED_ACTIVE_TASKS})")
            return 1
        
        if all_warnings:
            print("✅ All DAGs have resource limits (with warnings)")
        else:
            print("✅ All DAGs have proper resource limits")
        return 0
    else:
        # Check all DAGs
        is_valid, all_errors, all_warnings = check_all_dags()
        
        if all_warnings:
            print("⚠️  Resource limit warnings:")
            for file_path, warnings in all_warnings.items():
                print(f"\n  {file_path}:")
                for warning in warnings:
                    print(f"    - {warning}")
        
        if not is_valid:
            print("\n❌ Resource limit violations:")
            for file_path, errors in all_errors.items():
                print(f"\n  {file_path}:")
                for error in errors:
                    print(f"    - {error}")
            print(f"\nRecommended limits:")
            print(f"  - max_active_runs: {DEFAULT_MAX_ACTIVE_RUNS} (max: {MAX_ALLOWED_ACTIVE_RUNS})")
            print(f"  - max_active_tasks: {DEFAULT_MAX_ACTIVE_TASKS} (max: {MAX_ALLOWED_ACTIVE_TASKS})")
            return 1
        
        if all_warnings:
            print("✅ All DAGs have resource limits (with warnings)")
        else:
            print("✅ All DAGs have proper resource limits")
        return 0


if __name__ == '__main__':
    exit(main())

