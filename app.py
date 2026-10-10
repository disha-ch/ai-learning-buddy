import os,json
from pathlib import Path
import streamlit as st
from engine import Engine,SAMPLES

# Never share Engine instances across browser sessions using st.cache_resource.
st.set_page_config(page_title='Maya • Memory Lab',page_icon='🧠',layout='wide')
st.markdown('''<style>.stApp{background:#0c1220;color:#edf2ff}h1,h2,h3{letter-spacing:-.035em}div[data-testid="stMetric"]{background:#172237;padding:16px;border-radius:14px} .stCaption{color:#a5b4cf}</style>''',unsafe_allow_html=True)
st.title('🧠 Maya’s Learning Buddy')
st.caption('FDE MEMORY LAB  ·  Python coaching  ·  Notebook code + LangGraph')
with st.sidebar:
 st.header('Your lab controls')
 key=st.text_input('OpenRouter API key',type='password',value='')
 model=st.text_input('Chat model',value='openrouter/free')
 emb='openai/text-embedding-3-small'
 backend=st.selectbox('Semantic memory backend',['mem0','notebook'],format_func=lambda x:'Mem0 OSS (tutor version)' if x=='mem0' else 'Notebook from-scratch (compare)')
 st.caption('Each visitor supplies their own key. Chat uses OpenRouter. Embeddings may incur a small charge. The key stays in this browser session, never in exports.')
 if st.button('Connect / restart lab',type='primary',disabled=not key):
  try:
   with st.spinner('Connecting and indexing notebook course notes…'): st.session_state.engine=Engine(key,model,emb,backend=backend)
   st.session_state.step=0
  except Exception as exc: st.error(f'Connection failed ({type(exc).__name__}). Check key, credit, model availability and network.')
 st.divider()
 st.caption('Mem0 needs no separate API key in this app.')
 st.caption('Original memory definitions are preserved in notebook_core.py. Scenario extensions and graph nodes live in engine.py.')
if 'engine' not in st.session_state:
 st.info('Enter your key in the sidebar and connect to explore Maya’s nine-turn scenario.')
 st.subheader('Seven memory types, one conversation')
 st.table({'Memory':['Working','Semantic','Episodic','Procedural','Parametric','External','Prospective'],'Explore':['Recent chat + rolling summary','Name, role, goal, current skills','Learning struggles and milestones','Simple examples; no jargon','Pretrained Python knowledge; optional training candidates','Course RAG + live Python.org lookup','Tomorrow’s practice reminder']})
 st.stop()
e=st.session_state.engine
st.caption('Active semantic memory: '+('Mem0 OSS · Qdrant · OpenRouter' if e.backend=='mem0' else 'Notebook vector store'))
with st.sidebar:
 st.write('🕒 Simulated time:',e.c.ts())
 if st.button('Advance one day ⏩'): e.c.CLOCK.advance(days=1); st.rerun()
 st.caption('Due reminders are checked on your next message. The live version lookup uses real time.')
 consent=st.checkbox('Opt in to training-candidate collection',value=e.c.CONSENT.get('maya',False))
 e.c.set_consent('maya',consent)
 if st.button('End session + consolidate'):
  try:
   with st.spinner('Consolidating…'): st.session_state.consolidation=e.end_session()
   st.rerun()
  except Exception as exc: st.error(f'Consolidation failed ({type(exc).__name__}).')
 st.download_button('Download memory snapshot',e.export(),'maya_memory.json','application/json')
 uploaded=st.file_uploader('Restore a memory snapshot',type='json')
 if uploaded and st.button('Restore snapshot'):
  try: e.restore(uploaded.getvalue()); st.rerun()
  except Exception: st.error('Could not restore: use a valid snapshot with the same embedding model.')
 if st.checkbox('Confirm deleting Maya’s memories') and st.button('Forget Maya'):
  e.forget(); st.session_state.step=0; st.session_state.pop('consolidation',None); st.rerun()
 st.caption('Mem0 uses a private local Qdrant database for this browser session. Download a snapshot before closing. This is a single-user learning demo.')
