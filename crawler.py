#!/usr/bin/env python3
import re
import sys
import json
import shutil
import socket
import threading
import pandas as pd
from requests import get
from time import sleep, time
from base64 import b64decode
from hashlib import md5
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

def calculate_rank(query, data):
    """ Sort data by similarity to query """
    pages = list(data.values())
    df = pd.DataFrame(pages, columns=['pages'])
    df['pages'] = df['pages'].apply(lambda x:[x])
    scores, pages = search(query, df)
    return scores, list(map(lambda x: x.tolist()[0][0], pages))

def assign_ranks(final=False):
    """ Assign ranks and save result """
    global locked, \
            depth, \
            pos_q, \
            neg_q, \
            data

    if not locked and (len(data) > 15*(depth+1) or final):
        locked = True

        scores, sorted_pages = calculate_rank(' '.join(query), data)

        data = {}

        try:
            sorted_urls = list(map(lambda x: x[:x.index(' || ')], sorted_pages))
        except Exception:
            print(f'\r{" "*cols()}\r{red}|| ERROR{reset}')
            locked = False
            return 1

        for url in reversed(sorted_urls):
            # If url has children shift all children to beginning of q
            if url in children:
                pos_q = children[url][0] + list(set(pos_q)-set(children[url][0]))
                neg_q = children[url][1] + list(set(neg_q)-set(children[url][1]))

        clrline()
        separator = '\n' + ' ' * 24
        toprint = separator.join(sorted_urls[:5])
        print(f'{yellow}\nBest result at depth {depth}: {toprint}{reset}\n')
        # for url in sorted_urls[:5]:
        #     print(f'{yellow}{url} {page_hashes[url]}{reset}')
        depth += 1

        with open('results.txt', 'a') as f:
            for i in range(3):
                try:
                    a = sorted_pages[i].index(' || ')
                except Exception:
                    print(f'\r{" "*cols()}\r{red}|| ERROR {sorted_pages[i][:60]}{reset}')
                    locked = False
                    return 1

                f.write(f'{sorted_urls[i]} - {sorted_pages[i][a+4:a+56]}\n')
            f.write('\n')

        locked = False

    return 0

def main():
    """ Actual searcher """
    global visited,    \
        prevscores,    \
        data,          \
        children,      \
        locked,        \
        depth,         \
        should_exit,   \
        pos_q,         \
        neg_q,         \
        page_hashes,   \
        blacklist

    q_len = lambda: len(pos_q) + len(neg_q)
    print_status = lambda: print((f'\r{" "*cols()}\r{green}Depth: {depth}  Queued: {q_len()}  '
        f'Searched: {len(data)}  Current: {curr[:70]+"..." if len(curr)>75 else curr}{reset}'), end='', flush=True)

    while True:
        if should_exit:
            break

        start = time()
        while q_len() == 0 or locked:
            sleep(0.5)
            if(time() - start > 10):
                if len(data)>0:
                    assign_ranks(final=True)

                should_exit = True
                return

        if len(pos_q) > 0:
            curr = pos_q.pop(0)
            timeout = 10
        else:
            curr = neg_q.pop(0)
            timeout = 9

        print_status()

        delim = curr.index('onion') + 5

        # if subdirs of site have been visited more than 20 times then dont visit site
        # again
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
                timeout=timeout).text

        except Exception as err:
            print(f'\r{" "*cols()}\r{red}{curr} took too long to respond{reset}')

            # If a url is unresponsive remove all its subdirectories from queues
            pos_q = list(filter(lambda x: not x.startswith(curr[:delim]), pos_q))
            neg_q = list(filter(lambda x: not x.startswith(curr[:delim]), neg_q))

            continue


        if len(tosearch) < 30 or any(list(map(lambda x: x in tosearch, blacklist))):
            # print(f'\r{" "*cols()}\r{red}{curr} too small or contains blacklisted token(s){reset}')
            continue

        page_hash = md5(tosearch.encode('utf-8')).hexdigest()
        if page_hash not in list(page_hashes.values()):
            page_hashes[curr] = page_hash
        else:
            continue

        score, _ = calculate_rank(' '.join(query), {'1': tosearch})
        # print(curr, score)

        if score[0] > (0.01+0.01*(depth)):
            # Doing this because after ranking pages we can grab url easily
            data[curr] = curr + ' || ' + remove_html_tags(tosearch)
            complete_urls = set(re.findall(url_regex, tosearch))
            unique_complete = complete_urls - set(visited) - (set(pos_q).union(set(neg_q)))

            subdirs = set(map(lambda x: curr[:delim] + x if x.startswith('/') else curr[:delim] + '/' + x, 
                re.findall(subdir_regex, tosearch)))
            unique_subdirs = subdirs - set(visited) - (set(pos_q).union(set(neg_q)))

            unique = unique_complete.union(unique_subdirs)
            # else:
            #     unique = unique_complete

            # Positive set contains all the url that contain one or more keywords in them
            positive_set = set(filter(lambda x: any(list(keyword in x.lower() for keyword in query)), unique))

            # Everything else goes in negative_set
            negative_set = unique - positive_set

            pos_q.extend(list(positive_set))
            neg_q.extend(list(negative_set))

            if len(unique) > 0:
                if len(negative_set) > 0:
                    clrline()
                    print('\n'.join(list(negative_set)[:30]))
                if len(positive_set) > 0:
                    clrline()
                    print('\n'.join(positive_set))

                children[curr] = [list(positive_set), list(negative_set)]

            else:
                print(f'\r{" "*cols()}\r{red}No links found in {curr}{reset}')

            if assign_ranks() == 1:
                continue


