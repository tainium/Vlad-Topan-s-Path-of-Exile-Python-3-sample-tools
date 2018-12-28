#!/usr/bin/env python3
"""
Display an overlay window showing if the game is running or not (as an example).

The window is "always on top" (including over the Path of Exile window if it's in either "Windowed"
or "Windowed full screen" modes (see the game video settings).

The tkinter module used for the UI is included in the standard Python installer on Windows.

See poe_clienttxt.py for an example on how to watch for changes in the game log (client.txt), which
contains information about the current area (and thus a method to find out e.g. if the user is in
his hideout or not).

Author: Vlad Ioan Topan (vtopan/gmail)
"""

from ctypes import windll, WINFUNCTYPE
from ctypes.wintypes import HWND, LPWSTR
import threading
import time
from tkinter import Tk, Button, Label, StringVar, GROOVE


VER = '0.1.0 (dec.2018)'


FindWindow = WINFUNCTYPE(HWND, LPWSTR, LPWSTR)(("FindWindowW", windll.user32))
STOP = 0    # poll stop flag; proper sync should be used in production code


def poll_poe_window(tkvar):
    """
    Continuously poll the PoE window's existence and update the Tk variable.
    """
    while 1:
        if STOP:
            break
        is_running = None != FindWindow(None, "Path of Exile")  # NOQA
        tkvar.set(f'PoE is {"" if is_running else "not"} running')
        time.sleep(0.2)


def quit(root):
    """
    Stop polling & the main UI loop.
    """
    global STOP
    STOP = 1
    time.sleep(0.2)
    root.quit()


def show_ui():
    global STOP

    # the overlay's main window
    root = Tk()

    # topmost, no borders, center horizontally, top-of-screen
    root.wm_attributes("-topmost", 1)
    root.attributes("-toolwindow", 1)
    w, h = 150, 60
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    root.geometry('{}x{}+{}+{}'.format(w, h, x, 0))
    root.update_idletasks()
    root.overrideredirect(True)

    # game status label
    crt_area = StringVar()
    l_area = Label(root, textvariable=crt_area, relief=GROOVE)
    crt_area.set('-')
    l_area.pack(pady=5)

    # quit button
    but = Button(root, command=lambda:quit(root), text='Close')
    but.pack()

    # start polling thread
    threading.Thread(target=poll_poe_window, args=(crt_area,)).start()
    root.mainloop()
    STOP = 1


if __name__ == '__main__':
    show_ui()

