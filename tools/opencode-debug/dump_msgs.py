import sqlite3, sys, json
sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect(r'C:\Users\Josemi\.local\share\opencode\opencode.db')
for sid in ['ses_e9fe5102bffejRFe7gs73tGnc7', 'ses_e9fe5a014ffeit0jt5oxpUj3aQ']:
    print(f'=== {sid} ===')
    rows = db.execute(
        'SELECT seq, type, data FROM session_message WHERE session_id=? ORDER BY seq', (sid,)
    ).fetchall()
    print(f'{len(rows)} messages')
    for seq, typ, data in rows[-14:]:
        d = json.loads(data)
        parts = d.get('content') or []
        for p in parts:
            t = p.get('type')
            if t == 'text':
                print(f'  [{typ}] TEXT: {(p.get("text") or "")[:500]}'.replace(chr(10), ' '))
            elif t == 'reasoning':
                print(f'  [{typ}] think: {(p.get("text") or "")[:200]}'.replace(chr(10), ' '))
            elif t == 'tool_call':
                print(f"  [{typ}] CALL {p.get('name')}: {str(p.get('input') or p.get('args'))[:200]}")
            elif t == 'tool_result':
                out = str(p.get('output') or p.get('result') or '')[:200]
                print(f'  [{typ}] RESULT: {out}'.replace(chr(10), ' '))
            else:
                print(f'  [{typ}] {t}: {str(p)[:150]}')
        err = d.get('error')
        if err:
            print(f'  ERROR: {str(err)[:300]}')
