import unittest,json,os
from unittest.mock import patch
from langchain_core.messages import AIMessage
from observatory_core import Observatory

class FakeMemory:
 mode='Mem0 OSS'
 def __init__(self):self.rows=[];self.users=[];self.fail=False
 def search(self,q,u):self.users.append(u);return self.rows[:]
 def all(self,u):return self.rows[:]
 def add(self,t,u):
  self.users.append(u)
  if self.fail:raise TimeoutError()
  self.rows.append({'id':str(len(self.rows)),'memory':t});return {'results':[{'event':'ADD','memory':t}]}
 def close(self):pass
class FakeLLM:
 def __init__(self):self.prompts=[]
 def invoke(self,messages):self.prompts.append(messages);return AIMessage(content='A function is a reusable block of code.')

class ObservatoryChecks(unittest.TestCase):
 def setUp(self):self.mem=FakeMemory();self.llm=FakeLLM();self.lab=Observatory(backend=self.mem,llm=self.llm)
 def test_regex_records_preferences_events_and_tasks(self):
  self.lab.chat('Whenever you teach me, avoid jargon.')
  self.lab.chat('Yesterday I studied loops and struggled.')
  result=self.lab.chat('Remind me tomorrow at 7 PM to practice loops.')
  self.assertEqual(len(self.lab.registry['procedural']),1)
  self.assertEqual(len(self.lab.registry['episodic']),1)
  self.assertEqual(len(result['tasks']),1)
  self.assertIn('T19:00:00',result['tasks'][0]['due'])
  self.assertEqual([s['name'] for s in result['stages']],['recall','external','respond','consolidate'])
  self.assertEqual(len(result['cards']),7)
 def test_new_thread_retains_mem0_and_clears_working(self):
  self.lab.chat('Maya is learning Python.');first=self.lab.snapshot()
  self.lab.new_thread();second=self.lab.snapshot()
  self.assertEqual(first['message_count'],2);self.assertEqual(second['message_count'],0)
  self.assertEqual(second['records'],first['records'])
  self.lab.chat('What do you know?')
  self.assertTrue(self.lab.hits)
 def test_failed_consolidation_preserves_answer_and_reports_error(self):
  self.mem.fail=True;result=self.lab.chat('I mastered loops.')
  self.assertTrue(result['history'][-1]['answer']);self.assertTrue(result['warning'])
  self.assertTrue(any(x['action']=='ERROR' for x in result['operations']))
  self.assertEqual(len(self.lab.registry['episodic']),1)
 def test_two_visitors_are_isolated(self):
  other=Observatory(backend=FakeMemory(),llm=FakeLLM())
  self.lab.chat('My goal is AI engineering.')
  self.assertNotEqual(self.lab.user_id,other.user_id)
  self.assertEqual(other.snapshot()['records'],[])
  self.assertTrue(all(u==self.lab.user_id for u in self.mem.users))
 def test_stable_version_ignores_prerelease(self):
  class Response:
   def raise_for_status(self):pass
   def json(self):return [{'name':'Python 3.16.0a1'},{'name':'Python 3.14.2'},{'name':'Python 3.13.9'}]
  with patch('observatory_core.requests.get',return_value=Response()):r=self.lab.chat('What is the latest stable Python version?')
  self.assertEqual(self.lab.registry['external'][0]['value'],'Python 3.14.2')
  self.assertTrue(any(o['type']=='external' and o['action']=='FETCH' for o in r['operations']))
 def test_procedural_rule_reaches_next_prompt(self):
  self.lab.chat('Always explain using tiny examples.');self.lab.chat('What is a list?')
  self.assertIn('Always explain using tiny examples.',self.llm.prompts[-1][0].content)
 def test_milestone_is_classified_episodic(self):
  result=self.lab.chat('I have now mastered nested loops!')
  card=next(x for x in result['cards'] if x['type']=='episodic')
  self.assertTrue(card['items']);self.assertIn('WRITE',card['actions'])

class DjangoAPI(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  os.environ.setdefault('DJANGO_SETTINGS_MODULE','observatory.settings')
  import django;django.setup()
 def test_csrf_and_session_isolation(self):
  from django.test import Client,override_settings
  from observatory import views
  with override_settings(ALLOWED_HOSTS=['testserver']):
   a=Client(enforce_csrf_checks=True);b=Client(enforce_csrf_checks=True)
   a.get('/');b.get('/')
   self.assertEqual(a.post('/api/chat',data=json.dumps({'question':'Hi'}),content_type='application/json').status_code,403)
   def fresh(*args,**kw):return Observatory(backend=FakeMemory(),llm=FakeLLM())
   with patch('observatory.views.Observatory',side_effect=fresh):
    r=a.post('/api/connect',data=json.dumps({'key':'test-key'}),content_type='application/json',HTTP_X_CSRFTOKEN=a.cookies['csrftoken'].value)
   self.assertEqual(r.status_code,200)
   r=a.post('/api/chat',data=json.dumps({'question':'My name is Maya'}),content_type='application/json',HTTP_X_CSRFTOKEN=a.cookies['csrftoken'].value)
   self.assertEqual(r.status_code,200);self.assertEqual(len(r.json()['cards']),7)
   self.assertFalse(b.get('/api/state').json()['connected'])
   self.assertNotIn('test-key',r.content.decode())
   views.LABS.clear()
if __name__=='__main__':unittest.main()
