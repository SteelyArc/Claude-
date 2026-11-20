import sys, json, urllib.parse, urllib.request
def q(s, n=12):
    u='https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode({'action':'query','format':'json','list':'search','srnamespace':6,'srlimit':n,'srsearch':s})
    r=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'doc-research-bot/1.0'})))
    return [x['title'] for x in r['query']['search']]
for s in sys.argv[1:]:
    print('##',s); [print('  ',t) for t in q(s)]
