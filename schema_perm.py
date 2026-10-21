import json, urllib.request, sys
sys.stdout.reconfigure(encoding='utf-8')
req = urllib.request.Request('https://opencode.ai/config.json', headers={'User-Agent': 'opencode/2.0'})
d = json.load(urllib.request.urlopen(req, timeout=20))
defs = d.get('$defs') or {}
for k, v in defs.items():
    if 'Permission' in k or 'Polic' in k:
        print('---', k, ':', json.dumps(v, ensure_ascii=False)[:1500])
props = d.get('properties', {})
for k in ('permissions', 'policies', 'permission'):
    if k in props:
        print('TOP', k, ':', json.dumps(props[k], ensure_ascii=False)[:800])
