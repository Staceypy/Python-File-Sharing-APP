import argparse
import multiprocessing as mp
from pathlib import Path
from typing import List

from .config import PORT
from .file_operations.scanner import file_scanner
from .network.listener import tcp_listener
from .network.downloader import file_downloader
from .utils.file_utils import get_initial_file_dict

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="File synchronization system")
    parser.add_argument('--ip', 
                       required=True,
                       help='The ip addresses of vmb and vmc (comma-separated)')
    return parser.parse_args()

def main():
    args = parse_args()
    peers_ip = args.ip.split(',')
    
    # Initialize shared file dictionary
    g_file_dict = mp.Manager().dict(get_initial_file_dict())
    print(f'Initial file dictionary: {g_file_dict}')
    
    # Start TCP listener process
    listener = mp.Process(target=tcp_listener, args=(PORT, g_file_dict))
    listener.daemon = True
    listener.start()
    print('Listener started')
    
    # Start file scanner process
    scanner = mp.Process(target=file_scanner, args=(Path(dir_path), g_file_dict, peers_ip))
    scanner.daemon = True
    scanner.start()
    print('Scanner started')
    
    # Start file downloader process
    downloader = mp.Process(target=file_downloader, args=(g_file_dict,))
    downloader.daemon = True
    downloader.start()
    print('Downloader started')
    
    # Join processes
    try:
        listener.join()
        scanner.join()
        downloader.join()
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    main() 