#!/usr/bin/env python3
"""
Analyze Claude Code data directory structure.
Produces comprehensive statistics and structure information.
"""

import os
import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

def get_file_info(filepath: Path) -> Dict[str, Any]:
    """Get basic file info without reading content."""
    try:
        stat = filepath.stat()
        return {
            'size_bytes': stat.st_size,
            'extension': filepath.suffix,
            'name': filepath.name
        }
    except Exception as e:
        return {'error': str(e)}

def analyze_jsonl_structure(filepath: Path, max_lines: int = 5) -> Dict[str, Any]:
    """Analyze JSONL file structure by reading only first few lines."""
    result = {
        'total_lines': 0,
        'sample_keys': set(),
        'types_seen': set(),
        'sample_objects': []
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f):
                result['total_lines'] += 1
                if i < max_lines:
                    try:
                        obj = json.loads(line.strip())
                        if isinstance(obj, dict):
                            result['sample_keys'].update(obj.keys())
                            if 'type' in obj:
                                result['types_seen'].add(obj['type'])
                            if i < 2:
                                # Only store minimal sample
                                sample = {k: type(v).__name__ for k, v in obj.items()}
                                result['sample_objects'].append(sample)
                    except json.JSONDecodeError:
                        pass
        
        result['sample_keys'] = list(result['sample_keys'])
        result['types_seen'] = list(result['types_seen'])
    except Exception as e:
        result['error'] = str(e)
    
    return result

def analyze_json_structure(filepath: Path) -> Dict[str, Any]:
    """Analyze JSON file structure."""
    result = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if len(content) > 50000:  # Don't parse huge files
                result['warning'] = 'File too large, skipping full parse'
                result['size'] = len(content)
            else:
                data = json.loads(content)
                if isinstance(data, list):
                    result['type'] = 'array'
                    result['length'] = len(data)
                    if data and isinstance(data[0], dict):
                        result['item_keys'] = list(data[0].keys())
                elif isinstance(data, dict):
                    result['type'] = 'object'
                    result['keys'] = list(data.keys())
    except Exception as e:
        result['error'] = str(e)
    return result

def analyze_directory(base_path: Path) -> Dict[str, Any]:
    """Analyze the complete Claude Code directory structure."""
    
    structure = {
        'root_contents': [],
        'projects': {},
        'plans': {},
        'todos': {},
        'file_history': {},
        'other_folders': {},
        'root_files': {},
        'statistics': defaultdict(int)
    }
    
    # Analyze root level
    for item in base_path.iterdir():
        if item.name.startswith('.'):
            continue
            
        if item.is_file():
            info = get_file_info(item)
            structure['root_contents'].append({'type': 'file', 'name': item.name, **info})
            structure['statistics']['root_files'] += 1
            
            if item.suffix == '.jsonl':
                structure['root_files'][item.name] = analyze_jsonl_structure(item)
            elif item.suffix == '.json':
                structure['root_files'][item.name] = analyze_json_structure(item)
                
        elif item.is_dir():
            structure['root_contents'].append({'type': 'dir', 'name': item.name})
            
            if item.name == 'projects':
                structure['projects'] = analyze_projects_folder(item)
            elif item.name == 'plans':
                structure['plans'] = analyze_plans_folder(item)
            elif item.name == 'todos':
                structure['todos'] = analyze_todos_folder(item)
            elif item.name == 'file-history':
                structure['file_history'] = analyze_file_history_folder(item)
            else:
                # Other folders - just count contents
                try:
                    contents = list(item.iterdir())
                    structure['other_folders'][item.name] = {
                        'item_count': len(contents),
                        'sample_items': [c.name for c in contents[:5]]
                    }
                except Exception as e:
                    structure['other_folders'][item.name] = {'error': str(e)}
    
    return structure

