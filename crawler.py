#!/usr/bin/env python3
import re
import sys
import json
import shutil
import socket
import threading
import pandas as pd
from requests import get
from time import sleep
from retriever.searcher import search

def remove_html_tags(text):
    """ Remove html tags with regex"""
    text = re.sub(r'(?=<!--)([\s\S]*?)-->', '', text)
    text = re.sub(r'(?=/\*)([\s\S]*?)\*/', '', text)
    scripts = re.compile(r"<script[^>]*>.*?</script>", 
            flags=re.DOTALL)
    styles = re.compile(r"<style[^>]*>.*?</style>",
            flags=re.DOTALL)
    tags = re.compile(r'<[^>]+>|&nbsp|&amp|&lt|&gt|&quot|&apos')
    text = re.sub(tags, '', 
            re.sub(styles, '', 
                re.sub(scripts, '', 
                    re.sub(r'[\r\n\t]', '', text))))
    return text

def rank_data(query, data):
    """ Sort data by similarity to query """
    pages = list(data.values())
    df = pd.DataFrame(pages, columns=['pages'])
    df['pages'] = df['pages'].apply(lambda x:[x])
    return list(map(lambda x: x.tolist()[0][0], search(query, df)))

def main():
    """ Actual searcher """
    global visited, \
        data, \
        children, \
        locked, \
        depth_counter, \
        pos_q, \
        neg_q

    cols = lambda: shutil.get_terminal_size().columns
    clrline = lambda : print('\r' + ' '*cols() + '\r', end="", flush=True)
    q_len = lambda: len(pos_q) + len(neg_q)
    print_status = lambda: print((f'{green}Depth: {depth_counter}  Queued: {q_len()}  '
        f'Searched: {len(data)}  Current: {curr[:70]+"..." if len(curr)>75 else curr}{reset}'), end='', flush=True)

    while True:
        while q_len() == 0 or locked:
            sleep(0.1)

        if len(pos_q) > 0:
            curr = pos_q.pop(0)
        else:
            curr = neg_q.pop(0)

        delim = curr.index('onion') + 5

        if curr not in visited:
            visited.append(curr)
        else:
            continue

        try:
            tosearch = get(curr, 
                    proxies={
                        'http':'socks5h://localhost:9050',
                        'https':'socks5h://localhost:9050'
                    },
                    timeout=7).text

            if len(tosearch) > 30:
                # Doing this because after ranking pages we can grab url easily
                data[curr] = curr + ' || ' + remove_html_tags(tosearch)
            else:
                continue

            clrline()
            print_status()

        except Exception as err:
            clrline()
            print(f'{red}{curr} took too long to respond{reset}')
            print_status()

            # If a url is unresponsive remove all its subdirectories from queues
            pos_q = list(filter(lambda x: not x.startswith(curr[:delim]), pos_q))
            neg_q = list(filter(lambda x: not x.startswith(curr[:delim]), neg_q))

            continue

        complete_urls = set(map(lambda x: x[0], 
            re.findall(url_regex, tosearch)))
        unique_complete = complete_urls - set(visited) - (set(pos_q).union(set(neg_q)))

        subdirs = set(map(lambda x: curr[:delim] + x, 
            re.findall(subdir_regex, tosearch)))
        unique_subdirs = subdirs - set(visited) - (set(pos_q).union(set(neg_q)))

        unique = unique_complete.union(unique_subdirs)

        positive_set = set(filter(lambda x: any(list(keyword in x.lower() for keyword in query)), unique))
        pos_q.extend(list(positive_set))
        neg_q.extend(list(unique - positive_set)[:10])

        clrline()

        if len(unique) > 0:
            if len(neg_q) > 0:
                print('\n'.join(neg_q[:50]))
            if len(pos_q) > 0:
                print('\n'.join(pos_q))
                
            children[curr] = [list(pos_q), list(neg_q)]

        else:
            print(f'{red}No links found in {curr}{reset}')

        print_status()

        if not locked and len(data) > 45:
            locked = True

            date_copy = data.copy()
            sorted_pages = rank_data(' '.join(query), date_copy)
            data = {}

            sorted_urls = list(map(lambda x: x[:x.index(' || ')], sorted_pages))

            separator = '\n' + ' ' * 24
            toprint = separator.join(sorted_urls[:2])
            clrline()
            print(f'{green}Best result at depth {depth_counter}: {toprint}{reset}\n')
            depth_counter += 1

            with open('results.txt', 'a') as f:
                f.write(f'{depth_counter}. {sorted_urls[0]} \n{depth_counter}. {sorted_urls[1]} \n\n')

            for url in sorted_urls:
                # If url has children shift all children to beginning of q
                if url in children:
                    pos_q = children[url][0] + pos_q
                    neg_q = children[url][1] + neg_q
                else:
                    print(f'{url} has no children')

            locked = False


if __name__ == '__main__':

    query = list(map(lambda x: x.lower(), [
            'flipkart',
            'leak',
            'leaked',
            'cybercrime',
            'breach',
            'hacking',
            'blackhat',
        ]))


    banned_types = "|".join([
            'png',
            'svg',
            'gif',
            'jpg',
            'mp4',
            'js',
            'css',
            'xml',
            'rss',
            'jpeg'
        ])

    url_regex = rf'((?:https?:\/\/)\w+.onion\/?(?!\S+?({banned_types}))[\w\/\-%.]*\/?)'
    subdir_regex = r'<a href="(\/\S*(?:html|php))">'

    pos_q = []
    neg_q = [
            "http://puvurb7xtke4mhy56fuoexp522ou67gd37sodgc6agaas6vg2wb54vad.onion/index.php?title=Main_Page",
            "http://l2rovcfp45ucvnb4futewkhmxqb6kktruoagx57a4zgmvjewjl2ftpyd.onion/",
            # "http://cavetord6bosm3sl.onion/",
            # "http://s6cco2jylmxqcdeh.onion/",
            # "http://z2hjm7uhwisw5jm5.onion/",
            # "http://zw3crggtadila2sg.onion/",
            # "http://76qugh5bey5gum7l.onion/",
            # "http://koi6xzo34wxxvs6m.onion/",
            # "http://torpress2sarn7xw.onion/"
        ]
    visited = []
    children = {}
    data = {}

    depth_counter = 0
    locked = False

    # Must do this if you want colours to work on windows
    iswin = sys.platform.startswith('win')
    if iswin:
        os.system('color')

    green = '\x1b[32m'
    red = '\x1b[31m'
    reset = '\x1b[0m'

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    host = socket.getaddrinfo('127.0.0.1', 9050)
    status = sock.connect_ex(host[-1][4])
    if status != 0:
        print('{red}Tor proxy not found on port 9050, aborting{reset}')
        exit(0)

    # Clear results file
    open('results.txt', 'w').close()

    threads=[]
    for _ in range(150):
        threads.append(threading.Thread(target=main))
        threads[-1].start()
        threads[-1].join()
