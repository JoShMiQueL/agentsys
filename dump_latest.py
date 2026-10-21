import sqlite3, sys, json
sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect(r'C:\Users\Josemi\.local\share\opencode\opencode.db')
rows = db.execute(
    "SELECT id, parent_id, agent, model, title, time_created, time_updated, tokens_input, tokens_output FROM session_v2 ORDER BY time_created DESC LIMIT 6"
).fetchall()
for r in rows:
    m = json.loads(r[3]) if r[3] else {}
    print(f"{r[0][:24]} parent={(r[1] or '-')[:24]} agent={r[2]} model={m.get('id')} title={str(r[4])[:50]}")
    print(f"   created={r[5]} updated={r[6]} in={r[7]} out={r[8]}")
    msgs = db.execute(
        "SELECT seq, type, data FROM session_message WHERE session_id=? ORDER BY seq DESC LIMIT 3", (r[0],)
    ).fetchall()
    for seq, typ, data in msgs:
        d = json.loads(data)
        for p in (d.get('content') or [])[-3:]:
            t = p.get('type')
            if t == 'tool':
                st = p.get('state') or {}
                print(f"   [{typ}] tool={p.get('name') or p.get('tool')} status={st.get('status')} in={str(st.get('input'))[:140]}")
            elif t == 'text':
                print(f"   [{typ}] text: {(p.get('text') or '')[:200]}".replace(chr(10), ' '))
            elif t == 'reasoning':
                print(f"   [{typ}] think: {(p.get('text') or '')[:150]}".replace(chr(10), ' '))
            else:
                print(f"   [{typ}] {t}: {str(p)[:140]}")