cols=st.columns(4)
for col,name in zip(cols,['semantic','episodic','procedural','prospective']): col.metric(name.title(),len(e.mm.stores()[name].rows))
chat,inspector,learn,source=st.tabs(['💬 Chat playground','🔬 Memory inspector','📚 How it works','</> Original code'])
with chat:
 left,right=st.columns([3,2])
 with right:
  st.subheader('Guided nine-turn scenario')
  idx=st.selectbox('Choose a turn',range(9),index=min(st.session_state.get('step',0),8),format_func=lambda i:f'{i+1}. {SAMPLES[i]}')
  run=st.button('Send selected turn',type='primary')
  st.caption('Send in order. Then end the session and ask what Maya struggled with to prove long-term recall. Advance one day and say “Hi” to trigger the reminder.')
  st.info('Parametric knowledge = what the model learned during pretraining. Saving a training candidate does not retrain the model.')
  if getattr(e,'usage',None):
   st.write('Memory included / tools used on last response')
   st.table({'Type':list(e.usage),'Backend activity':list(e.usage.values())})
  if getattr(e,'nodes',None): st.write('Last graph execution'); st.code(' → '.join(e.nodes))
 with left:
  for m in e.history:
   with st.chat_message(m['role']):
    st.markdown(m['content'])
    if m.get('memory_usage'):
     with st.expander('🧠 Memory types for this response'):
      st.table({'Memory type':list(m['memory_usage']),'Backend activity':list(m['memory_usage'].values())})
     with st.expander('Backend operations for this response'):
      st.json(m.get('memory_events',[]))
  prompt=st.chat_input('Ask your learning buddy…')
  if run: prompt=SAMPLES[idx]
  if prompt:
   try:
    with st.spinner('Running memory graph…'): e.turn(prompt)
    if run: st.session_state.step=min(idx+1,8)
    st.rerun()
   except Exception as exc: st.error(f'Turn failed ({type(exc).__name__}); the response was not completed. Mem0 writes may already have been saved; inspect memory before retrying. Check model availability and credits.')
  if ('maya',e.session) in e.buddy.last_turn:
   up,down=st.columns(2)
   feedback=True if up.button('👍 Helpful') else False if down.button('👎 Not helpful') else None
   if feedback is not None:
    try: e.buddy.give_feedback('maya',e.session,thumbs_up=feedback); st.success('Feedback recorded. See procedural statistics and candidate audit.')
    except Exception: st.error('Feedback could not be saved.')
with inspector:
 st.subheader('See what actually happened')
 st.caption('Retrieved / included means available to the model, not proof it causally relied on that memory.')
 if getattr(e,'usage',None): st.table({'Memory':list(e.usage),'Observed behavior':list(e.usage.values())})
 if e.backend=='mem0':
  with st.expander('Mem0 native ADD / UPDATE / DELETE and search results',expanded=True): st.json(e.mm.semantic.events)
  if st.button('Load Mem0 update history'):
   try: st.json(e.mm.semantic.history('maya'))
   except Exception: st.error('Mem0 history could not be loaded.')
 kind=st.selectbox('Memory store',['working','semantic','episodic','procedural','external','prospective','parametric candidates'],format_func=str.title)
 if kind=='working':
  wm=e.mm.wm('maya',e.session); st.json({'summary':wm.summary,'recent_turns':wm.turns,'scratchpad':wm.scratch,'approx_tokens':wm.tokens()})
 else: st.json(e.snapshot()['param' if kind=='parametric candidates' else kind])
 with st.expander('Changes on the last turn',expanded=True): st.json(getattr(e,'delta',{}))
 with st.expander('Retrieved episodes / playbooks / working context'): st.json(getattr(e,'retrieved',{}))
 with st.expander('Tool calls and memory reads'): st.json(e.events)
 with st.expander('Exact retrieved context sent to model'): st.code(e.context)
 with st.expander('Live external evidence'): st.json(e.external)
 with st.expander('Training-candidate audit (no actual training)'): st.json(e.mm.param.audit)
 with st.expander('Last end-of-session consolidation'): st.json(st.session_state.get('consolidation',{}))
with learn:
 st.markdown('''### Memory lifecycle
1. **Capture:** extract facts, reported experiences and explicit teaching preferences.
2. **Retrieve:** notebook semantic search, recency-weighted episodes, teaching playbooks and due reminders.
3. **Respond:** original tool-calling loop inside a LangGraph node; tools can store facts, search notes or create reminders.
4. **Inspect:** compare store snapshots and show actual tool calls.
5. **Consolidate:** end the session to derive an episode and useful teaching procedures, then clear working memory.
6. **Persist or forget:** download a snapshot, restore it later, or delete Maya’s data.

### What changed from the notebook?
Mem0 is the default semantic backend: it owns fact extraction, deduplication, update history and retrieval. All other memory types use the notebook classes. The memory class definitions and `run_agent` are copied verbatim. We added a corrected OpenRouter client, configurable embedding model, four-node LangGraph, immediate experience/preference capture, a Python.org tool, notebook-state rollback, and Streamlit controls (Mem0 writes are not transactional). This makes all nine turns observable without waiting for end-of-session consolidation.

Episode timestamps indicate **when recorded**; “yesterday” remains in the episode text. Retrieval is approximate and model-dependent. The model can still fail to call a tool or extract a memory—check the inspector rather than assuming success.

The graph has no persistent checkpointer: the notebook memory objects hold state. Working memory is ephemeral; downloaded snapshots hold long-term stores. Reminder delivery occurs on chat turns only. Parametric weights never change here.
''')
with source:
 name=st.selectbox('Read implementation',['notebook_core.py','engine.py','mem0_backend.py','source_map.json'])
 st.code(Path(__file__).with_name(name).read_text(),language='json' if name.endswith('json') else 'python')
