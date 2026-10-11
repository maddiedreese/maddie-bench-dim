"""Persistent conservative spend reservations, shared across development runs."""
import json
import time
import uuid
from pathlib import Path
from filelock import FileLock

class BudgetExceeded(RuntimeError):
    pass

class Budget:
    # Deliberately use the highest published Astra Standard rates, including
    # long-context cache writes; these are ceilings, not exact invoice costs.
    INPUT_PER_MILLION=25.
    OUTPUT_PER_MILLION=75.
    def __init__(self,path:Path,limit=100.):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.limit=min(float(limit),100.)
        if not 0<self.limit<=100:raise ValueError('Budget must be within (0,100] USD')
        self.lock=FileLock(str(path)+'.lock')

    def read(self):
        return json.loads(self.path.read_text()) if self.path.exists() else {'entries':[]}

    def save(self,data):
        tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2));tmp.replace(self.path)

    def reserve(self,input_bound,output_bound):
        amount=(input_bound*self.INPUT_PER_MILLION+output_bound*self.OUTPUT_PER_MILLION)/1e6
        with self.lock:
            data=self.read()
            if sum(e['reserved_usd'] for e in data['entries'])+amount>self.limit:
                raise BudgetExceeded('Project API budget exhausted; no request sent')
            token=str(uuid.uuid4())
            data['entries'].append({'id':token,'time':time.time(),'reserved_usd':amount,'status':'pending'})
            self.save(data)
        return token

    def settle(self,token,input_tokens,output_tokens):
        with self.lock:
            data=self.read()
            for e in data['entries']:
                if e['id']==token:
                    amount=(input_tokens*self.INPUT_PER_MILLION+output_tokens*self.OUTPUT_PER_MILLION)/1e6
                    if amount>e['reserved_usd']:raise BudgetExceeded('Usage exceeded conservative reservation; stop and audit')
                    e.update(reserved_usd=amount,status='completed',input_tokens=input_tokens,output_tokens=output_tokens)
                    break
            self.save(data)

    def total(self):
        with self.lock:return sum(e['reserved_usd'] for e in self.read()['entries'])
