"""Django transport. All graph/memory behavior lives in observatory_core.py.

Only an opaque lab ID is stored in the signed session cookie, never credentials.
Run one gunicorn worker; in-process labs expire after two hours of inactivity.
"""
import json,os,time,uuid,threading
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET,require_POST
from observatory_core import Observatory,empty_snapshot,friendly_error
LABS={};LOCK=threading.RLock();MAX_LABS=40

def payload(request):
 data=json.loads(request.body or b'{}')
 if not isinstance(data,dict):raise ValueError('Expected a JSON object')
 return data

def current(request):
 with LOCK:
  lab=LABS.get(request.session.get('lab_id'))
  if lab:lab.last_seen=time.time()
  return lab

def error(text,status=400):return JsonResponse({'error':text},status=status)

@require_GET
@ensure_csrf_cookie
def index(request):return render(request,'index.html')

@require_GET
def health(request):return JsonResponse({'status':'ok'})

@require_GET
def state(request):
 lab=current(request)
 data=lab.snapshot() if lab else empty_snapshot()
 data['server_key_ready']=bool(os.getenv('OPEN_ROUTER_KEY') or os.getenv('OPENROUTER_API_KEY'))
 data['cloud_key_ready']=bool(os.getenv('MEM0_API_KEY'))
 return JsonResponse(data)

@require_POST
def connect(request):
 try:
  data=payload(request);key=str(data.get('key') or os.getenv('OPEN_ROUTER_KEY') or os.getenv('OPENROUTER_API_KEY') or '')
  model=str(data.get('model') or 'openrouter/free')
  cloud_key=str(data.get('mem0_key') or os.getenv('MEM0_API_KEY') or '') if data.get('cloud') else None
  if not key:return error('An OpenRouter key is required. Add it to the server environment or enter your own.')
  if data.get('cloud') and not cloud_key:return error('Mem0 Cloud needs a Mem0 Platform key. Turn Cloud off to use OSS.')
  with LOCK:
   expired=[k for k,v in LABS.items() if time.time()-v.last_seen>7200]
   for k in expired:LABS.pop(k).close()
   if len(LABS)>=MAX_LABS:return error('The demo is at capacity. Please try again later.',503)
  lab=Observatory(key,model,cloud_key=cloud_key)
  with LOCK:
   old=LABS.pop(request.session.get('lab_id'),None)
   if old:old.close()
   token=uuid.uuid4().hex;LABS[token]=lab;request.session['lab_id']=token
  return JsonResponse(lab.snapshot())
 except (ValueError,TypeError,json.JSONDecodeError):return error('Invalid configuration.')
 except Exception as exc:return error(friendly_error(exc),502)

@require_POST
def chat(request):
 lab=current(request)
 if not lab:return error('Connect a learning session first.',409)
 try:
  text=payload(request).get('question','')
  if not isinstance(text,str):return error('Question must be text.')
  return JsonResponse(lab.chat(text))
 except (ValueError,TypeError,json.JSONDecodeError):return error('Enter between 1 and 6,000 characters.')

@require_POST
def new_thread(request):
 lab=current(request)
 if not lab:return error('Connect first.',409)
 lab.new_thread();return JsonResponse(lab.snapshot())

@require_POST
def refresh(request):
 lab=current(request)
 if not lab:return error('Connect first.',409)
 lab.refresh();return JsonResponse(lab.snapshot())

@require_POST
def complete_task(request):
 lab=current(request)
 if not lab:return error('Connect first.',409)
 try:lab.complete_task(payload(request).get('id'));return JsonResponse(lab.snapshot())
 except (ValueError,TypeError,json.JSONDecodeError):return error('Task not found.',404)