def analyze_projects_folder(projects_path: Path) -> Dict[str, Any]:
    """Analyze the projects folder structure."""
    result = {
        'project_count': 0,
        'projects': [],
        'file_patterns': defaultdict(int),
        'sample_project': None
    }
    
    for project_dir in projects_path.iterdir():
        if not project_dir.is_dir():
            continue
        
        result['project_count'] += 1
        
        project_info = {
            'name': project_dir.name,
            'files': []
        }
        
        for f in project_dir.iterdir():
            if f.is_file():
                info = get_file_info(f)
                project_info['files'].append(info)
                
                # Categorize by pattern
                if f.name.startswith('agent-'):
                    result['file_patterns']['agent_files'] += 1
                elif f.suffix == '.jsonl':
                    result['file_patterns']['conversation_files'] += 1
        
        # Store sample project analysis
        if result['sample_project'] is None and project_info['files']:
            result['sample_project'] = project_info
            
            # Analyze one conversation file structure
            for f in project_dir.iterdir():
                if f.suffix == '.jsonl' and not f.name.startswith('agent-'):
                    result['sample_conversation_structure'] = analyze_jsonl_structure(f, max_lines=10)
                    break
        
        result['projects'].append({
            'name': project_dir.name,
            'file_count': len(project_info['files'])
        })
    
    return result

def analyze_plans_folder(plans_path: Path) -> Dict[str, Any]:
    """Analyze the plans folder."""
    result = {
        'plan_count': 0,
        'plans': [],
        'sample_plan': None
    }
    
    for f in plans_path.iterdir():
        if f.is_file() and f.suffix == '.md':
            result['plan_count'] += 1
            info = get_file_info(f)
            result['plans'].append(info)
            
            if result['sample_plan'] is None:
                try:
                    with open(f, 'r') as pf:
                        content = pf.read()
                        result['sample_plan'] = {
                            'name': f.name,
                            'size': len(content),
                            'first_500_chars': content[:500]
                        }
                except Exception as e:
                    result['sample_plan'] = {'error': str(e)}
    
    return result

def analyze_todos_folder(todos_path: Path) -> Dict[str, Any]:
    """Analyze the todos folder."""
    result = {
        'todo_count': 0,
        'naming_pattern': None,
        'sample_todo': None,
        'todos': []
    }
    
    for f in todos_path.iterdir():
        if f.is_file() and f.suffix == '.json':
            result['todo_count'] += 1
            info = get_file_info(f)
            result['todos'].append(info)
            
            # Analyze naming pattern
            if result['naming_pattern'] is None:
                parts = f.stem.split('-agent-')
                if len(parts) == 2:
                    result['naming_pattern'] = '<session_id>-agent-<agent_id>'
            
            if result['sample_todo'] is None:
                result['sample_todo'] = analyze_json_structure(f)
    
    return result

def analyze_file_history_folder(fh_path: Path) -> Dict[str, Any]:
    """Analyze file-history folder."""
    result = {
        'session_count': 0,
        'file_pattern': None,
        'sample_session': None
    }
    
    for session_dir in fh_path.iterdir():
        if session_dir.is_dir():
            result['session_count'] += 1
            
            if result['sample_session'] is None:
                files = list(session_dir.iterdir())
                result['sample_session'] = {
                    'name': session_dir.name,
                    'file_count': len(files),
                    'sample_files': [f.name for f in files[:5]]
                }
                
                # Analyze file naming pattern
                if files:
                    name = files[0].name
                    if '@v' in name:
                        result['file_pattern'] = '<hash>@v<version>'
    
    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: analyze_structure.py <claude_data_path>")
        print("Example: analyze_structure.py ./copilot_raw")
        sys.exit(1)
    
    data_path = Path(sys.argv[1])
    if not data_path.exists():
        print(f"Error: Path {data_path} does not exist")
        sys.exit(1)
    
    print(f"Analyzing Claude Code data directory: {data_path}")
    print("=" * 60)
    
    structure = analyze_directory(data_path)
    
    # Output results
    print(json.dumps(structure, indent=2, default=str))

if __name__ == '__main__':
    main()
