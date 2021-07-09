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
    scores, pages = search(query, df)
    return scores, list(map(lambda x: x.tolist()[0][0], pages))

def main():
    """ Actual searcher """
    global visited,    \
        prevscores,    \
        data,          \
        children,      \
        locked,        \
        depth_counter, \
        should_exit,   \
        pos_q,         \
        neg_q

    cols = lambda: shutil.get_terminal_size().columns
    clrline = lambda : print('\r' + ' '*cols() + '\r', end="", flush=True)
    q_len = lambda: len(pos_q) + len(neg_q)
    print_status = lambda: print((f'\r{" "*cols()}\r{green}Depth: {depth_counter}  Queued: {q_len()}  '
        f'Searched: {len(data)}  Current: {curr[:70]+"..." if len(curr)>75 else curr}{reset}'), end='', flush=True)

    while True:

        if should_exit:
            exit(0)

        while q_len() == 0 or locked:
            sleep(0.1)

        if len(pos_q) > 0:
            curr = pos_q.pop(0)
            timeout = 10
        else:
            curr = neg_q.pop(0)
            timeout = 8

        print_status()

        delim = curr.index('onion') + 5

        # if subdirs of site have been visited more than 20 times then dont visit site
        # again
        if len(list(filter(lambda x: x.startswith(curr[:delim]), visited))) < 20:
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

            if len(tosearch) > 30:
                # Doing this because after ranking pages we can grab url easily
                data[curr] = curr + ' || ' + remove_html_tags(tosearch)
            else:
                continue

        except Exception as err:
            print(f'\r{" "*cols()}\r{red}{curr} took too long to respond{reset}')

            # If a url is unresponsive remove all its subdirectories from queues
            pos_q = list(filter(lambda x: not x.startswith(curr[:delim]), pos_q))
            neg_q = list(filter(lambda x: not x.startswith(curr[:delim]), neg_q))

            continue

        complete_urls = set(re.findall(url_regex, tosearch))
        unique_complete = complete_urls - set(visited) - (set(pos_q).union(set(neg_q)))

        score, _ = rank_data(' '.join(query), {'1': tosearch})
        # print(f"score for {curr}:", score)

        if score[0] > 0.07:
            subdirs = set(map(lambda x: curr[:delim] + x if x.startswith('/') else curr[:delim] + '/' + x, 
                re.findall(subdir_regex, tosearch)))
            unique_subdirs = subdirs - set(visited) - (set(pos_q).union(set(neg_q)))

            unique = unique_complete.union(unique_subdirs)
        else:
            unique = unique_complete

        positive_set = set(filter(lambda x: any(list(keyword in x.lower() for keyword in query)), unique))
        negative_set = unique - positive_set

        pos_q.extend(list(positive_set))
        neg_q.extend(list(negative_set)[:10])


        if len(unique) > 0:
            if len(negative_set) > 0:
                clrline()
                print('\n'.join(list(negative_set)[:10]))
            if len(positive_set) > 0:
                print('\n'.join(positive_set))
                
            children[curr] = [list(positive_set), list(negative_set)]

        else:
            print(f'\r{" "*cols()}\r{red}No links found in {curr}{reset}')

        if not locked and len(data) > 60:
            locked = True

            date_copy = data.copy()
            scores, sorted_pages = rank_data(' '.join(query), date_copy)

            if depth_counter == 1:
                prevscores = scores
            else:
                if scores[0] < prevscores[0]:
                    clrline()
                    print(f'{red}Better results in previous depth, exiting{reset}')
                    should_exit = True
                    exit(0)

            data = {}

            try:
                sorted_urls = list(map(lambda x: x[:x.index(' || ')], sorted_pages))
            except Exception:
                print(f'\r{" "*cols()}\r{red}|| ERROR{reset}')
                print(sorted_urls)
                locked = False
                continue

            separator = '\n' + ' ' * 24
            toprint = separator.join(sorted_urls[:5])

            clrline()
            depth_counter += 1
            print(f'{yellow}\nBest result at depth {depth_counter}: {toprint}{reset}\n')

            with open('results.txt', 'a') as f:
                a = sorted_pages[0].index(' || ')
                b = sorted_pages[1].index(' || ')
                f.write((f'{depth_counter}. {sorted_urls[0]} - {sorted_pages[0][a+6:a+56]}\n'
                        f'{depth_counter}. {sorted_urls[1]} - {sorted_pages[1][b+6:b+56]}\n\n'))

            for url in reversed(sorted_urls[:3]):
                # If url has children shift all children to beginning of q
                if url in children:
                    pos_q = children[url][0] + pos_q
                    neg_q = children[url][1][:20] + neg_q
                else:
                    print(f'{url} has no children')

            locked = False

if __name__ == '__main__':
    query = list(map(lambda x: x.lower(), [
            'flipkart',
            'data leak',
            'leaked',
            'cybercrime',
            'hacking',
        ]))

    # query = list(map(lambda x: x.lower(), [
    #         "dominos",
    #         'leak',
    #     ]))


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
            'zip',
            'xmlrpc.php'
        ])

    url_regex = rf'((?:https?:\/\/)\w+.onion\/?(?!\S+?(?:{banned_types}))[\w\/\-%\.\?]*\/?)'
    subdir_regex = r'<a href="(\/?\S+(?:html|php)\?.*?)"'

    visited = []
    children = {}
    data = {}
    prevscores = [0]

    depth_counter = 0
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

    url = f"https://ahmia.fi/search/?q={'+'.join(query)}"
    engine_page = get(url).text
    neg_q = re.findall(r'redirect_url=(.*?)">', engine_page)
    pos_q = []

    threads=[]
    for _ in range(6):
        threads.append(threading.Thread(target=main))
        threads[-1].start()
