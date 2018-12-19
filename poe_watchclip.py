#!/usr/bin/env python3
"""
Watch clipboard for unique items & query PoE official trade site for lowest price (by name).

Author: Vlad Ioan Topan (vtopan/gmail)
"""

import os
import re
import pprint
from tkinter import Tk, TclError  # Windows only, for easy clipboard access
import time

import requests


VER = '0.1.0 (dec.2018)'

PRICE_COUNT = 20    # number of (lowest) prices to retrieve
CURR_MAP_FILE = 'currency-map.txt'

# needed to map from the full names to the random-like shortcuts
if os.path.isfile(CURR_MAP_FILE):
    CURR_MAP = {e[0].strip():e[1].strip() for e in re.findall(r'([ \w\']+)\s*=\s*([-\w]+)',
        open(CURR_MAP_FILE).read())}
else:
    CURR_MAP = {'Exalted Orb': 'exa'}


def parse_item_info(text):
    """
    Parse item info (from clipboard, as obtained by pressing Ctrl+C hovering an item in-game).
    """
    m = re.findall(r'^Rarity: (\w+)\r?\n(.+?)\r?\n(.+?)\r?\n', text)
    if not m:
        return {}
    info = {'name': m[0][1], 'rarity': m[0][0], 'type': m[0][2]}
    if info['rarity'] == 'Currency':
        info['type'] = info.pop('rarity')
    m = re.findall(r'^Quality: +(\d+)%', text)
    info['quality'] = int(m[0]) if m else 0
    m = re.findall(r'^Sockets: ((?:\w-){5,})', text)
    if m:
        info['links'] = len(m[0]) // 2
    info['corrupted'] = bool(re.search('^Corrupted$', text, re.M))
    return info


def fetch_trade_results(ids, exchange=False):
    """
    Fetch the trade/exchange search results for the given ID list.
    """
    results = []
    if ids:
        # can only get max. 10 results in a request
        for i in range(0, PRICE_COUNT, 10):
            url = f'https://www.pathofexile.com/api/trade/fetch/{",".join(ids[i:i+10])}'
            # print(f'[#] Requesting {url}...')
            res = requests.get(url)
            if res.status_code != 200:
                print(f'[!] Trade result retrieval failed: HTTP {res.status_code}! '
                        f'Message: {res.json().get("error", "unknown error")}')
                break
            results += res.json()['result']
    return results


def query_trade(name=None, links=None, corrupted=None, rarity=None, league='Betrayal', priced=None):
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

    :return: A list of {'id':..., 'item': {'frameType':..., 'explicitMods': [...], 'name': ...,
            etc.}, etc.}
    """
    j = {'query':{'filters':{}}, 'sort': {'price': 'asc'}}
    if name:
        j['query']['name'] = name
    if links:
        j['query']['filters']['socket_filters'] = {'filters': {'links': {'min': links}}}
    if corrupted is not None:
        j['query']['filters']['misc_filters'] = {'filters': {'corrupted': {'option':
                str(corrupted).lower()}}}
    if rarity:
        j['query']['filters']['type_filters'] = {'filters': {'rarity': {'option': rarity.lower()}}}
    if priced is not None:
        j['query']['filters']['trade_filters'] = {'filters': {'sale_type': {'option': 'priced'}}}
    # print('[#] Query parameters:')
    # pprint.pprint(j)
    res = requests.post(f'https://www.pathofexile.com/api/trade/search/{league}', json=j)
    jres = res.json()
    if res.status_code != 200:
        print(f'[!] Trade query failed: HTTP {res.status_code}! '
                f'Message: {jres.get("error", "unknown error")}')
        return []
    results = fetch_trade_results(jres['result'])
    return results


def query_exchange(currency, league='Betrayal'):
    """
    Query pathofexile.com/trade/exchange for how much a currency sells.
    """
    qcurrency = CURR_MAP.get(currency, currency.replace(' ', '-').replace("'", '').lower())
    j = {'exchange': {'have': ['chaos'], 'want': [qcurrency], 'status': {'option': 'online'}}}
    # print('[#] Query parameters:')
    # pprint.pprint(j)
    res = requests.post(f'https://www.pathofexile.com/api/trade/exchange/{league}', json=j)
    jres = res.json()
    if res.status_code != 200:
        print(f'[!] Trade query failed: HTTP {res.status_code}! '
                f'Message: {jres.get("error", "unknown error")}')
        return []
    results = fetch_trade_results(jres['result'], exchange=True)
    if results and results[0]['item']['typeLine'] != currency:
        results = []
        print(f'[!] Failed translating {currency} to short name; add it to currency-map.txt!')
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
        except TclError:     # ignore non-text clipboard contents
            continue
        try:
            if text != prev:
                info = parse_item_info(text)
                # pprint.pprint(info)
                trade_info = None
                if info:
                    if info.get('rarity') == 'Unique':
                        print('[*] Found unique item in clipboard: %(name)s (%(type)s)' % info)
                        print('[-] Getting prices from pathofexile.com/trade...')
                        trade_info = query_trade(priced=True,
                                **{k:v for k, v in info.items() if k in ('name', 'links',
                                'corrupted', 'rarity')})
                    elif info['type'] == 'Currency':
                        print(f'[-] Found currency {info["name"]} in clipboard; '
                                'getting prices from pathofexile.com/trade/exchange...')
                        trade_info = query_exchange(info['name'])
                    if trade_info:
                        prices = [x['listing']['price'] for x in trade_info]
                        prices = ['%(amount)s%(currency)s' % x for x in prices]
                        prices = {'%s x %s' % (prices.count(x), x):None for x in prices}
                        print(f'[-] Lowest {PRICE_COUNT} prices: {", ".join(prices.keys())}')
                    elif trade_info is not None:
                        print(f'[!] No results!')
                prev = text
            time.sleep(.3)
        except KeyboardInterrupt:
            break


if __name__ == '__main__':
    watch_clipboard()
