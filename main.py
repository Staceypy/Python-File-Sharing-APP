"""
Currently, BLOCK_SIZE is set to 10MB. If network is OK, download can succeed in one time.
If it fails, the downloading will start from where it is left.
BUT, it may not be that efficient...
So, if it got stuck a lot, please set BLOCK_SIZE to 5 MB manually.
Achieved Functions:
1. Compression of large file over 700MB
2. Resume from breakpoint
3. Update file partially
"""
import json
import math
import os
import zipfile
import time
import socket
import argparse
import struct
import hashlib
from zipfile import ZipFile
from os.path import join, isfile, isdir, exists
import threading
from multiprocessing import Process
import multiprocessing as mp

COMPRESSION_SIZE = 700000000  # 700MB
STATE_READY = 1
STATE_NOT_READY = 0
PORT = 20000
BUFFER_SIZE = 20 * 1024 * 1024
BLOCK_SIZE = 1024 * 1024 * 10
NO_FILE = 4001
SOCKET_CLOSE = 4000

dir_path = '/home/tc/workplace/cw1/share/'
log_path = '/home/tc/workplace/cw1/log'

if not exists(dir_path):
    os.mkdir(dir_path)
if not exists(log_path):
    os.mkdir(log_path)


def zip_file(file_name):
    file_news = file_name.split('.')[0] + '.zip'
    zipf = ZipFile(join(dir_path, file_news), "w", zipfile.ZIP_DEFLATED)
    zipf.write(os.path.join(dir_path, file_name), arcname=file_name)
    zipf.close()
    return file_news


def unzip_file(unzip_file):  # 'vam.zip'
    f = zipfile.ZipFile(join(dir_path, unzip_file), 'r')
    f.extractall(dir_path)


def getsize(filename):
    return os.path.getsize(join(dir_path, filename))


def getmtime(filename):
    return os.path.getmtime(join(dir_path, filename))


def get_md5(filename):
    f = open(join(dir_path, filename), 'rb')
    contents = f.read()
    f.close()
    return hashlib.md5(contents).hexdigest()


def sort_log(path):
    dir_list = os.listdir(path)
    dir_list = sorted(dir_list, key=lambda x: os.path.getmtime(os.path.join(path, x)))
    if len(dir_list) > 0:
        print(f'logs: {dir_list}')
    return dir_list


def traverse(path):
    file_list = []
    file_folder_list = os.listdir(path)
    for file_folder_name in file_folder_list:
        if isfile(join(path, file_folder_name)) & file_folder_name.endswith('.lefting') is False:
            file_list.append(file_folder_name)
        if isdir(join(path, file_folder_name)):
            file_list.append(file_folder_name)
            sub_folder = traverse(join(path, file_folder_name))
            for file in sub_folder:
                file_list.append(file_folder_name + '/' + file)
    return file_list


def file_scanner(folder, g_file_dict, peers):
    while True:
        new = {}
        modified = {}
        time.sleep(1)
        file_list = traverse(folder)
        if len(file_list) > 0:
            for file in file_list:
                if '.' in file and file.split('.')[-1] != 'lefting':  # Don't record folder and lefting files
                    if file not in g_file_dict.keys():
                        print('TRUE')
                        if file.split('.')[-1] == 'zip':
                            g_file_dict.update({file: [getmtime(file), getsize(file)]})
                        else:
                            new[file] = [getmtime(file), getsize(file)]
                            g_file_dict.update({file: [getmtime(file), getsize(file)]})
                    else:
                        if getmtime(file) != g_file_dict[file][0]:  # a modified file
                            modified[file] = [getmtime(file), getsize(file)]
                            g_file_dict.update({file: [getmtime(file), getsize(file)]})
                else:
                    continue

        if len(modified) > 0:
            print(f'modified:{modified}')
            msg = make_package("modified", modified)
            for peer in peers:
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    server_socket.connect((peer, PORT))
                    server_socket.send(msg)
                    server_socket.close()
                except:
                    time.sleep(0.1)
                    continue

        if len(new) > 0:
            print(f'new:{new}')
            msg = make_package("new", new)
            for peer in peers:
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    server_socket.connect((peer, PORT))
                    server_socket.send(msg)
                    server_socket.close()
                except:
                    time.sleep(0.1)
                    continue
        else:
            continue


