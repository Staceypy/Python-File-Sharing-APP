import os
from pathlib import Path

# Network Configuration
PORT = 20000
BUFFER_SIZE = 20 * 1024 * 1024  # 20MB
BLOCK_SIZE = 1024 * 1024 * 10   # 10MB
COMPRESSION_SIZE = 700_000_000  # 700MB

# State Constants
STATE_READY = 1
STATE_NOT_READY = 0
NO_FILE = 4001
SOCKET_CLOSE = 4000

# Paths
BASE_DIR = Path('/home/tc/workplace/cw1')
SHARE_DIR = BASE_DIR / 'share'
LOG_DIR = BASE_DIR / 'log'

# Create directories if they don't exist
SHARE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True) 