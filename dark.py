#!/usr/bin/env python3
from requests import get
import threading
import re

# url_regex = r'(?:(?:https?|ftp):\/\/)[\w/\-?=%.]+\.[\w/\-&?=%.]+'
# url_regex = r'(?:(?:https?|ftp):\/\/)[\w/\-%.]+\.[\w/\-&%.]+'
url_regex = [r'(?:(?:https?|ftp|irc):\/\/)\w+.onion\/?[\w/\-%.]*\/?',r'<a href="(\/\S*?html)">']
url = 'http://darkfailllnkf4vf.onion/'

clrline = lambda : print('\r'+' '*20+'\r',end="",flush=True)

q=[url]
visited = []

def main():
    global q, visited
    while len(q)!=0:
        curr = q.pop(0)

        if curr not in visited:
            visited.append(curr)
        else:
            continue

        try:
            tosearch = get(curr, 
                    proxies={'http':'socks5h://localhost:9050',
                            'https':'socks5h://localhost:9050'},
                    timeout=8).text
        except Exception as err:
            clrline()
            print(f"nothing in {curr}")
            print(f'Count: {len(q)}',end="",flush=True)

            continue

        children = set()
        for regex in url_regex:
            children = children.union(set(re.findall(regex, tosearch)))

        children = list(map(lambda x: curr[:curr.index('.onion')+6]+x if\
                x.startswith('/') else x, children))
        unique = list(filter(lambda x: x not in q,
                children))

        if len(unique)>0:
            q.extend(unique)
            clrline()
            print('\n'.join(unique))
            print(f'Count: {len(q)}', end="", flush=True)

threads=[]
for _ in range(100):
    threads.append(threading.Thread(target=main))
    threads[-1].start()
