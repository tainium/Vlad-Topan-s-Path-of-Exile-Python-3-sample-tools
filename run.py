#!/usr/bin/env python3
"""
Run all PoE tools.

Author: Vlad Ioan Topan (vtopan/gmail)
"""
import poe_macros
import poe_watchclip


poe_macros.load_macros()
poe_watchclip.watch_clipboard()