def file_downloader(file_dict_local):
    while True:
        time.sleep(1)
        logs = sort_log(log_path)
        if len(logs) > 0:
            for log in logs:
                start_downloading_time = time.time()
                with open(join(log_path, log), 'r') as f:
                    dict = json.load(fp=f)
                    print(f'log reads:{dict}')
                    f.close()
                    print(dict["name"] not in file_dict_local.keys())
                if dict["name"].split('.')[-1] != 'modified':
                    if dict["name"] not in file_dict_local.keys():
                        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        connection_socket.connect((dict["peer"], PORT))
                        print(connection_socket)
                        index = dict["index"]
                        total_block_number = math.ceil(dict["size"] / BLOCK_SIZE)
                        print(f'total block number: {total_block_number}.')
                        tem_file_name = dict["name"] + '.lefting'
                        if '/' in tem_file_name:  # For file in a folder: 'vmb_folder/dog.png.lefting'
                            folder_path = join(dir_path, tem_file_name.split('/')[0])
                            if not exists(folder_path):
                                os.mkdir(folder_path)
                            tem_file_name = tem_file_name.split('/')[1]  # 'dog.png.lefting'
                            file_path = join(folder_path, tem_file_name)
                        else:
                            file_path = join(dir_path, tem_file_name)
                        if not exists(file_path):  # create file and write in block 0
                            connection_socket.send(get_file_order(dict))
                            print('I send sth. I got', end='')
                            received_index_b, block = get_tcp_package(connection_socket)
                            received_index = int.from_bytes(received_index_b, byteorder='big', signed=False)
                            if received_index == NO_FILE:
                                os.remove(join(log_path, log))
                                print('NO FILE OK')
                                connection_socket.close()
                                break
                            else:
                                f = open(file_path, 'wb')
                                f.write(block)
                                f.close()
                                dict["index"] = index + 1
                                index = index + 1
                                with open(join(log_path, log), 'w') as f:
                                    json.dump(dict, f)
                                    f.close()
                        else:
                            pass
                        while index < total_block_number:  # from block 1
                            connection_socket.send(get_file_order(dict))
                            received_index_b, block = get_tcp_package(connection_socket)
                            if len(received_index_b) == 0 & len(block) == 0:
                                print('No one need this connection')
                                break
                            received_index = int.from_bytes(received_index_b, byteorder='big', signed=False)
                            print(f'received index: {received_index}, block_len: {len(block)}')
                            if received_index == SOCKET_CLOSE:
                                break
                            # file can be writen in specified index in order to resume from breakpoint
                            if index == received_index:
                                f = open(file_path, 'rb+')
                                f.seek(index * BLOCK_SIZE, 0)
                                f.write(block)
                                f.close()
                                print(f'index: {index}')
                                dict["index"] = index + 1
                                index = index + 1
                                if index < total_block_number - 1:
                                    with open(join(log_path, log), 'w') as f:
                                        json.dump(dict, f)
                                        f.close()
                            else:
                                continue
                        connection_socket.close()

                        if dict["size"] > 700000000:  # I need extract what I download
                            zip_filename = dict['name'].split('.')[0] + '.zip'
                            os.rename(join(dir_path, tem_file_name), join(dir_path, zip_filename))
                            unzip_file(zip_filename)
                            print(f'unzip file: {zip_filename}', end=' ')
                            size = getsize(dict['name'])
                        else:
                            size = os.path.getsize(file_path)
                        if size == dict["size"]:  # rename, delete log, update g_file_dict and calculate speed
                            print(f'{dict["name"]} file is received, size is correct')
                            formal_file_path = join(dir_path, dict["name"])
                            if dict['size'] < 700000000:
                                os.rename(file_path, formal_file_path)
                            mtime = os.path.getmtime(formal_file_path)
                            size = os.path.getsize(formal_file_path)
                            file_dict_local.update({dict["name"]: [mtime, size]})
                            os.remove(join(log_path, log))
                            if not exists(join(log_path, log)):
                                print('the correspond file ticket is removed from logs')
                            size = dict["size"]
                            finished_downloading_time = time.time()
                            consuming_time = finished_downloading_time - start_downloading_time
                            rounded_size = size / (1024 * 1024)
                            speed = size / (consuming_time * 1024 * 1024)
                            print(
                                f'downloaded {dict["name"]} of size {round(rounded_size, 3)} MB in {round(consuming_time, 3)} s')
                            print('speed: {:.3f} Mbps'.format(speed))
                        else:
                            print('size is incorrect')
                    else:
                        os.remove(join(log_path, log))
                else:
                    normal_filename = dict["name"].split('.')[0] + '.' + dict["name"].split('.')[1]  # vma.txt
                    file_path = join(dir_path, normal_filename)
                    if exists(file_path):
                        os.rename(file_path, join(dir_path, normal_filename + '.lefting'))  # vma.txt。lefting
                        dict["name"] = normal_filename
                        modified_size = 0.001 * dict['size']
                        index = 0
                        modified_block_number = math.ceil(modified_size / BLOCK_SIZE)
                        print(f'total block number: {modified_block_number}.')
                        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        connection_socket.connect((dict["peer"], PORT))
                        print(connection_socket)
                        while index < modified_block_number:
                            connection_socket.send(get_file_order(dict))
                            received_index_b, block = get_tcp_package(connection_socket)
                            if len(received_index_b) == 0 & len(block) == 0:
                                print('No one need this connection')
                                break
                            received_index = int.from_bytes(received_index_b, byteorder='big', signed=False)
                            print(f'received index: {received_index}, block_len: {len(block)}')
                            if received_index == SOCKET_CLOSE:
                                break
                            if index == received_index:
                                f = open(join(dir_path, normal_filename + '.lefting'), 'rb+')
                                f.seek(index * BLOCK_SIZE, 0)
                                f.write(block)
                                f.close()
                                print(f'index: {index}')
                                dict["index"] = index + 1
                                index = index + 1
                                if index < modified_block_number - 1:
                                    with open(join(log_path, log), 'w') as f:
                                        json.dump(dict, f)
                                        f.close()
                        connection_socket.close()
                        received_size = os.path.getsize(join(dir_path, normal_filename + '.lefting'))
                        if received_size == dict["size"]:
                            print(f'{dict["name"]} file is received, size is correct')
                            # if "/" in dict["name"]:
                            formal_file_path = join(dir_path, normal_filename)
                            os.rename(join(dir_path, normal_filename + '.lefting'), formal_file_path)
                            mtime = os.path.getmtime(formal_file_path)
                            size = os.path.getsize(formal_file_path)
                            file_dict_local.update({dict["name"]: [mtime, size]})
                            os.remove(join(log_path, log))
                            if not exists(join(log_path, log)):
                                print('the correspond file ticket is removed from logs')
                        else:
                            print('size is incorrect')
                    else:
                        print('356 should\'t reach')
                        os.remove(join(log_path, log))


