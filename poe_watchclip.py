#!/usr/bin/env python3
"""
Watch clipboard for unique items & query PoE official trade site for lowest price (by name).

Author: Vlad Ioan Topan (vtopan/gmail)
"""

import binascii
import json
import re
import pprint
from tkinter import Tk  # Windows only, for easy clipboard access
import time
import zlib

import requests


VER = '0.1.0 (dec.2018)'

PRICE_COUNT = 20    # number of (lowest) prices to retrieve


def parse_item_info(text):
    """
    Parse item info (from clipboard, as obtained by pressing Ctrl+C hovering an item in-game).
    """
    m = re.findall(r'^Rarity: (\w+)\r?\n(.+?)\r?\n(.+?)\r?\n', text)
    if not m:
        return {}
    info = {'name': m[0][1], 'rarity': m[0][0], 'type': m[0][2]}
    m = re.findall(r'^Quality: +(\d+)%', text)
    info['quality'] = int(m[0]) if m else 0
    m = re.findall(r'^Sockets: ((?:\w-){5,})', text)
    if m:
        info['links'] = len(m[0]) // 2
    info['corrupted'] = bool(re.search('^Corrupted$', text, re.M))
    return info
    
    
def query_trade(name=None, links=None, corrupted=None, rarity=None, league='Betrayal', priced=None, max_res=10):
    """
    Query pathofexile.com/trade.
    
    Price in results:
        {'listing': {
            'account': {'lastCharacterName': '...',
                        'name': '...',
                        'online': {'league': 'Betrayal', 'status': 'afk'}}, ...},
            'indexed': '2018-12-10T08:44:20Z',
            'price': {'amount': 1, 'currency': 'exa', 'type': '~price'},
            'stash': {'name': '...', 'x': ..., 'y': ...}, ...}
    
    :return: A list of {'id':..., 'item': {'frameType':..., 'explicitMods': [...], 'name': ..., etc.}, etc.}
    """
    j = {'query':{'filters':{}}, 'sort': {'price': 'asc'}}
    if name:
        j['query']['name'] = name
    if links:
        j['query']['filters']['socket_filters'] = {'filters': {'links': {'min': links}}}
    if corrupted is not None:
        j['query']['filters']['misc_filters'] = {'filters': {'corrupted': {'option': str(corrupted).lower()}}}
    if rarity:
        j['query']['filters']['type_filters'] = {'filters': {'rarity': {'option': rarity.lower()}}}
    if priced is not None:
        j['query']['filters']['trade_filters'] = {'filters': {'sale_type': {'option': 'priced'}}}
    # print('[#] Query parameters:')
    # pprint.pprint(j)
    res = requests.post(f'https://www.pathofexile.com/api/trade/search/{league}', json=j)
    jres = res.json()
    if res.status_code != 200:
        print(f'[!] Trade query failed: HTTP {res.status_code}! Message: {jres.get("error", "unknown error")}')
        return {}
    if jres['result']:
        results = []
        # can only get max. 10 results in a request
        for i in range(0, max_res, 10):
            url = f'https://www.pathofexile.com/api/trade/fetch/{",".join(jres["result"][i:i+10])}'
            # print(f'[#] Requesting {url}...')
            res = requests.get(url)
            if res.status_code != 200:
                print(f'[!] Trade result retrieval failed: HTTP {res.status_code}! Message: {res.json().get("error", "unknown error")}')
                break
            results += res.json()['result']
    return results
    
    
def watch_clipboard():
    """
    Watch clipboard for unique items being copied to check lowest prices on trade.
    """
    print('[*] Watching clipboard (Ctrl+C to stop)...')
    prev = None    
    while 1:
        try:
            text = Tk().clipboard_get()
            if text != prev:
                info = parse_item_info(text)
                if info and info['rarity'] == 'Unique':
                    print('[*] Found unique item in clipboard: %(name)s (%(type)s)' % info)
                    # pprint.pprint(info)
                    print('[-] Getting prices from pathofexile.com/trade...')
                    tinfo = query_trade(priced=True, max_res=PRICE_COUNT, **{k:v for k, v in info.items() if k in ('name', 'links', 'corrupted', 'rarity')})
                    if not tinfo:
                        print('[!] No results!')
                    else:
                        prices = [x['listing']['price'] for x in tinfo]
                        prices = ['%(amount)s%(currency)s' % x for x in prices]
                        prices = {'%s x %s' % (prices.count(x), x):None for x in prices}
                        print(f'[-] Lowest {PRICE_COUNT} prices: {", ".join(prices.keys())}')                        
                prev = text
            time.sleep(.3)
        except KeyboardInterrupt:
            break
            
            
if __name__ == '__main__':
    watch_clipboard()
