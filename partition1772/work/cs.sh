for s in "$@"; do echo "## $s"; curl -s -G -A "HistoryDocResearch/1.0 (educational)" https://commons.wikimedia.org/w/api.php --data-urlencode action=query --data-urlencode format=json --data-urlencode list=search --data-urlencode srnamespace=6 --data-urlencode srlimit=10 --data-urlencode "srsearch=$s" | python3 -c "import json,sys
try:
  [print('   ',x['title']) for x in json.load(sys.stdin)['query']['search']]
except Exception as e: print('ERR',e)"; sleep 2; done