def tcp_listener(server_port, file_dict):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', server_port))
    server_socket.listen(20)
    print('Server listening...')
    while True:
        conn, client_address = server_socket.accept()
        print('<< New connection from', client_address)
        th = threading.Thread(target=sub_connection, args=(conn, client_address, file_dict,))
        th.daemon = True
        th.start()


def make_package(d, b=None):
    dumped_json_string = json.dumps(b)
    json_header = json.dumps(d)
    json_length = len(json_header.encode())
    binary_data = dumped_json_string.encode()
    bin_length = len(binary_data)
    msg = struct.pack('!II', json_length, bin_length) + json_header.encode() + binary_data
    return msg


def get_tcp_package(connection_socket):
    header_b = connection_socket.recv(8)
    json_header_size = int.from_bytes(header_b[:4], byteorder='big', signed=False)
    data_header_size = int.from_bytes(header_b[4:], byteorder='big', signed=False)
    print(f'({json_header_size}, {data_header_size})')
    buf = b''
    while len(buf) < json_header_size:
        buf += connection_socket.recv(json_header_size)
    json_bin = buf[:json_header_size]
    buf = buf[json_header_size:]
    while len(buf) < data_header_size:
        buf += connection_socket.recv(data_header_size)
    data_bin = buf
    return json_bin, data_bin


