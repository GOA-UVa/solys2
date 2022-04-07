#!/usr/bin/env python3

"""
Solys2 "server" simulator so the app can be executed without a real Solys2.
"""

import socket
import time
import threading

current_azimuth = 0
current_zenith = 0

azimuth_adj = 0
zenith_adj = 0

def server_thread(conn: socket.socket):
    global current_azimuth
    global current_zenith
    global azimuth_adj
    global zenith_adj
    print("new connection")
    empties = 0
    while True:
        if empties > 1000:
            break
        data = conn.recv(1024)
        if data:
            empties = 0
            print(data)
            cmd = str(data)[2:4]
            if cmd == "TI":
                ret = "TI 2022 93 15 15 15"
            elif cmd == "PO":
                vals = str(data)[2:-3].split()
                if int(vals[1]) == 0:
                    current_azimuth = float(vals[2])
                else:
                    current_zenith = float(vals[2])
                ret = "PO"
            elif cmd == "CP":
                ret = "CP {} {}".format(current_azimuth+azimuth_adj, current_zenith+zenith_adj)
            elif cmd == "AD":
                vals = str(data)[2:-3].split()
                if len(vals) <= 1:
                    ret = "AD {} {}".format(azimuth_adj, zenith_adj)
                else:
                    print(vals)
                    if int(vals[1]) == 0:
                        azimuth_adj += float(vals[2])
                    else:
                        zenith_adj += float(vals[2])
                    ret = "AD"
            else:
                ret = "{} 1 1 1 1 1 1 1 1 1 1 1".format(cmd)
            print(ret)
            conn.sendall(bytes(ret, "utf-8"))
        else:
            empties += 1
        time.sleep(0.1)
    print("Socket unused")
    conn.close()

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_address = ('localhost', 15000)
    sock.bind(server_address)
    sock.listen(1)
    stopped = False
    while not stopped:
        try:
            conn, (ip, port) = sock.accept()
        except socket.timeout:
            pass
        except:
            raise
        else:
            th = threading.Thread(target=server_thread, args=[conn])
            th.start()


if __name__ == "__main__":
    main()
