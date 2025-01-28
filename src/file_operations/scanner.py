import time
from pathlib import Path
from typing import Dict, List
from ..config import SHARE_DIR
from ..network.protocol import make_package

def traverse(path: Path) -> List[str]:
    """Recursively traverse directory and return list of files."""
    file_list = []
    for item in path.iterdir():
        if item.is_file() and not item.name.endswith('.lefting'):
            file_list.append(str(item.relative_to(path)))
        elif item.is_dir():
            folder_name = item.name
            file_list.append(folder_name)
            sub_files = traverse(item)
            file_list.extend(f"{folder_name}/{file}" for file in sub_files)
    return file_list

def file_scanner(folder: Path, g_file_dict: Dict, peers: List[str]) -> None:
    """Monitor directory for new and modified files."""
    while True:
        new = {}
        modified = {}
        time.sleep(1)
        
        file_list = traverse(folder)
        if not file_list:
            continue
            
        for file in file_list:
            file_path = folder / file
            if not file_path.is_file() or file.endswith('.lefting'):
                continue
                
            mtime = file_path.stat().st_mtime
            size = file_path.stat().st_size
            
            if file not in g_file_dict:
                if file.endswith('.zip'):
                    g_file_dict[file] = [mtime, size]
                else:
                    new[file] = [mtime, size]
                    g_file_dict[file] = [mtime, size]
            elif mtime != g_file_dict[file][0]:
                modified[file] = [mtime, size]
                g_file_dict[file] = [mtime, size]

        # Handle modified files
        if modified:
            msg = make_package("modified", modified)
            broadcast_changes(peers, msg)

        # Handle new files
        if new:
            msg = make_package("new", new)
            broadcast_changes(peers, msg) 