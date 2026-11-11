import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'))
for k,v in r.items():
    if k in ('logs','tlw','ticks'): continue
    print(f"{k}: {v}")
for l in r.get('logs',[]): print('--- op log tail:', l.strip()[-300:].replace('\n',' | '))
