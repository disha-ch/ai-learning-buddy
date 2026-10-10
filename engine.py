"""Adapters and LangGraph orchestration; notebook_core.py stays unchanged."""
import types, json, copy, re
from pathlib import Path
from typing import TypedDict
import requests
from openai import OpenAI
from langgraph.graph import StateGraph, START, END

SAMPLES = [
 "Hi, I'm Maya. I'm a software engineer learning Python to become an AI Engineer.",
 "I studied Python loops yesterday but struggled with nested loops.",
 "Whenever you explain concepts, use simple examples and avoid jargon.",
 "Can you explain Python functions?",
 "What did I struggle with yesterday?",
 "What's the latest stable Python version?",
 "Remind me tomorrow to practice nested loops.",
 "What are we discussing right now?",
 "I've mastered nested loops now!",
]
class Turn(TypedDict, total=False):
 message: str
 reply: str
 nodes: list[str]

class Engine:
 def __init__(self, key, model='openrouter/free', embedding='openai/text-embedding-3-small', backend='notebook'):
  self.c=types.ModuleType('isolated_notebook_core')
  exec(compile(Path(__file__).with_name('notebook_core.py').read_text(),'notebook_core.py','exec'),self.c.__dict__)
  c=self.c
  c.client=OpenAI(api_key=key,base_url='https://openrouter.ai/api/v1',timeout=60,max_retries=1)
  c.CHAT_MODEL=model; c.EMBED_MODEL=embedding
  self.mm=c.MemoryManager()
  self.backend=backend
  if backend=='mem0':
   from mem0_backend import Mem0Semantic
   self.mm.semantic=Mem0Semantic(key,model,embedding)
  self.buddy=c.StudyBuddy(self.mm)
  self.buddy.register_user('maya','Maya',False)
  self.session='s1'; self.events=[]; self.context=''; self.external=[]; self.history=[]
  # Extensions required by Maya's scenario; original notebook definitions stay intact.
  c.COACH_SYSTEM += '\nFor standard Python functions use pretrained knowledge unless external information is needed. Never claim a live lookup without a tool result. Student-specific explanation preferences override generic playbooks.'
  g=StateGraph(Turn)
  for name,fn in [('capture_memory',self.capture),('retrieve_context',self.retrieve),('respond',self.respond),('inspect_changes',self.inspect)]: g.add_node(name,fn)
  g.add_edge(START,'capture_memory'); g.add_edge('capture_memory','retrieve_context'); g.add_edge('retrieve_context','respond'); g.add_edge('respond','inspect_changes'); g.add_edge('inspect_changes',END)
  self.graph=g.compile()
 def snapshot(self):
  return {n:[{k:v for k,v in r.items() if k!='vec'} for r in s.rows.values()] for n,s in self.mm.stores().items()}
 def capture(self,state):
  self.before=copy.deepcopy(self.snapshot()); self.events=[]; self.external=[]; self.buddy.trace=[]
  if self.backend=='mem0': self.mm.semantic.events.clear()
  d=self.c.llm_json('Extract ONLY explicitly stated student memories from this message. JSON keys: facts (list of short third-person facts), episode (string or null: a reported study experience or milestone, preserve relative date), preference (string or null: explicit instruction for HOW to explain). Questions are not memories. A mastered skill is a current fact AND an episode. Do not extract reminders here.',state['message'])
  for f in d.get('facts',[]):
   if isinstance(f,str): self.events.append({'semantic':self.mm.semantic.upsert('maya',f)})
  if isinstance(d.get('episode'),str) and d['episode']:
   rid=self.mm.episodic.record('maya',self.session,d['episode'],tags=['reported experience'])
   self.events.append({'episodic':rid,'recorded_at':self.c.ts(),'event_time':'See relative date in text'})
  if isinstance(d.get('preference'),str) and d['preference']:
   for r in self.mm.procedural.store.all({'user_id':'maya','source':'explicit_preference'}): del self.mm.procedural.store.rows[r['id']]
   self.mm.procedural.learn('Explain any concept to Maya',[d['preference']],scope='student',user_id='maya',source='explicit_preference')
  return {'nodes':['capture_memory']}
 def retrieve(self,state):
  due=self.mm.prospective.due('maya')
  triggered=self.mm.prospective.triggered_by('maya',state['message'])
  self.context,self.proc_ids=self.buddy.build_context('maya',state['message'])
  self.retrieved={
   'semantic_backend':self.backend,
   'semantic': next((x['result'].get('results',[]) for x in reversed(self.mm.semantic.events) if x['operation']=='mem0.search'),[]) if self.backend=='mem0' else self.mm.semantic.render('maya',state['message']),
   'prospective':{'due_ids':[r['id'] for r in due],'topic_triggered_ids':[r['id'] for r in triggered]},
   'episodic':self.mm.episodic.recall('maya',state['message'],k=2) if self.mm.episodic.count('maya') else [],
   'procedural':[r for r in self.mm.procedural.store.rows.values() if r['id'] in self.proc_ids],
   'working':{'recent_messages':len(self.mm.wm('maya',self.session).turns),'summary':self.mm.wm('maya',self.session).summary},
  }
  # Always apply explicit style; similarity retrieval alone can miss generic preferences.
  prefs=self.mm.procedural.store.all({'user_id':'maya','source':'explicit_preference'})
  self.context+='\n## EXPLICIT EXPLANATION PREFERENCES\n'+'\n'.join(self.c.ProceduralMemory.fmt(r) for r in prefs)
  self.proc_ids=list(set(self.proc_ids+[r['id'] for r in prefs]))
  return {'nodes':state['nodes']+['retrieve_context']}
 def latest_python(self):
  url='https://www.python.org/api/v2/downloads/release/?is_published=true'
  try:
   response=requests.get(url,timeout=20); response.raise_for_status(); data=response.json()
   rows=data if isinstance(data,list) else data.get('results',[])
   versions=[]
   for r in rows:
    name=r.get('name','')
    if re.fullmatch(r'Python 3\.\d+\.\d+',name) and not r.get('pre_release',False): versions.append((tuple(map(int,name.split()[1].split('.'))),name))
   if not versions: raise ValueError('No stable releases returned')
   result={'latest_stable':max(versions)[1],'source':url,'retrieved_at':self.c.datetime.now().isoformat()}
   self.mm.external.ingest('Python.org live release lookup',json.dumps(result)); self.external.append(result)
   return json.dumps(result)
  except Exception:
   return 'Live Python.org lookup failed. Do not guess the latest version; say it could not be verified.'
 def respond(self,state):
  c=self.c; wm=self.mm.wm('maya',self.session)
  tools=self.buddy.tools_for('maya')+[c.Tool('latest_python_version','Fetch current latest stable Python release from official Python.org. MUST use for latest version questions.',{},self.latest_python)]
  messages=[{'role':'system','content':c.COACH_SYSTEM+'\nToday (simulated): '+c.ts()+'\n'+self.context},*wm.messages(),{'role':'user','content':state['message']}]
  def log(n,a,r): self.events.append({'tool':n,'arguments':a,'result':str(r)})
  reply=c.run_agent(messages,tools,on_tool=log) or 'The model returned no text; please retry.'
  wm.add('user',state['message']); wm.add('assistant',reply)
  self.buddy.last_turn[('maya',self.session)]={'user':state['message'],'assistant':reply,'procs':self.proc_ids}
  self.history.extend([{'role':'user','content':state['message']},{'role':'assistant','content':reply}])
  return {'reply':reply,'nodes':state['nodes']+['respond']}
 def inspect(self,state):
  after=self.snapshot(); self.delta={k:{'before':self.before[k],'after':v} for k,v in after.items() if self.before[k]!=v}
  self.events.extend({'read':x} for x in self.buddy.trace)
  if self.backend=='mem0': self.events.extend(copy.deepcopy(self.mm.semantic.events))
  self.usage={
   'Working':f"{self.retrieved['working']['recent_messages']} prior message(s); current question included",
   'Semantic':f"{len(self.retrieved['semantic'])} fact(s) retrieved via {self.backend}",
   'Episodic':f"{len(self.retrieved['episodic'])} episode(s) retrieved",
   'Procedural':f'{len(self.proc_ids)} playbook(s)/preference(s) included',
   'External':'Tool called' if any(x.get('tool') in ('latest_python_version','search_course_material') for x in self.events) else 'No external tool called',
   'Prospective':f"Due check: {len(set(self.retrieved['prospective']['due_ids']+self.retrieved['prospective']['topic_triggered_ids']))} reminder(s) surfaced; "+('new reminder tool called' if any(x.get('tool')=='set_reminder' for x in self.events) else 'no reminder tool call'),
   'Parametric':'Pretrained model generated answer; weights unchanged',
  }
  self.history[-1]['memory_usage']=copy.deepcopy(self.usage)
  self.history[-1]['memory_events']=copy.deepcopy(self.events)
  self.nodes=state['nodes']+['inspect_changes']
  return {'nodes':self.nodes}
 def turn(self,message):
  # Commit a complete turn, or roll all memory mutations back on API failure.
  backup=copy.deepcopy((self.mm,self.buddy.last_turn,self.history))
  try: return self.graph.invoke({'message':message})['reply']
  except Exception:
   self.mm,self.buddy.last_turn,self.history=backup; self.buddy.mm=self.mm
   raise
 def end_session(self):
  if not self.mm.wm('maya',self.session).full: return {}
  result=self.buddy.end_session('maya',self.session)
  self.session='s'+self.c.uuid.uuid4().hex[:8]; self.history=[]
  return result
 def export(self):
  return json.dumps({'format':1,'stores':{n:list(s.rows.values()) for n,s in self.mm.stores().items()},'clock':self.c.ts(),'consent':self.c.CONSENT,'names':self.mm.names,'audit':self.mm.param.audit,'embedding_model':self.c.EMBED_MODEL,'backend':self.backend},indent=2)
 def restore(self,data):
  d=json.loads(data)
  if d.get('format')!=1 or d.get('backend','notebook')!=self.backend or d['embedding_model']!=self.c.EMBED_MODEL: raise ValueError('Snapshot format or embedding model mismatch')
  expected=set(self.mm.stores())
  if set(d['stores'])!=expected: raise ValueError('Incomplete snapshot')
  for n,rows in d['stores'].items():
   if not isinstance(rows,list) or any(not all(k in r for k in ('id','text','vec','meta')) for r in rows): raise ValueError('Invalid memory rows')
  for n,s in self.mm.stores().items(): s.rows={r['id']:r for r in d['stores'][n]}
  self.c.CLOCK.t=self.c.datetime.fromisoformat(d['clock']); self.c.CONSENT.clear(); self.c.CONSENT.update(d['consent']); self.mm.names=d['names']; self.mm.param.audit=d['audit']
  self.mm.working.clear(); self.history=[]; self.buddy.last_turn.clear()
  self.context=''; self.events=[]; self.delta={}; self.external=[]; self.usage={}; self.retrieved={}
 def forget(self):
  self.c.forget_user(self.mm,'maya'); self.mm.working.clear(); self.history=[]; self.buddy.last_turn.clear(); self.events=[]; self.context=''; self.delta={}; self.external=[]; self.usage={}; self.retrieved={}
  self.mm.param.audit=[x for x in self.mm.param.audit if x['user']!='maya']
  self.buddy.register_user('maya','Maya',False)
