"""Streamlit host entry point; shares its backend with the Django application."""
import os,json
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st
import streamlit.components.v1 as components
from observatory_core import Observatory,empty_snapshot,SAMPLES,friendly_error
from ui_parts import memory_cards,trace_html,pipeline_html,lottie_html,e
load_dotenv(Path(__file__).parent/'.env')
st.set_page_config(page_title='Memory Observatory',page_icon='◉',layout='wide',initial_sidebar_state='collapsed')
BASE=Path(__file__).parent
st.markdown('<style>'+ (BASE/'static/observatory/style.css').read_text()+'''
.stApp{background:radial-gradient(ellipse at 80% 0%,#211936 0%,#090d19 42%);color:#e9eef9}.block-container{max-width:1480px;padding-top:2.4rem;padding-bottom:2rem}section[data-testid="stSidebar"]{background:#111827}div[data-testid="stChatMessage"]{background:#111b2d;border:1px solid #26344d;border-radius:14px;padding:16px}div[data-testid="stChatInput"]{border-radius:14px}div[data-testid="stTabs"] button{font-size:13px}button[kind="primary"]{background:#b6a1ff;color:#101322;border:0}div[data-testid="stExpander"]{background:#111827;border-color:#29334a}
</style>''',unsafe_allow_html=True)

def secret(name):
 try:return str(st.secrets.get(name,'') or os.getenv(name,''))
 except (FileNotFoundError,st.errors.StreamlitSecretNotFoundError):return os.getenv(name,'')

server_key=secret('OPEN_ROUTER_KEY') or secret('OPENROUTER_API_KEY')
server_mem0=secret('MEM0_API_KEY')
with st.sidebar:
 st.markdown('### Observatory settings')
 if server_key:st.success('Owner’s demo key is configured server-side.')
 supplied=st.text_input('OpenRouter key (optional override)' if server_key else 'OpenRouter API key',type='password')
 key=supplied or server_key
 model=st.text_input('Chat model',value='openrouter/free')
 cloud=st.checkbox('Use Mem0 Cloud (as in the notebook)',value=bool(server_mem0))
 mem_key=st.text_input('Mem0 Platform key',type='password') if cloud and not server_mem0 else ''
 st.caption('Cloud uses Mem0 Platform. OSS uses your OpenRouter key and local Qdrant. No model weights are changed.')
 connect=st.button('Start learning session',type='primary',disabled=not key or (cloud and not (mem_key or server_mem0)))
 if connect:
  try:
   with st.spinner('Preparing the memory backend…'):new=Observatory(key,model,cloud_key=(mem_key or server_mem0) if cloud else None)
   old=st.session_state.get('observatory')
   st.session_state.observatory=new
   if old:old.close()
   st.session_state.pop('setup_error',None)
   st.rerun()
  except Exception as exc:st.error(friendly_error(exc))
 st.caption('Never paste keys into chat. Your key is not included in traces or downloads.')
# Start automatically only when the owner has configured a server-side key.
if server_key and 'observatory' not in st.session_state and not st.session_state.get('setup_error'):
 try:st.session_state.observatory=Observatory(server_key,model,cloud_key=server_mem0 or None)
 except Exception as exc:st.session_state.setup_error=friendly_error(exc)
lab=st.session_state.get('observatory');data=lab.snapshot() if lab else empty_snapshot()
hero,animation=st.columns([5,1])
with hero:
 st.markdown('<div class="obs-header"><div class="obs-eyebrow">FDE LAB / LANGGRAPH × MEM0 × OPENROUTER</div><h1 class="obs-title">A conversation.<br><span>Seven kinds of memory.</span></h1><p class="obs-subtitle">Learn with Maya’s AI buddy. Watch the facts, experiences and preferences behind every response become visible.</p></div>',unsafe_allow_html=True)
 st.markdown(f'<span class="obs-status">{e(data["backend"])} · Lesson {data["thread"]} · {data["turn"]} turns</span>',unsafe_allow_html=True)
with animation:components.html(lottie_html(),height=165,scrolling=False)
if not lab:
 st.info('Open Settings in the sidebar and add your OpenRouter key to begin. If the owner adds it to Streamlit Secrets, teammates can start without a key.')
 if st.session_state.get('setup_error'):st.error(st.session_state.setup_error)
if lab:
 with st.sidebar:
  if st.button('New conversation · keep memories'):lab.new_thread();st.rerun()
  if st.button('Refresh stored Mem0 records'):lab.refresh();st.rerun()
  st.download_button('Download session + operation trace',json.dumps(data,indent=2,default=str),'observatory_session.json','application/json')
  st.caption('A new conversation resets working context while retaining this student’s memories. Browser/server restarts do not preserve all local state.')

