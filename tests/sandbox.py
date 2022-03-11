#!/usr/bin/env python3

from enum import Enum
import re
import time
from typing import List, Tuple

from solys2moon import solys2 as s2
from solys2moon import autotrack as aut

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
            only_nums_split = only_nums.split()
            isdecimal = all(s.isdecimal() for s in only_nums_split)
            if isdecimal:
                numbers = list(map(float, only_nums_split))
            else:
                numbers = [1]
        else:
            numbers = [1]
    else:
        out_code = OutCode.NONE
        if rstrip.startswith("NO"):
            out_code = OutCode.ERROR
            err_code = rstrip.split()[1]
            print("ERROR {}: {}".format(err_code, s2.translate_error(err_code)))
    return numbers, out_code

def send_command(s: s2.connection.SolysConnection, cmd: str):
    resp = s.send_cmd(cmd)
    print(cmd)
    print("Respuesta: {}".format(resp))
    nums, out = read_output(resp, cmd)
    while out == OutCode.NONE:
        time.sleep(0.1)
        resp = s.recv_msg()
        nums, out = read_output(resp, cmd)
        print("Respuesta: {}".format(resp))

def pruebas_comandos_raw():
    s = s2.connection.SolysConnection(TCP_IP, TCP_PORT)
    cmd_pwd = "PW solys"
    cmd_prot = "PR 0"
    cmd = "PO"
    send_command(s, cmd_pwd)
    send_command(s, cmd_prot)
    send_command(s, cmd)
    send_command(s, "VE")
    #send_command(s, "PO 1 40")
    s.close()

def main():
    aut.track_sun(TCP_IP, 30, TCP_PORT, "solys", True)

if __name__ == "__main__":
    main()