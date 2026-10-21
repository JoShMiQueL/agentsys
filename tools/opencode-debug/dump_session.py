import json, sys
sys.stdout.reconfigure(encoding='utf-8')
d = json.load(sys.stdin)
sessions = d if isinstance(d, list) else [d]
for s in sessions:
    sid = (s.get('id') or (s.get('session') or {}).get('id'))
    print('SESSION', sid)
    msgs = s.get('messages') or (s.get('session') or {}).get('messages') or []
    for m in msgs[-30:]:
        role = m.get('role') or (m.get('info') or {}).get('role', '?')
        for p in (m.get('parts') or [])[-5:]:
            t = p.get('type')
            if t == 'text':
                txt = (p.get('text') or '')[:400].replace('\n', ' ')
                print(f'  [{role}] text: {txt}')
            elif t == 'tool':
                st = p.get('state') or {}
                print(f"  [{role}] tool={p.get('tool')} status={st.get('status')} input={str(st.get('input'))[:160]}")
                err = st.get('error')
                if err:
                    print(f'       ERROR: {str(err)[:300]}')
            elif t == 'subtask' or t == 'task':
                print(f'  [{role}] {t}: {str(p)[:250]}')
            elif t:
                print(f'  [{role}] {t}: {str(p)[:120]}')