talk,observatory,activity,guide=st.tabs(['Conversation','Memory observatory','Operation trace','How it works'])
with talk:
 left,right=st.columns([1.65,1],gap='large')
 with left:
  current=[x for x in data['history'] if x['thread']==data['thread']]
  if not current:
   st.markdown('<h2 class="obs-section-title">What are we learning today?</h2><p class="obs-section-subtitle">Ask about a topic, record a study session, or tell your buddy how you like to learn.</p>',unsafe_allow_html=True)
  for i,turn in enumerate(current):
   with st.chat_message('user'):st.markdown(turn['question'])
   if turn['answer']:
    with st.chat_message('assistant'):
     st.markdown(turn['answer'])
     kinds=list(dict.fromkeys(o['type'].title() for o in turn['operations']))
     st.caption('Observed memory operations: '+' · '.join(kinds))
     with st.expander('Inspect this response’s backend operations'):st.markdown(trace_html(turn['operations']),unsafe_allow_html=True)
   if turn['warning']:st.warning(turn['warning'])
  with st.expander('Try Maya’s guided memory lifecycle',expanded=not bool(current)):
   chosen=st.selectbox('Pick a sample',SAMPLES,label_visibility='collapsed')
   send=st.button('Send sample',disabled=not lab)
  prompt=st.chat_input('Ask, learn, or record a milestone…',disabled=not lab,max_chars=6000)
  if send:prompt=chosen
  if prompt and lab:
   with st.status('Following the memory lifecycle…',expanded=True) as status:
    lab.chat(prompt,notify=lambda name:status.write('→ '+name.title()))
    status.update(label='Response and operation trace ready',state='complete')
   st.rerun()
 with right:
  st.markdown('<h2 class="obs-section-title">Behind the response</h2><p class="obs-section-subtitle">Executed graph nodes. Real operations, not guessed attention.</p>',unsafe_allow_html=True)
  st.markdown(pipeline_html(data['stages']),unsafe_allow_html=True)
  for card in data['cards']:
   actions=' · '.join(card['actions'])
   st.markdown(f'<div style="display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid #263149;padding:10px 0"><span style="color:{card["color"]}">{card["symbol"]} {card["type"].title()}</span><span style="font:10px/2 ui-monospace;color:#9caeca">{e(actions)}</span></div>',unsafe_allow_html=True)
  st.caption('READ means a retrieval happened. It does not prove the model relied on that memory.')
with observatory:
 st.markdown('<h2 class="obs-section-title">Memory, made visible.</h2><p class="obs-section-subtitle">State after the latest turn · select a type below to inspect complete records.</p>',unsafe_allow_html=True)
 st.markdown(memory_cards(data['cards']),unsafe_allow_html=True)
 selected=st.selectbox('Inspect all items',[c['type'] for c in data['cards']],format_func=str.title)
 card=next(c for c in data['cards'] if c['type']==selected)
 st.json({'type':selected,'actions':card['actions'],'items':card['items']})
 if selected=='prospective' and lab:
  for task in data['tasks']:
   if task['status']!='COMPLETED' and st.button('Mark complete: '+task['text'],key=task['id']):lab.complete_task(task['id']);st.rerun()
with activity:
 st.markdown('<h2 class="obs-section-title">The application’s audit trail.</h2>',unsafe_allow_html=True)
 st.markdown(pipeline_html(data['stages']),unsafe_allow_html=True)
 st.markdown(trace_html(data['operations']),unsafe_allow_html=True)
 with st.expander('Raw recalled records and similarity scores'):st.json(data['recalled'])
 with st.expander('Raw Mem0 records'):st.json(data['records'])
 with st.expander('Raw executed operations'):st.json(data['operations'])
with guide:
 st.markdown('''### Your notebook, as an application
**Recall → external lookup → respond → consolidate → dashboard.**

- **Working:** LangGraph `InMemorySaver`, isolated by student and lesson.
- **Semantic / episodic:** Mem0 records classified for display; local reported experiences are retained too.
- **Procedural:** explicit teaching preferences, included in the prompt.
- **External:** a real Python.org lookup, timestamp and source.
- **Prospective:** pending intentions, with manual completion. No background notifications.
- **Parametric:** the model’s pretrained knowledge. We log the model call; weights are neither inspected nor trained.

“New conversation” changes the LangGraph thread while preserving this student’s long-term records. Mem0 Cloud requires a Mem0 Platform key; OSS does not. The same backend also powers the Django UI and API included in the repo.

The source notebook is preserved under `reference/`. We corrected broken regex word boundaries, scoped global state per visitor, added partial-failure reporting, and changed the release lookup to select stable Python versions.
''')
 st.caption('Mem0 classification is heuristic. Memories may be stale or imperfect. Snapshots contain your conversation. Local state is ephemeral; Cloud records remain at the provider.')
