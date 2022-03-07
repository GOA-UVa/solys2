from enum import Enum
import re
import time
from typing import List, Tuple

from solys2moon import solys2moon as s2m

TCP_IP = "157.88.43.171"
TCP_PORT = 15000

class OutCode(Enum):
    NONE = -1
    ERROR = 0
    ANSWER = 1


def read_output(s: str, cmd: str) -> Tuple[List[float], 'OutCode']:
    rstrip = s.strip()
    out_code = OutCode.ANSWER
    numbers = []
    if rstrip.startswith(cmd[:2]):
        temp = re.sub(cmd, '', rstrip)
        unwateted = re.sub('(\d|\.|\ )', '', temp)
        only_nums = re.sub(unwateted, '', temp)
        if len(only_nums) > 0:
            numbers = list(map(float, only_nums.split()))
    else:
        out_code = OutCode.NONE
        if rstrip.startswith("NO"):
            out_code = OutCode.ERROR
            err_code = rstrip.split()[1]
            print("ERROR {}: {}".format(err_code, s2m.ERROR_CODES[err_code]))
    return numbers, out_code

def send_command(cmd: str):
    resp = s2m.connection.send_command(cmd)
    print(cmd)
    print("Respuesta: {}".format(resp))
    nums, out = read_output(resp, cmd)
    while out == OutCode.NONE:
        time.sleep(0.1)
        resp = s2m.connection.recv_msg()
        nums, out = read_output(resp, cmd)
        print("Respuesta: {}".format(resp))

def main():
    print("e")
    cmd_pwd = "PW solys"
    cmd_prot = "PR 0"
    cmd = "PO"
    s2m.connection.connect(TCP_IP, TCP_PORT)
    send_command(cmd_pwd)
    send_command(cmd_prot)    
    send_command(cmd) 
    send_command("MS")
    #send_command("PO 1 40")
    s2m.connection.close_connection()

if __name__ == "__main__":
    main()