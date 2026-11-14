"""Publish synthetic knowledge on an isolated local demo server and verify visibility."""
import json
import os
import time
import uuid
from urllib.parse import urlsplit
import httpx

if os.getenv('DEMO_SYNTHETIC_CONFIRM') != '1' or not os.getenv('DEMO_ADMIN_PASSWORD'):
    raise SystemExit('Set DEMO_SYNTHETIC_CONFIRM=1 and DEMO_ADMIN_PASSWORD for an isolated demo database')
base = os.getenv('DEMO_BASE_URL', 'http://127.0.0.1:8000')
parsed = urlsplit(base)
if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost'} or parsed.username or parsed.password or parsed.path not in {'', '/'} or parsed.query or parsed.fragment:
    raise SystemExit('Only a local server may be used')
run = uuid.uuid4().hex[:12]
code, title = f'synthetic-{run}', f'合成演示景点{run}'
with httpx.Client(base_url=base, timeout=30) as client:
    login = client.post('/api/auth/login', json={'password': os.environ['DEMO_ADMIN_PASSWORD']}); login.raise_for_status()
    headers = {'Authorization': 'Bearer ' + login.json()['token']}
    payload = {'title': title, 'category': '景点信息', 'aliases': [title], 'content': f'{title}是虚构的本地演示景点，仅用于验证知识发布与游客检索。', 'source': '本机合成演示资料，非真实景区信息', 'metadata_json': json.dumps({'attraction_id': code})}
    response = client.post('/api/knowledge/', headers=headers, json=payload); response.raise_for_status(); entry = response.json()
    before = client.get('/api/guide/bootstrap'); before.raise_for_status()
    assert code not in [row['spot_code'] for row in before.json().get('catalog', [])]
    response = client.post('/api/knowledge-publications/', headers=headers, json={'idempotency_key': f'demo-{run}', 'items': [{'entry_id': entry['id'], 'revision_id': entry['draft_revision_id'], 'expected_version': entry['lock_version']}]}); response.raise_for_status(); job_id = response.json()['id']
    for _ in range(90):
        response = client.get(f'/api/knowledge-publications/{job_id}', headers=headers); response.raise_for_status(); job = response.json()
        if job['state'] in {'succeeded', 'failed'}: break
        time.sleep(.5)
    assert job['state'] == 'succeeded', job
    catalog = client.get('/api/guide/bootstrap'); catalog.raise_for_status()
    matches = [row for row in catalog.json().get('catalog', []) if row['spot_code'] == code]
    assert len(matches) == 1 and matches[0]['published_revision_id'] == entry['draft_revision_id']
    response = client.post('/api/chat/stream', json={'query': f'{title}是什么？', 'session_id': f'demo-{run}', 'text_only': True}); response.raise_for_status()
    events = []
    for block in response.text.replace('\r\n', '\n').split('\n\n'):
        lines = block.splitlines(); kind = next((x[7:] for x in lines if x.startswith('event: ')), None); data = next((x[6:] for x in lines if x.startswith('data: ')), None)
        if kind and data: events.append((kind, json.loads(data)))
    sources = [doc for kind, body in events if kind == 'sources' for doc in body.get('docs', [])]
    assert any(doc.get('revision_id') == entry['draft_revision_id'] and doc.get('source') == payload['source'] for doc in sources), sources
    assert any(kind == 'done' for kind, _ in events)
    print('PASS: draft hidden; publication succeeded; tourist catalog and answer reference published revision (synthetic data)')
