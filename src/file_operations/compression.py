import zipfile
from pathlib import Path
from ..config import SHARE_DIR

def zip_file(file_name: str) -> str:
    """Compress a file using ZIP format."""
    file_base = Path(file_name).stem
    zip_name = f"{file_base}.zip"
    
    with zipfile.ZipFile(SHARE_DIR / zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(SHARE_DIR / file_name, arcname=file_name)
    
    return zip_name

def unzip_file(zip_file: str) -> None:
    """Extract contents of a ZIP file."""
    with zipfile.ZipFile(SHARE_DIR / zip_file, 'r') as f:
        f.extractall(SHARE_DIR) 