def sub_connection(connection_socket, client_address, g_file_dict):
    while True:
        time.sleep(0.1)
        try:
            json_bin, data_bin = get_tcp_package(connection_socket)
        except OSError as er:
            continue
        if len(json_bin) == 0 & len(data_bin) == 0:
            time.sleep(1)
            json_bin, data_bin = get_tcp_package(connection_socket)
            if len(json_bin) == 0 & len(data_bin) == 0:
                print('No one need this connection')
                connection_socket.send(make_package("close"))
                break

        json_header = json_bin.decode()
        json_data = data_bin.decode()
        print(f'I receive json_header: {json_header}, json_data: {json_data}')  # test
        loaded_dict = json.loads(json_data)

        if "new" in json_header:
            for key in loaded_dict.keys():
                name = key.split('.')[0] + '.json'
                if '/' in name:
                    name = name.replace('/', '@')
                if not exists(join(log_path, name)):
                    json_ticket = {"name": key, "mtime": loaded_dict[key][0], "size": loaded_dict[key][1],
                                   "peer": client_address[0],
                                   "index": 0}
                    with open(join(log_path, name), 'w') as f:
                        json.dump(json_ticket, f)
                        print('log is added to log_path')
                        f.close()
            connection_socket.close()

        if "modified" in json_header:
            for key in loaded_dict.keys():
                json_ticket = {"name": key + '.modified', "mtime": loaded_dict[key][0],
                               "size": loaded_dict[key][1],
                               "peer": client_address[0],
                               "index": 0}
                name = key.split('.')[0] + '.modified.json'
                with open(join(log_path, name), 'w') as f:
                    json.dump(json_ticket, f)
                    print('log is added to log_path')
                    f.close()
            break

        if "hello" in json_header:
            checkout_new_file(client_address, loaded_dict, g_file_dict)
            connection_socket.send(make_package("hello_back", g_file_dict.copy()))
            print("I have say hello back")

        if "get_file" in json_header:
            if '@' in loaded_dict["name"]:  # rename if it's a file in a folder, because '/' can't appear in filename
                received_filename = loaded_dict["name"].replace('@', '/')
            elif 'modified' in loaded_dict["name"]:
                received_filename = loaded_dict["name"].split('.')[0] + '.' + loaded_dict["name"].split('.')[1]
            else:
                received_filename = loaded_dict["name"]
            index = loaded_dict["index"]
            if received_filename in g_file_dict.keys():
                if loaded_dict["size"] > 700000000:  # file over 700MB will be compressed
                    ziped_filename = received_filename.split('.')[0] + '.zip'
                    if not exists(join(dir_path, ziped_filename)):
                        zip_file(received_filename)
                    key = ziped_filename  # 'vma.zip'
                else:
                    key = received_filename

                block = get_file_block(key, index)
                index_b = index.to_bytes(4, byteorder='big')
                block_length = len(block)
                index_b_length = len(index_b)
                msg = index_b_length.to_bytes(4, byteorder='big') + block_length.to_bytes(4,
                                                                                          byteorder='big') + index_b + block
                connection_socket.send(msg)
                print(f'sender index: {index}, block_length: {block_length}')
            if received_filename not in g_file_dict.keys():
                header = NO_FILE
                header_b = header.to_bytes(4, byteorder='big')
                block = b''
                block_length = len(block)
                header_b_length = len(header_b)
                msg = header_b_length.to_bytes(4, byteorder='big') + block_length.to_bytes(4,
                                                                                           byteorder='big') + header_b + block
                connection_socket.send(msg)
                print("requested file doesn't exist")

    connection_socket.close()


