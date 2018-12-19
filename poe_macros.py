#!/usr/bin/env python3
"""
Send custom text on keypress (macros) to the active window.

Author: Vlad Ioan Topan (vtopan/gmail)
"""

import keyboard

import os
import re


VER = '0.1.0 (dec.2018)'

CMAP = {
    'cr': 'enter',
    }


def _text_sender(text):
    def _inner():
        for e in re.findall('\{[^\}]+\}|[^\{\}]+', text):
            if e[0] == '{':
                e = e[1:-1]
                if e.isnumeric():
                    e = int(e)
                else:
                    e = CMAP.get(e.lower(), e)
                # print(f'Key: {e}')
                keyboard.send(e)
            else:
                # print(f'Text: {e}')
                keyboard.write(e)
    return _inner


def add_macro(shortcut, text):
    print(f'[*] Adding macro {shortcut} -> {repr(text)}...')
    keyboard.add_hotkey(shortcut, _text_sender(text), suppress=True)


def load_macros():
    if not os.path.isfile('macros.txt'):
        print('[!] Rename macros.txt.sample to macros.txt and add macros to it!')
        return
    for m in open('macros.txt'):
        if (not m.strip()) or m.lstrip()[0] == '#':
            continue
        add_macro(*m.strip().split('|',1))


if __name__ == '__main__':
    print('[*] Waiting for Ctrl+C to stop...')
    load_macros()
    keyboard.wait()
