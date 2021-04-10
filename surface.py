#!/usr/bin/env python3
from requests import get
import re

# url_regex = r'(?:(?:https?|ftp):\/\/)[\w/\-?=%.]+\.[\w/\-&?=%.]+'
# url_regex = r'(?:(?:https?|ftp):\/\/)[\w/\-%.]+\.[\w/\-&%.]+'
url_regex = r'(?:(?:https?|ftp|irc):\/\/)[\w/\-%.]+\/'
url = 'http://google.com'

clrline = lambda : print('\r'+' '*10+'\r',end="",flush=True)

q=[url]
visited = []
while len(q)!=0:
    curr = q.pop(0)

    if curr not in visited:
        visited.append(curr)
    else:
        continue

    try:
        tosearch = get(curr).text
    except:
        print(curr)
        continue

    children = set(re.findall(url_regex, tosearch))

    if len(children)>0:
        q.extend(children)
        clrline()
        print('\n'.join(children))
        print(f'Count: {len(q)}',end="",flush=True)

    if len(q)+len(visited)>1000:
        print('\nFound enough sites. Exiting...')
        exit()
