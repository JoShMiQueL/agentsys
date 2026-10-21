import sqlite3, sys, json
sys.stdout.reconfigure(encoding='utf-8')
db = sqlite3.connect(r'C:\Users\Josemi\.local\share\opencode\opencode.db')
tables = [r[0] for r in db.execute("select name from sqlite_master where type='table'")]
print('TABLES:', tables)
for t in tables:
    if 'session' in t.lower():
        cols = [c[1] for c in db.execute(f'PRAGMA table_info({t})')]
        print(f'\n{t} cols: {cols}')
        try:
            for row in db.execute(f'SELECT * FROM {t} ORDER BY rowid DESC LIMIT 5'):
                print(' ', str(row)[:400])
        except Exception as e:
            print('  err', e)
