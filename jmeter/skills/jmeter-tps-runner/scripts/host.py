"""Durable question outbox. A queued item is not evidence of UI display."""
from pathlib import Path
from .storage import write_new, atomic_json


def enqueue(root, question_id, title, *, simulated=False):
    folder=Path(root)/'questions';folder.mkdir(exist_ok=True)
    item={'id':question_id,'title':title,'simulated':simulated,'status':'queued',
          'queue_continues':True,'user_response':None}
    write_new(folder/(question_id+'.json'),item)
    return item


def acknowledge(root, question_id, receipt, response=None):
    import json
    if not receipt: raise ValueError('Host tool receipt required')
    folder=Path(root)/'questions'
    if Path(question_id).name != question_id or any(c in question_id for c in '/\\:'):
        raise ValueError('Invalid question id')
    path=folder/(question_id+'.json')
    item=json.loads(path.read_text(encoding='utf-8'))
    item.update(status='answered' if response is not None else 'submitted-to-host',
                host_receipt=receipt,user_response=response)
    # submitted-to-host does not claim the human has seen or answered it.
    atomic_json(path,item)
    return item
