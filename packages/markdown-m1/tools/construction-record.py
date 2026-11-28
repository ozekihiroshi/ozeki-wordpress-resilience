"""Development-only, local construction record. Not an S3 format or live hook.

Record the operation BEFORE executing it; append a confirmation AFTER success.
References are supplied by the caller at construction time, never inferred from DB.
An unresolved attempt blocks replay. No automatic retry or reconstruction repair.
"""
import copy
import json
import os
from pathlib import Path


class ConstructionRecord:
    schema = 'owr-local-construction-experiment-1'

    def __init__(self, path, dispatch):
        self.path = Path(path)
        self.dispatch = dispatch
        self.outputs = {}
        self.sequence = 0
        self.stopped = False
        with self.path.open('x', encoding='utf-8') as f:
            f.write(json.dumps({'schema': self.schema}) + '\n')

    def append(self, item):
        with self.path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            f.flush()
            os.fsync(f.fileno())

    @staticmethod
    def resolve(value, outputs):
        if isinstance(value, dict):
            if set(value) == {'ref'}:
                key, member = value['ref'].split('.', 1)
                if key not in outputs or member not in outputs[key]:
                    raise ValueError('Unconfirmed prior reference: ' + value['ref'])
                return copy.deepcopy(outputs[key][member])
            if set(value) == {'text'}:
                return ''.join(str(ConstructionRecord.resolve(v, outputs)) for v in value['text'])
            return {k: ConstructionRecord.resolve(v, outputs) for k, v in value.items()}
        if isinstance(value, list):
            return [ConstructionRecord.resolve(v, outputs) for v in value]
        return copy.deepcopy(value)

    def execute(self, key, operation, inputs):
        if self.stopped or key in self.outputs:
            raise ValueError('Stopped or duplicate operation; do not retry blindly')
        resolved = self.resolve(inputs, self.outputs)
        self.sequence += 1
        self.append({'event': 'attempt', 'sequence': self.sequence, 'key': key,
                     'operation': operation, 'inputs': inputs, 'submitted': resolved})
        self.stopped = True
        result = self.dispatch(operation, copy.deepcopy(resolved))
        if not isinstance(result, dict):
            raise ValueError('Operation confirmation must be an object')
        self.append({'event': 'confirmed', 'sequence': self.sequence, 'key': key, 'result': result})
        self.outputs[key] = copy.deepcopy(result)
        self.stopped = False
        return result

    @classmethod
    def replay(cls, source, destination, dispatch):
        lines = [json.loads(s) for s in Path(source).read_text(encoding='utf-8').splitlines()]
        if not lines or lines.pop(0) != {'schema': cls.schema} or len(lines) % 2:
            raise ValueError('Incomplete or unknown construction record')
        # Validate the complete source before performing ANY target operation.
        outputs = {}
        operations = []
        for n in range(0, len(lines), 2):
            a, c = lines[n:n+2]
            if (a.get('event') != 'attempt' or c.get('event') != 'confirmed'
                or a['sequence'] != n // 2 + 1 or c['sequence'] != a['sequence']
                or c['key'] != a['key'] or a['key'] in outputs
                or cls.resolve(a['inputs'], outputs) != a['submitted']):
                raise ValueError('Invalid construction order/confirmation/input')
            outputs[a['key']] = c['result']
            operations.append(a)
        target = cls(destination, dispatch)
        for a in operations:
            target.execute(a['key'], a['operation'], a['inputs'])
        return target
