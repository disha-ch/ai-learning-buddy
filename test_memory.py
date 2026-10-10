"""Offline integration checks; model behavior is stubbed, not a live quality eval."""
import unittest, json
from unittest.mock import patch
from types import SimpleNamespace
from engine import Engine
class FakeClient:
 def __init__(self,*a,**kw):
  self.embeddings=SimpleNamespace(create=lambda **kw:SimpleNamespace(data=[SimpleNamespace(embedding=[1.,.5,.2]) for _ in kw['input']]))
class MemoryChecks(unittest.TestCase):
 def setUp(self):
  with patch('engine.OpenAI',FakeClient): self.e=Engine('test-key')
  self.e.c.llm_json=lambda *a,**kw:kw.get('default',{})
 def test_graph_and_working(self):
  self.e.c.chat=lambda *a,**kw:SimpleNamespace(content='A function is reusable code.',tool_calls=None)
  self.e.turn('Explain functions')
  self.assertEqual(len(self.e.mm.wm('maya','s1').turns),2)
  self.assertEqual(len(self.e.nodes),4)
 def test_once_only_reminder(self):
  e=self.e; rid=e.mm.prospective.add('maya','practice',in_days=1)
  self.assertEqual(e.mm.prospective.due('maya'),[])
  e.c.CLOCK.advance(days=1); self.assertEqual(len(e.mm.prospective.due('maya')),1)
  e.mm.prospective.mark(rid); self.assertEqual(e.mm.prospective.due('maya'),[])
 def test_snapshot_forgetting_and_isolation(self):
  e=self.e; e.mm.semantic.upsert('maya','Maya studies Python'); e.mm.semantic.upsert('other','Other learns Java')
  self.assertEqual(e.mm.semantic.render('maya'),['Maya studies Python'])
  data=e.export(); self.assertNotIn('test-key',data)
  e.forget(); self.assertEqual(e.mm.semantic.render('maya'),[])
  e.restore(data); self.assertEqual(e.mm.semantic.render('maya'),['Maya studies Python'])
 def test_failed_turn_rolls_back_reminder(self):
  e=self.e; rid=e.mm.prospective.add('maya','practice',in_days=0)
  def fail(*a,**kw): raise RuntimeError('offline')
  e.c.chat=fail
  with self.assertRaises(RuntimeError): e.turn('Hi')
  self.assertEqual(e.mm.prospective.store.rows[rid]['meta']['status'],'pending')
 def test_consent_gate(self):
  self.assertEqual(self.e.mm.param.consider('maya','question','answer'), 'rejected: no consent')
if __name__=='__main__': unittest.main()

class Mem0AdapterChecks(unittest.TestCase):
 def test_native_add_and_user_filtered_search(self):
  from mem0_backend import Mem0Semantic
  fake=SimpleNamespace(add=lambda *a,**kw:{'results':[{'id':'1','event':'ADD'}]},
   search=lambda query,**kw: {'results':[{'id':'1','memory':'Maya learns Python','score':0.9}]} if kw['filters']=={'user_id':'maya'} else {})
  with patch('mem0_backend.Memory.from_config',return_value=fake) as factory:
   m=Mem0Semantic('test-key','openrouter/free','openai/text-embedding-3-small')
  config=factory.call_args.args[0]
  self.assertEqual(config['embedder']['config']['openai_base_url'],'https://openrouter.ai/api/v1')
  self.assertEqual(m.upsert('maya','Maya learns Python')['action'],'ADD')
  self.assertEqual(m.render('maya','Python'),['Maya learns Python'])
  self.assertEqual(m.render('other','Python'),[])
  self.assertEqual(m.events[-1]['operation'],'mem0.search')
 def test_mem0_live_client_not_deepcopied(self):
  import copy
  from mem0_backend import Mem0Semantic
  with patch('mem0_backend.Memory.from_config',return_value=object()):
   m=Mem0Semantic('test-key','openrouter/free','openai/text-embedding-3-small')
  self.assertIs(copy.deepcopy(m),m)
