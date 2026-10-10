import html,json
from pathlib import Path

def e(value):return html.escape(str(value),quote=True)

def memory_cards(cards):
 out=[]
 for c in cards:
  rows=''.join(f'<div class="memory-item">{e(t)}</div>' for t in c['items'][-4:]) or '<div class="memory-empty">Nothing recorded yet.<br>Start a conversation to watch this space.</div>'
  out.append(f'''<article class="memory-card" style="--tone:{c['color']}"><div class="card-top"><span class="memory-symbol">{c['symbol']}</span><span class="memory-count">{len(c['items'])}</span></div><h3>{c['type'].title()}</h3><p class="card-subtitle">{c['subtitle']}</p><div class="memory-actions">{' '.join(f'<span>{e(a)}</span>' for a in c['actions'])}</div><div class="memory-items">{rows}</div></article>''')
 return '<div class="memory-grid">'+''.join(out)+'</div>'

def trace_html(ops):
 return '<div class="trace-list">'+(''.join(f'<div class="trace-row"><span class="trace-time">{e(x.get("at",""))}</span><span class="trace-kind">{e(x["type"].title())}</span><span class="trace-action">{e(x["action"])}</span><p>{e(x["detail"])}</p></div>' for x in ops) or '<p class="memory-empty">Send a message to see real backend operations here.</p>')+'</div>'

def pipeline_html(stages):
 observed={s['name']:s for s in stages}
 return '<div class="pipeline">'+''.join(f'<div class="pipeline-step {observed.get(n,{}).get("status","")}"><span>0{i+1}</span><strong>{n.title()}</strong><small>{str(observed[n]["ms"])+" ms" if n in observed else "Waiting"}</small></div>' for i,n in enumerate(['recall','external','respond','consolidate']))+'</div>'

def lottie_html():
 data=(Path(__file__).parent/'static/observatory/memory-orbit.json').read_text()
 return '''<div id="orbit" aria-label="Animated memory orbit" style="height:150px;width:100%;"></div><script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script><script>if(window.lottie){lottie.loadAnimation({container:document.getElementById('orbit'),renderer:'svg',loop:true,autoplay:!matchMedia('(prefers-reduced-motion: reduce)').matches,animationData:'''+data+'''})}</script>'''
