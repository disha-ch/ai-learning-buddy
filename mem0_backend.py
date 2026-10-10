"""Mem0 OSS 2.2.1 adapter for the notebook's semantic-memory interface.

Mem0 owns extraction, deduplication, updates, retrieval and history.
The store facade is only for the notebook inspector/export interface.
"""
import os
os.environ.setdefault('MEM0_TELEMETRY','false')
import copy
import tempfile
from pathlib import Path
from mem0 import Memory

class Mem0Store:
    def __init__(self, owner): self.owner=owner
    @property
    def rows(self):
        records=self.owner.client.get_all(filters={'user_id':'maya'},top_k=1000)['results']
        return {r['id']:{'id':r['id'],'text':r['memory'],'vec':[], 'meta':{
            **(r.get('metadata') or {}),'user_id':'maya','status':'active',
            'created_at':r.get('created_at'),'updated_at':r.get('updated_at'),
            'backend':'mem0'}} for r in records}
    @rows.setter
    def rows(self, value):
        self.owner.client.delete_all(user_id='maya')
        for r in value.values():
            self.owner.client.add(r['text'],user_id='maya',infer=False,
                                  metadata={k:v for k,v in r['meta'].items() if k not in ('user_id',)})
    def all(self,where=None):
        return [r for r in self.rows.values() if not where or all(r['meta'].get(k)==v for k,v in where.items())]
    def delete_where(self,where):
        if where != {'user_id':'maya'}: return 0
        n=len(self.rows); self.owner.client.delete_all(user_id='maya'); self.owner.events.clear(); return n

class Mem0Semantic:
    def __init__(self,key,model,embedding):
        self.directory=Path(tempfile.mkdtemp(prefix='maya_mem0_'))
        self.events=[]
        self.client=Memory.from_config({
            'llm':{'provider':'openai','config':{'model':model,'api_key':key,
                'openai_base_url':'https://openrouter.ai/api/v1','temperature':0}},
            'embedder':{'provider':'openai','config':{'model':embedding,'api_key':key,
                'openai_base_url':'https://openrouter.ai/api/v1','embedding_dims':1536}},
            'vector_store':{'provider':'qdrant','config':{'collection_name':'maya_semantic',
                'path':str(self.directory/'qdrant'),'embedding_model_dims':1536,'on_disk':True}},
            'history_db_path':str(self.directory/'history.db'),
        })
        self.store=Mem0Store(self)
    def __deepcopy__(self,memo):
        # SQLite/Qdrant clients cannot be deep-copied. Mem0 writes are durable
        # and cannot be rolled back with a Python object snapshot.
        return self
    def upsert(self,user_id,fact,category='general'):
        if user_id!='maya': raise ValueError('This lab supports Maya only')
        result=self.client.add([{'role':'user','content':fact}],user_id=user_id,
                               metadata={'category':category,'memory_type':'semantic'})
        self.events.append({'operation':'mem0.add','input':fact,'result':copy.deepcopy(result)})
        changes=result.get('results',[])
        return {'action':','.join(str(r.get('event','MEM0')) for r in changes) or 'NOOP',
                'result':result}
    def render(self,user_id,query=None,k=6):
        if user_id!='maya': return []
        if query:
            result=self.client.search(query,filters={'user_id':user_id},top_k=k)
            operation='mem0.search'
        else:
            result=self.client.get_all(filters={'user_id':user_id},top_k=1000)
            operation='mem0.get_all'
        self.events.append({'operation':operation,'query':query,'result':copy.deepcopy(result)})
        return [r['memory'] for r in result['results']]
    def history(self,user_id):
        return [{'id':r['id'],'events':self.client.history(r['id'])} for r in self.store.all({'user_id':user_id})]
