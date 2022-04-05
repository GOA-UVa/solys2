#!/usr/bin/env python3

from enum import Enum
import re
import time
from typing import List, Tuple
import logging

from solys2 import solys2 as s2
from solys2.automation import autotrack as aut
from solys2 import positioncalc as psc

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
    send_command(s, "PO 1 94.9")
    #send_command(s, "PO 1 40")
    s.close()

def prueba_cross():
    cp = aut.CrossParameters(-1, 1, 0.1, -1, 1, 0.1, 5, 3)
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("sandbox")
    aut.solar_cross(TCP_IP, logger, cp, TCP_PORT, "solys", library=psc.SunLibrary.SPICEDSUN, altitude=710, kernels_path="./kernels.temp.dir")

def prueba_black():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("sandbox")
    aut.black_moon(TCP_IP, logger, library=psc.MoonLibrary.PYLUNAR)

def prueba_track():
    #mt = aut.MoonTracker(TCP_IP, 15, TCP_PORT, "solys", True, "./log.out.temp.txt", psc.MoonLibrary.SPICEDMOON, altitude=710, kernels_path="./kernels.temp.dir")
    handler = logging.StreamHandler()
    st = aut.SunTracker(TCP_IP, 15, TCP_PORT, "solys", True, "./log.out.temp.txt", psc.SunLibrary.SPICEDSUN, altitude=710, kernels_path="./kernels.temp.dir",
        extra_log_handlers=[handler])

def main():
    prueba_track()

if __name__ == "__main__":
    main()