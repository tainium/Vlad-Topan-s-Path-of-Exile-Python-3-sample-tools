#!/usr/bin/env python3
"""
Sample Path of Exile client.txt monitor.

To obtain the full process path (and thus to find Client.txt), we use the Windows APIs:

- FindWindow("Path of Exile", ...) to get a window handle
- GetWindowThreadProcessId(hwnd, ...) to obtain the PID
- OpenProcess(PROCESS_QUERY_INFORMATION, pid, ...) to obtain a process handle
- QueryFullProcessImageNameW(proc_handle, ...) to obtain the process image (executable) path

Author: Vlad Ioan Topan (vtopan/gmail)
"""

import ctypes
from ctypes import byref, windll, WINFUNCTYPE, get_last_error, FormatError
from ctypes.wintypes import BOOL, DWORD, PDWORD, HANDLE, HWND, LPWSTR
import os
import sys


VER = '0.1.0 (dec.2018)'

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

FindWindow = WINFUNCTYPE(HWND, LPWSTR, LPWSTR)(("FindWindowW", windll.user32))
GetWindowThreadProcessId = WINFUNCTYPE(DWORD, HWND, PDWORD)(("GetWindowThreadProcessId",
    windll.user32))
OpenProcess = WINFUNCTYPE(HANDLE, DWORD, BOOL, DWORD)(("OpenProcess", windll.kernel32))
QueryFullProcessImageName = WINFUNCTYPE(BOOL, HANDLE, DWORD, LPWSTR,
        PDWORD)(("QueryFullProcessImageNameW", windll.kernel32))
CloseHandle = WINFUNCTYPE(BOOL, HANDLE)(("CloseHandle", windll.kernel32))


def last_error():
    """
    Returns the last error as reported by the OS.
    """
    err = get_last_error()
    return "0x%08X: %s" % (err, FormatError(err))


def get_poe_path():
    """
    Returns the path to the PoE folder (or None if the game isn't running).
    """
    hwnd = FindWindow(None, "Path of Exile")
    if not hwnd:
        return None
    pid = DWORD(0)
    GetWindowThreadProcessId(hwnd, byref(pid))
    pid = pid.value
    # print(f'[#] PoE PID: {pid}')
    ph = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if ph is None:
        raise OSError(f'[!] OpenProcess(pid={pid}) failed: {last_error()}')
    size = DWORD(2048)
    buf = ctypes.create_unicode_buffer(size.value)
    res = QueryFullProcessImageName(ph, 0, buf, byref(size))
    if not res:
        raise OSError(f'[!] QueryFullProcessImageName() failed: {last_error()}')
    exe_path = str(buf.value)
    # print(f'[#] EXE path: {exe_path}')
    CloseHandle(ph)
    return os.path.dirname(exe_path)


def watch_area_changes():
    """
    Watch client.txt for area changes (the game must be runing).
    """
    poe_path = get_poe_path()
    print(f'[*] PoE path: {poe_path}')
    if not poe_path:
        sys.exit()
    log_path = os.path.join(poe_path, 'logs\\client.txt')
    log_size = os.path.getsize(log_path)
    print(f'[*] Log path: {log_path}; size: {log_size/1024/1024:.2f}MB')
    # read "tail" (last 1 MB)
    fh = open(log_path, 'rb')
    if log_size > 1024 * 1024:
        fh.seek(log_size - 1024 * 1024)
    tail = fh.read().decode('utf8', errors='replace')
    marker = '] : You have entered '
    pos = tail.rfind(marker)
    if pos < 0:
        print('[!] No area change message found in log tail!')
        crt_area = 'unknown'
    else:
        crt_area = tail[pos + len(marker):].split('\n', 1)[0].strip('\r\n .')
        print(f'[*] Current area: {crt_area}')
    print('[*] Watching for area changes; press Ctrl+C to stop...')
    while 1:
        line = fh.readline().decode('utf8', errors='replace')
        if marker in line:
            crt_area = line[line.find(marker) + len(marker):].strip('\r\n .')
            # a more elegant extraction would be re.search(r'\] : You have entered ([\w -]+)', line)
            print(f'[*] Area changed: {crt_area}')


if __name__ == '__main__':
    watch_area_changes()

