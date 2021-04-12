#!/usr/bin/env python3
from requests import get
import threading
import re

url_regex = r'(?:(?:https?|ftp|irc):\/\/)\w+.onion\/?[\w/\-%.]*\/?'
subdir_regex = r'<a href="(\/\S*?html)">'

clrline = lambda : print('\r'+' '*20+'\r', end="", flush=True)

# List of active/sem-active forums from pastebin
# to start from
q=[ "http://cavetord6bosm3sl.onion/",
    "http://cardshopffielsxi.onion/",
    "http://s6cco2jylmxqcdeh.onion/",
    "http://z2hjm7uhwisw5jm5.onion/",
    "http://zw3crggtadila2sg.onion/",
    "http://rrcc5uuudhh4oz3c.onion/",
    "http://3mrdrr2gas45q6hp.onion:2000/",
    "http://thundersplv36ecb.onion/",
    "http://76qugh5bey5gum7l.onion/",
    "http://koi6xzo34wxxvs6m.onion/",
    "http://torpress2sarn7xw.onion/" ]
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
            continue


        children = {'new': set(), 'subdirs': set()}
        new_urls = set(re.findall(url_regex, tosearch))
        delim = curr.index('onion')+6
        subdirs = set(map(lambda x: curr[:delim]+x, 
                re.findall(subdir_regex, tosearch)))

        children[0] = new_urls
        children[1] = subdirs

        unique_new = children[0] - set(q)
        unique_subdirs = children[1] - set(q)
        unique = unique_new.union(unique_subdirs)

        if len(unique)>0:
            clrline()
            # print('\n'.join(unique_subdirs))
            print('\n'.join(unique_new))
            q.extend(unique)
            if tosearch.count('message')+tosearch.count('forum')+tosearch.count('post')>5:
                print(f'\x1b[32mPossible Forum: {curr}\x1b[0m')
            print(f'Found URLs: {len(q)}', end="", flush=True)

threads=[]
for _ in range(100):
    threads.append(threading.Thread(target=main))
    threads[-1].start()
