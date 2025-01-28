import json
import struct
from typing import Tuple, Any, Dict

def make_package(header: str, data: Any = None) -> bytes:
    """Create a network package with header and data."""
    dumped_json_string = json.dumps(data) if data is not None else ""
    json_header = json.dumps(header)
    json_length = len(json_header.encode())
    binary_data = dumped_json_string.encode()
    bin_length = len(binary_data)
    
    return struct.pack('!II', json_length, bin_length) + json_header.encode() + binary_data

def get_tcp_package(connection_socket) -> Tuple[bytes, bytes]:
    """Receive and parse a TCP package."""
    header_b = connection_socket.recv(8)
    json_header_size = int.from_bytes(header_b[:4], byteorder='big', signed=False)
    data_header_size = int.from_bytes(header_b[4:], byteorder='big', signed=False)
    
    # Receive JSON header
    buf = b''
    while len(buf) < json_header_size:
        buf += connection_socket.recv(json_header_size)
    json_bin = buf[:json_header_size]
    buf = buf[json_header_size:]
    
    # Receive data
    while len(buf) < data_header_size:
        buf += connection_socket.recv(data_header_size)
    data_bin = buf
    
    return json_bin, data_bin 