if __name__ == '__main__':
    cols = lambda: shutil.get_terminal_size().columns
    clrline = lambda : print('\r' + ' '*cols() + '\r', end="", flush=True)

    query = list(map(lambda x: x.lower(), [
            'cats'
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
            'webp',
            'jpeg',
            'woff',
            'eot',
            'ttf',
            'zip'
        ])

    url_regex = rf'((?:https?:\/\/)\w+.onion\/?(?!\S+?(?:{banned_types}))[\w\/\-%\.\?]*\/?)'
    subdir_regex = r'<a href="(\/?\S+(?:html|php)\?.*?)"'

    visited = []
    page_hashes = {}
    children = {}
    data = {}
    prevscores = [0]

    depth = 0
    locked = False
    should_exit = False

    # Must do this if you want colours to work on windows
    iswin = sys.platform.startswith('win')
    if iswin:
        os.system('color')

    green = '\x1b[32m'
    red = '\x1b[31m'
    yellow = '\x1b[33m'
    reset = '\x1b[0m'

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    host = socket.getaddrinfo('127.0.0.1', 9050)
    status = sock.connect_ex(host[-1][4])
    if status != 0:
        print(f'{red}Tor proxy not found on port 9050, aborting{reset}')
        should_exit = True
        exit(0)

    # Clear results file
    open('results.txt', 'w').close()

    # Load blacklist
    blacklist = []
    with open('blacklist.txt') as f:
        for line in f:
            blacklist.append(b64decode(line).decode())

    if any(list(word in query for word in blacklist)):
        print(f'{yellow}Blacklist disabled because query contains blacklisted token{reset}')
        blacklist = []

    # Use search engine results for query as starting urls for crawler
    print(f'{yellow}Grabbing results from phobos{reset}')
    neg_q = []
    for i in range (1,4):
        url = f"http://phobosxilamwcg75xt22id7aywkzol6q6rfl2flipcqoc4e4ahima5id.onion/search?query={'+'.join(query)}&p={i}"
        headers = {
                'Referer': url
            }
        phobos_page = get(url, 
            proxies={
                'http':'socks5h://localhost:9050',
                'https':'socks5h://localhost:9050'
            },
            headers = headers,
            timeout=10).text
        neg_q.extend(re.findall('<a class="titles" href="(.*?)"', phobos_page))

    print(f'{yellow}Grabbing results from ahmia{reset}')
    url = f"https://ahmia.fi/search/?q={'+'.join(query)}"
    ahmia_page = get(url).text
    neg_q.extend(re.findall(r'redirect_url=(.*?)">', ahmia_page))

    pos_q = []

    threads=[]
    for _ in range(6):
        threads.append(threading.Thread(target=main))
        threads[-1].start()
