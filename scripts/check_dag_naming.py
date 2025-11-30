#!/usr/bin/env python3
"""
DAG Naming Convention Checker

Validates that DAGs follow the tenant naming convention: {tenant}_{dag_name}

Usage:
    python scripts/check_dag_naming.py
    python scripts/check_dag_naming.py dags/my_team/my_dag.py
"""

import sys
import os
import re
import ast
from pathlib import Path
from typing import Tuple, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'plugins'))

# Set Airflow environment
os.environ.setdefault('AIRFLOW_HOME', str(project_root))
os.environ.setdefault('AIRFLOW__CORE__EXECUTOR', 'SequentialExecutor')
os.environ.setdefault('AIRFLOW__DATABASE__SQL_ALCHEMY_CONN', 'sqlite:////tmp/check_naming_airflow.db')
os.environ.setdefault('AIRFLOW__CORE__LOAD_EXAMPLES', 'false')

from airflow.models import DagBag


# Known valid tenants (can be extended)
KNOWN_TENANTS = {
    'data-engineering',
    'analytics',
    'ml-team',
    'data-science',
    'platform',
    'devops',
}


def extract_dag_id_from_file(dag_file: Path) -> list[str]:
    """Extract DAG IDs from a Python file by parsing the AST."""
    dag_ids = []
    
    try:
        with open(dag_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            # Look for DAG() constructor calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'DAG':
                    # Look for dag_id argument
                    for keyword in node.keywords:
                        if keyword.arg == 'dag_id':
                            if isinstance(keyword.value, ast.Constant):
                                dag_ids.append(keyword.value.value)
                            elif isinstance(keyword.value, ast.Str):  # Python < 3.8
                                dag_ids.append(keyword.value.s)
    except Exception as e:
        # If AST parsing fails, we'll check via DagBag
        pass
    
    return dag_ids


def check_naming_convention(dag_id: str) -> Tuple[bool, str]:
    """Check if DAG ID follows naming convention: {tenant}_{name}."""
    if not dag_id:
        return False, "DAG ID is empty"
    
    # Check format: should have at least one underscore
    if '_' not in dag_id:
        return False, f"DAG ID '{dag_id}' must follow format: {{tenant}}_{{name}}"
    
    parts = dag_id.split('_', 1)
    if len(parts) != 2:
        return False, f"DAG ID '{dag_id}' must follow format: {{tenant}}_{{name}}"
    
    tenant, name = parts
    
    # Check tenant is not empty
    if not tenant:
        return False, f"DAG ID '{dag_id}' has empty tenant prefix"
    
    # Check name is not empty
    if not name:
        return False, f"DAG ID '{dag_id}' has empty name after tenant prefix"
    
    # Check tenant format (should be lowercase, alphanumeric with hyphens)
    if not re.match(r'^[a-z0-9-]+$', tenant):
        return False, f"DAG ID '{dag_id}' has invalid tenant format (use lowercase, alphanumeric, hyphens)"
    
    # Check name format (should be lowercase, alphanumeric with underscores)
    if not re.match(r'^[a-z0-9_]+$', name):
        return False, f"DAG ID '{dag_id}' has invalid name format (use lowercase, alphanumeric, underscores)"
    
    # Warning if tenant not in known list (not a failure)
    if tenant not in KNOWN_TENANTS:
        return True, f"Warning: Unknown tenant '{tenant}' (DAG ID is valid but tenant not in known list)"
    
    return True, "Valid"


def check_dag_file(dag_file: Path) -> tuple[bool, list[str]]:
    """Check naming conventions for a single DAG file."""
    errors = []
    warnings = []
    
    # Try to extract DAG IDs from file
    dag_ids = extract_dag_id_from_file(dag_file)
    
    # Also try loading via DagBag
    try:
        dag_bag = DagBag(
            dag_folder=str(dag_file.parent),
            include_examples=False,
        )
        
        for dag_id, dag in dag_bag.dags.items():
            if hasattr(dag, 'fileloc') and str(dag_file) in dag.fileloc:
                if dag_id not in dag_ids:
                    dag_ids.append(dag_id)
    except Exception:
        pass
    
    # Check each DAG ID
    for dag_id in dag_ids:
        is_valid, message = check_naming_convention(dag_id)
        if not is_valid:
            errors.append(f"{dag_id}: {message}")
        elif "Warning" in message:
            warnings.append(f"{dag_id}: {message}")
    
    # If no DAG IDs found, that's also an error
    if not dag_ids:
        errors.append("No DAG ID found in file")
    
    return len(errors) == 0, errors, warnings


def check_all_dags(dags_dir: Path = None) -> Tuple[bool, dict, dict]:
    """Check naming conventions for all DAGs."""
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
        is_valid, errors, warnings = check_dag_file(dag_file)
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
            
            is_valid, errors, warnings = check_dag_file(dag_file)
            if not is_valid:
                all_valid = False
            if errors:
                rel_path = str(dag_file.relative_to(project_root))
                all_errors[rel_path] = errors
            if warnings:
                rel_path = str(dag_file.relative_to(project_root))
                all_warnings[rel_path] = warnings
        
        if all_warnings:
            print("⚠️  Warnings:")
            for file_path, warnings in all_warnings.items():
                print(f"\n  {file_path}:")
                for warning in warnings:
                    print(f"    - {warning}")
        
        if not all_valid:
            print("\n❌ DAG naming convention violations:")
            for file_path, errors in all_errors.items():
                print(f"\n  {file_path}:")
                for error in errors:
                    print(f"    - {error}")
            print("\nDAG IDs must follow format: {tenant}_{name}")
            print("Example: data-engineering_daily_etl")
            return 1
        
        if all_warnings:
            print("✅ All DAGs follow naming convention (with warnings)")
        else:
            print("✅ All DAGs follow naming convention")
        return 0
    else:
        # Check all DAGs
        is_valid, all_errors, all_warnings = check_all_dags()
        
        if all_warnings:
            print("⚠️  Warnings:")
            for file_path, warnings in all_warnings.items():
                print(f"\n  {file_path}:")
                for warning in warnings:
                    print(f"    - {warning}")
        
        if not is_valid:
            print("\n❌ DAG naming convention violations:")
            for file_path, errors in all_errors.items():
                print(f"\n  {file_path}:")
                for error in errors:
                    print(f"    - {error}")
            print("\nDAG IDs must follow format: {tenant}_{name}")
            print("Example: data-engineering_daily_etl")
            return 1
        
        if all_warnings:
            print("✅ All DAGs follow naming convention (with warnings)")
        else:
            print("✅ All DAGs follow naming convention")
        return 0


if __name__ == '__main__':
    exit(main())

