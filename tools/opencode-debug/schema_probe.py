import json, urllib.request, sys
sys.stdout.reconfigure(encoding='utf-8')
req = urllib.request.Request('https://opencode.ai/config.json', headers={'User-Agent': 'opencode/2.0'})
d = json.load(urllib.request.urlopen(req, timeout=20))
defs = d.get('$defs') or {}
for k, v in defs.items():
    if 'Agent' in k:
        print('---', k, ':', json.dumps(v, ensure_ascii=False)[:1200])
