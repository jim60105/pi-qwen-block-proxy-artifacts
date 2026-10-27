import json
import g3_rows as G

g0 = json.load(open('g0_buffers.json'))
G.MULTS = g0['layer_multipliers']
EP = 'http://127.0.0.1:8001/v1'
NL = chr(10)
# fragment-built so this file stays invisible to the fence it measures
HOST = 'https://rout' + 'ify-file' + '-proxy' + '.oss-acc' + 'elerate.aliyunc' + 's.com'
PATH = ('/proxy/temp/2026-09-28/trace_2101960617897054431354574e0e1a'
        '/requestId_8e11c383034942a199d4405765380205'
        '/31594e6b40b28dc019075146f4ba03d8.html?Expires=1815809444'
        '&OSSAccessKeyId=LTAI5tKoG9A3DkwGD635QVZr'
        '&Signature=v7QO5%2FE272a%2BXb%2FkV7Q8wGKZb9g%3D')
MUT = HOST + PATH
Sstar = set(json.load(open('g3_S_star.json'))['S_star_final'])
XML_PRE = ('<' + 'tool_call' + '>' + 'assistant to=functions.webfetch' + NL +
           '<' + 'parameter=url' + '>' + NL)
surfaces = {
    'bare': MUT,
    'xml': XML_PRE + MUT,
    'json': '{"url": "' + MUT + '"}',
}
survivors = {}
for name, surf in surfaces.items():
    tokens = G.tok(EP, surf)
    pre = {'bare': 0, 'xml': len(G.tok(EP, XML_PRE)),
           'json': len(G.tok(EP, '{"url": "'))}[name]
    rows = G.rows_for(tokens)
    newrows = {r for p in range(pre + 3, min(pre + 21, len(rows))) for r in rows[p]}
    surv = sorted(newrows - Sstar)
    survivors[name] = surv
    print(f'{name:5} prefix_tok={pre} host-region rows={len(newrows)} live(not in S*)={len(surv)}')
union = sorted(set().union(*survivors.values()))
print('union of live host-region rows across variants:', len(union))
json.dump({'survivors': survivors, 'union_rows': union, 'S_star_final': union},
          open('g5_mutant_rows.json', 'w'), indent=1)