def get_file_block(filename, block_index):
    f = open(join(dir_path, filename), 'rb')
    f.seek(block_index * BLOCK_SIZE)
    file_block = f.read(BLOCK_SIZE)
    f.close()
    return file_block


def checkout_new_file(client_address, remote_file_dict, g_file_dict):  # leave tickets to downloader
    if len(remote_file_dict) > 0:
        new = [file for file in remote_file_dict.keys() if file not in g_file_dict.keys()]
        print(f'new: {new}')
        if len(new) > 0:
            for name in new:
                if name.split('.')[-1] == 'zip':
                    new.remove(name)
                name_json = name.split('.')[0] + '.json'
                if '/' in name_json:
                    name_json = name.replace('/', '@')
                json_file_name = join(log_path, name_json)
                if not exists(json_file_name):
                    json_data = {"name": name, "mtime": remote_file_dict[name][0],
                                 "size": remote_file_dict[name][1],
                                 "peer": client_address[0], "index": 0}
                    print(f'json_data:{json_data}')
                    try:
                        f = open(json_file_name, 'w')
                        json.dump(json_data, f)
                        f.close()
                        print(f'log {name} is added')
                    except:
                        print('checkout_new_file fails')
                        continue
                else:
                    print('I have this log')
                    continue
        else:
            print(f'{client_address} has no file that I want')
    else:
        print(f'{client_address} has no file at all')


def get_file_order(dict_log):  # dict_log = {"name": "dog.jpg", "mtime": 24323.234, "size": 2100.0, "peer":"123.3.34.0"}
    dumped_json_string = json.dumps(dict_log)
    dumped_json_string_b = dumped_json_string.encode()
    json_header = json.dumps("get_file")
    json_length = len(json_header.encode())
    bin_length = len(dumped_json_string_b)
    return struct.pack('!II', json_length, bin_length) + json_header.encode() + dumped_json_string_b


def _argparse():
    parser = argparse.ArgumentParser(description="This is description!")
    parser.add_argument('--ip', action='store', required=True,
                        dest='ip', help='The ip addresses of vmb and vmc')
    return parser.parse_args()


def main():
    parser = _argparse()
    ip1 = parser.ip.split(',')[0]
    ip2 = parser.ip.split(',')[1]
    peers_ip = [ip1, ip2]
    g_file_dict = mp.Manager().dict({})

    file_list = traverse(dir_path)
    if len(file_list) > 0:
        for file in file_list:
            if '.' in file and file.split('.')[-1] != 'lefting':  # Don't record folder and lefting files
                g_file_dict[file] = [getmtime(file), getsize(file)]
    print(f'g_file_dict: {g_file_dict}')

    listener = Process(target=tcp_listener, args=(PORT, g_file_dict,))
    listener.daemon = True
    listener.start()
    print('listener starts')

    scanner = Process(target=file_scanner, args=(dir_path, g_file_dict, peers_ip,))
    scanner.daemon = True
    scanner.start()
    print('scanner starts checking...')

    downloader = Process(target=file_downloader, args=(g_file_dict,))
    downloader.daemon = True
    downloader.start()
    print('downloader starts checking...')

    for peer in peers_ip:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((peer, PORT))
            print(f'>>> I connect {peer}', end=' ')
            client_socket.send(make_package("hello", g_file_dict.copy()))  # send entire file dict to new connected peer
            print('I have successfully say hello')

            json_bin, data_bin = get_tcp_package(client_socket)
            json_header = json_bin.decode()
            json_data = data_bin.decode()
            print(f'I receive json_header: {json_header}, json_data: {json_data}')  # test
            loaded_dict = json.loads(json_data)
            checkout_new_file((peer, PORT), loaded_dict, g_file_dict)
        except:
            print(f'{peer} is off line')
            continue

    listener.join()
    scanner.join()
    downloader.join()


if __name__ == "__main__":
    main()
