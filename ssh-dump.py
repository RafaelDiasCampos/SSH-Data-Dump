from subprocess import Popen, PIPE
from enum import Enum
import os
import re
from argparse import ArgumentParser

class FileType(Enum):
    FILE = 1
    DIRECTORY = 2

ignored_dirs = ["/dev", "/proc", "/sys"]
ignored_files = ["[", "[["]

def read_output(p):
    output = ""
    while True:
        out_byte = p.stdout.read(1)
        if not out_byte:
            break
        output += out_byte.decode()
        if output.endswith(" > "):
            output = output[:-3]
            if len(output) and output[-1] == "\n":
                output = output[:-1]
            break
    return output

def read_bytes(p, n):    
    return p.stdout.read(n)

def connect(host, username):
    p = Popen(f'ssh {username}@{host}', stdout = PIPE, 
        stderr = PIPE, stdin= PIPE, shell = True)

    read_output(p)

    return p

def run_command(p, command):
    p.stdin.write(f"{command}\n".encode())
    p.stdin.flush()
    raw_output = read_output(p) 
    parsed_output = raw_output.split("\n")[1:]
    return parsed_output

def parse_directory(p, path):
    if path in ignored_dirs:
        return []
    
    result = run_command(p, f"ls -lLa {path}")

    directory_info = []

    for line in result:
        line_split_raw = line.split(" ")
        line_split = [x for x in line_split_raw if x != ""]

        permissions = line_split[0]
        size = line_split[4]
        name = line_split[-1]

        if name == "." or name == "..":
            continue

        if size[-1] == ",":
            continue

        if permissions[0] == "d":
            directory_info.append({
                "type": FileType.DIRECTORY,
                "name": name
            })
        else:
            directory_info.append({
                "type": FileType.FILE,
                "name": name,
                "size": int(size)
            })

    return directory_info

def save_file(p, path, size):
    command = f"cat {path}\n"
    p.stdin.write(command.encode())
    p.stdin.flush()

    output_size = size + len(command)

    output = read_bytes(p, output_size)
    read_output(p)

    output = output[len(command):]
    
    output_file = os.path.join("output", path)
    output_file = re.sub(r'<|>|:|\?|\*' , "_", output_file)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "wb") as f:
        f.write(output)

def save_all_files(p, path = ""):
    directory_info = parse_directory(p, path)

    for file in directory_info:
        if file["name"] in ignored_files:
            continue
        if file["type"] == FileType.FILE:
            save_file(p, f".{path}/{file['name']}", file["size"])
        else:
            save_all_files(p, f"{path}/{file['name']}")

def main():
    parser = ArgumentParser()
    parser.add_argument("host", type=str)
    parser.add_argument("username", type=str)

    args = parser.parse_args()

    p = connect(args.host, args.username)

    save_all_files(p)

if __name__ == "__main__":
    main()