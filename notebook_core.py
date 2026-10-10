# Definitions copied verbatim from the supplied notebook; demonstrations omitted.
import os
from openai import OpenAI


# Notebook cell 5
import json, uuid, re, math, time, textwrap


# Notebook cell 5
import numpy as np


# Notebook cell 5
import pandas as pd


# Notebook cell 5
from datetime import datetime, timedelta


# Notebook cell 5
from dataclasses import dataclass


# Notebook cell 5
from typing import Callable, Optional


# Notebook cell 5
_embed_cache = {}


# Notebook cell 5
def embed(texts):
    """text(s) -> list of vectors (cached, batched)."""
    if isinstance(texts, str): texts = [texts]
    missing = [t for t in dict.fromkeys(texts) if t not in _embed_cache]
    if missing:
        resp = client.embeddings.create(model=EMBED_MODEL, input=missing)
        for t, d in zip(missing, resp.data):
            _embed_cache[t] = d.embedding
    return [_embed_cache[t] for t in texts]


# Notebook cell 5
def chat(messages, model=None, **kw):
    r = client.chat.completions.create(model=model or CHAT_MODEL, messages=messages, **kw)
    return r.choices[0].message


# Notebook cell 5
def llm_json(system, payload, default=None):
    """Ask the model for a JSON object. Never crashes the demo: falls back to `default`."""
    user = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    try:
        m = chat([{"role": "system", "content": system + "\nRespond with a single valid JSON object only."},
                  {"role": "user", "content": user}],
                 response_format={"type": "json_object"}, temperature=0)
        return json.loads(m.content)
    except Exception as e:
        print("⚠️ llm_json failed:", e)
        return default if default is not None else {}


# Notebook cell 5
class SimClock:
    def __init__(self, start): self.t = start
    def now(self): return self.t
    def advance(self, days=0, hours=0):
        self.t += timedelta(days=days, hours=hours); return self.t


# Notebook cell 5
CLOCK = SimClock(datetime(2026, 10, 8, 9, 0))


# Notebook cell 5
def ts(): return CLOCK.now().isoformat(timespec="minutes")


# Notebook cell 5
def hr(title): print("\n" + "═" * 72 + f"\n{title}\n" + "═" * 72)


# Notebook cell 8
class CoreMemory:
    """Small, always-in-context memory split into labelled blocks."""
    def __init__(self, limit=450):
        self.limit = limit
        self.blocks = {"student": "", "coach": "I am StudyBuddy, a friendly Python/ML coach. I keep answers short."}

    def render(self):
        return "\n".join(f"<{k}>\n{v or '(empty)'}\n</{k}>" for k, v in self.blocks.items())

    # --- the two operations we will expose to the LLM as tools ---
    def append(self, section, text):
        if section not in self.blocks: return f"ERROR: unknown section {section}"
        new = (self.blocks[section] + "\n" + text).strip()
        if len(new) > self.limit:
            return f"ERROR: block '{section}' would exceed {self.limit} chars. Use core_memory_replace to condense it first."
        self.blocks[section] = new
        return f"OK. '{section}' is now {len(new)}/{self.limit} chars."

    def replace(self, section, old, new):
        if section not in self.blocks: return f"ERROR: unknown section {section}"
        if old not in self.blocks[section]: return f"ERROR: text not found in '{section}'"
        self.blocks[section] = self.blocks[section].replace(old, new)
        return f"OK. Replaced text in '{section}'."


# Notebook cell 10
@dataclass
class Tool:
    name: str
    description: str
    properties: dict
    fn: Callable
    required: Optional[list] = None
    @property
    def schema(self):            # the JSON schema the OpenAI API wants
        return {"type": "function", "function": {
            "name": self.name, "description": self.description,
            "parameters": {"type": "object", "properties": self.properties,
                           "required": self.required if self.required is not None else list(self.properties)}}}


# Notebook cell 12
def run_agent(messages, tools, refresh=None, on_tool=None, max_steps=6, model=None):
    """Generic tool-calling loop. messages[0] must be the system message (it can be refreshed)."""
    registry = {t.name: t for t in tools}
    schemas = [t.schema for t in tools]
    for _ in range(max_steps):
        msg = chat(messages, model=model, **({"tools": schemas} if schemas else {}))
        if not msg.tool_calls:                                   # plain answer → hand control back to the user
            messages.append({"role": "assistant", "content": msg.content})
            return msg.content
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in msg.tool_calls]})
        for tc in msg.tool_calls:                                # the model may request several tools at once
            args = {}
            try:
                args = json.loads(tc.function.arguments or "{}")
                result = registry[tc.function.name].fn(**args)
            except Exception as e:
                result = f"ERROR: {e}"
            if on_tool: on_tool(tc.function.name, args, result)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
        if refresh: messages[0]["content"] = refresh()           # ← memory edits become visible immediately
    return "(stopped: max steps reached)"


# Notebook cell 12
def lab1_chat(user_msg):
    sys_msg = lambda: LAB1_SYSTEM + core.render()
    messages = [{"role": "system", "content": sys_msg()}] + lab1_history + [{"role": "user", "content": user_msg}]
    log = lambda n, a, r: print(f"     🔧 {n}({json.dumps(a)}) → {r}")
    reply = run_agent(messages, lab1_tools, refresh=sys_msg, on_tool=log)
    lab1_history.extend([{"role": "user", "content": user_msg}, {"role": "assistant", "content": reply}])
    print(f"👤 {user_msg}\n🤖 {reply}\n")
    return reply


# Notebook cell 21
def _match(meta, where):
    if not where: return True
    for k, v in where.items():
        mv = meta.get(k)
        if isinstance(v, (list, tuple, set)):
            if mv not in v: return False
        elif mv != v: return False
    return True


# Notebook cell 21
class VectorStore:
    def __init__(self, name): self.name, self.rows = name, {}

    def add(self, text, **meta):
        rid = f"{self.name[:3]}-{uuid.uuid4().hex[:6]}"
        meta.setdefault("created_at", ts())
        self.rows[rid] = {"id": rid, "text": text, "vec": embed(text)[0], "meta": meta}
        return rid

    def search(self, query, k=3, where=None, min_score=0.0):
        cand = [r for r in self.rows.values() if _match(r["meta"], where)]
        if not cand: return []
        q = np.array(embed(query)[0]); M = np.array([r["vec"] for r in cand])
        sims = M @ q / (np.linalg.norm(M, axis=1) * np.linalg.norm(q) + 1e-9)       # cosine similarity
        out = []
        for i in np.argsort(-sims)[:k]:
            if sims[i] >= min_score:
                r = cand[i]; out.append({"id": r["id"], "text": r["text"], "meta": r["meta"], "score": float(sims[i])})
        return out

    def all(self, where=None): return [r for r in self.rows.values() if _match(r["meta"], where)]
    def update(self, rid, **meta): self.rows[rid]["meta"].update(meta)
    def delete_where(self, where):
        ids = [r["id"] for r in self.all(where)]
        for i in ids: del self.rows[i]
        return len(ids)
    def save(self, path): json.dump(list(self.rows.values()), open(path, "w"))
    def load(self, path): self.rows = {r["id"]: r for r in json.load(open(path))}


# Notebook cell 21
def show_hits(hits, fields=()):
    for h in hits:
        extra = "  ".join(f"{f}={h['meta'].get(f)}" for f in fields)
        print(f"  {h['score']:.2f} │ {h['text'][:100]}  {extra}")


# Notebook cell 25
def summarize_turns(prev_summary, turns):
    text = "\n".join(f"{t['role']}: {t['content']}" for t in turns)
    m = chat([{"role": "system", "content": "Compress this tutoring conversation into <= 70 words. Keep names, goals, decisions, open questions. Merge with the previous summary."},
              {"role": "user", "content": f"PREVIOUS SUMMARY:\n{prev_summary or '(none)'}\n\nNEW TURNS:\n{text}"}], temperature=0)
    return m.content.strip()


# Notebook cell 25
class WorkingMemory:
    def __init__(self, budget_tokens=1500, keep_last=6):
        self.budget, self.keep_last = budget_tokens, keep_last
        self.turns, self.summary, self.scratch, self.full = [], "", {}, []
    def tokens(self): return (sum(len(t["content"]) for t in self.turns) + len(self.summary)) // 4   # ≈ 4 chars/token
    def add(self, role, content):
        t = {"role": role, "content": content}
        self.turns.append(t); self.full.append({**t, "ts": ts()})
        if self.tokens() > self.budget and len(self.turns) > self.keep_last:
            old, self.turns = self.turns[:-self.keep_last], self.turns[-self.keep_last:]
            self.summary = summarize_turns(self.summary, old)
            print(f"   🗜️  compacted {len(old)} turns → rolling summary ({len(self.summary)//4} tokens)")
    def messages(self):
        pre = [{"role": "system", "content": f"Summary of earlier turns in this session: {self.summary}"}] if self.summary else []
        return pre + self.turns


# Notebook cell 27
DECIDE_PROMPT = """You maintain a memory of facts about ONE user.
Given a NEW fact and EXISTING similar facts (with ids), choose:
  ADD    - the new fact is new information
  UPDATE - the new fact changes/contradicts/refines an existing fact (give that fact's id)
  NOOP   - the new fact is already known
Return JSON: {"action": "ADD"|"UPDATE"|"NOOP", "id": "<existing id or null>"}"""


# Notebook cell 27
class SemanticMemory:
    def __init__(self): self.store = VectorStore("semantic")

    def upsert(self, user_id, fact, category="general"):
        similar = self.store.search(fact, k=3, where={"user_id": user_id, "status": "active"}, min_score=0.40)
        action, target = "ADD", None
        if similar:
            d = llm_json(DECIDE_PROMPT, {"new_fact": fact, "existing": [{"id": h["id"], "fact": h["text"]} for h in similar]},
                         default={"action": "ADD"})
            action, target = str(d.get("action", "ADD")).upper(), d.get("id")
            if action == "UPDATE" and target not in {h["id"] for h in similar}: action = "ADD"
        if action == "NOOP":
            return {"action": "NOOP", "id": target}
        new_id = self.store.add(fact, user_id=user_id, status="active", category=category, replaces=target if action == "UPDATE" else None)
        if action == "UPDATE":
            old = self.store.rows[target]["text"]
            self.store.update(target, status="superseded", superseded_by=new_id, superseded_at=ts())
            return {"action": "UPDATE", "id": new_id, "replaced": old}
        return {"action": "ADD", "id": new_id}

    def render(self, user_id, query=None, k=6):
        active = self.store.all({"user_id": user_id, "status": "active"})
        if len(active) <= k or not query:                       # small profile → just show everything
            return [r["text"] for r in active]
        return [h["text"] for h in self.store.search(query, k=k, where={"user_id": user_id, "status": "active"})]

    def history(self, user_id):
        return [(r["meta"]["created_at"], r["meta"]["status"], r["text"]) for r in self.store.all({"user_id": user_id})]


# Notebook cell 29
class EpisodicMemory:
    HALF_LIFE_DAYS = 7
    def __init__(self): self.store = VectorStore("episodic")

    def record(self, user_id, session_id, summary, outcome="mixed", tags=()):
        return self.store.add(summary, user_id=user_id, session_id=session_id, outcome=outcome, tags=list(tags), ts=CLOCK.now().isoformat())

    def count(self, user_id): return len(self.store.all({"user_id": user_id}))

    def recall(self, user_id, query, k=2):
        hits = self.store.search(query, k=8, where={"user_id": user_id})
        for h in hits:
            age = (CLOCK.now() - datetime.fromisoformat(h["meta"]["ts"])).total_seconds() / 86400
            h["age_days"], h["recency"] = age, 0.5 ** (age / self.HALF_LIFE_DAYS)
            h["final"] = 0.75 * h["score"] + 0.25 * h["recency"]
        return sorted(hits, key=lambda h: -h["final"])[:k]

    def last(self, user_id):
        rows = self.store.all({"user_id": user_id})
        return max(rows, key=lambda r: r["meta"]["ts"]) if rows else None


# Notebook cell 32
class ProceduralMemory:
    def __init__(self): self.store = VectorStore("procedural")

    def learn(self, trigger, steps, scope="global", user_id=None, source="seed"):
        return self.store.add(trigger, scope=scope, user_id=user_id, steps=steps, source=source, wins=0, uses=0)

    def recall(self, user_id, situation, k=2):
        hits = self.store.search(situation, k=6, where={"scope": "global"}, min_score=0.15)
        if user_id: hits += self.store.search(situation, k=6, where={"scope": "student", "user_id": user_id}, min_score=0.15)
        for h in hits:
            m = h["meta"]; rate = (m["wins"] + 1) / (m["uses"] + 2)          # Laplace-smoothed win rate
            h["rank"] = h["score"] * (0.5 + rate)
        return sorted(hits, key=lambda h: -h["rank"])[:k]

    def feedback(self, pid, success):
        m = self.store.rows[pid]["meta"]; self.store.update(pid, uses=m["uses"] + 1, wins=m["wins"] + int(bool(success)))

    @staticmethod
    def fmt(h): return f"WHEN {h['text']} → " + " → ".join(h["meta"]["steps"])


# Notebook cell 32
def seed_procedures(proc):
    proc.learn("student is stuck on an error or exercise", ["give a hint, not the answer", "if still stuck give a second, bigger hint", "only then show the solution and ask them to explain it back"])
    proc.learn("student asks to explain a new concept", ["one-sentence intuition", "smallest runnable code example", "ask them to predict the output before running it"])
    proc.learn("student sounds anxious about an exam or deadline", ["acknowledge the pressure briefly", "prioritise the 3 highest-yield topics", "propose a small next step for today"])


# Notebook cell 35
def chunk_text(text, size=60, overlap=12):
    w, out, i = text.split(), [], 0
    while i < len(w):
        out.append(" ".join(w[i:i + size]))
        if i + size >= len(w): break
        i += size - overlap
    return out


# Notebook cell 35
class ExternalMemory:
    def __init__(self): self.store = VectorStore("external")
    def ingest(self, title, text):
        for n, c in enumerate(chunk_text(text)): self.store.add(c, title=title, chunk=n, scope="global")
    def search(self, query, k=3):
        return self.store.search(query, k=k, where={"scope": "global"})
    @staticmethod
    def fmt(hits): return "\n".join(f"[{h['meta']['title']}#{h['meta']['chunk']}] {h['text']}" for h in hits)


# Notebook cell 35
COURSE_DOCS = {
 "Python Decorators": """A decorator is a function that takes another function and returns a new function that adds behaviour around it.
 The @ syntax is shorthand: writing @timer above def work() is the same as work = timer(work). A typical decorator defines an inner wrapper
 function that accepts *args and **kwargs, does something before or after calling the original function, and returns the result. Use
 functools.wraps on the wrapper so the decorated function keeps its original name and docstring. Common uses are logging, timing, caching and access checks.""",
 "Overfitting and Train/Test Splits": """Overfitting happens when a model memorises the training data instead of learning the underlying pattern. The classic sign is a
 large gap between training accuracy and test accuracy, for example 99 percent on train but 60 percent on test. Always hold out a test set that the model never
 sees during training. To reduce overfitting use more data, simpler models, regularisation, early stopping, or cross-validation to get a more reliable estimate.""",
 "List Comprehensions": """A list comprehension builds a list in one expression: [x * x for x in range(5)] gives [0, 1, 4, 9, 16]. You can add a condition at
 the end, such as [x for x in nums if x % 2 == 0]. Comprehensions are usually faster and more readable than an equivalent for loop with append, but
 deeply nested comprehensions hurt readability, so switch to a normal loop when the logic gets complicated.""",
}


# Notebook cell 38
class ProspectiveMemory:
    def __init__(self): self.store = VectorStore("prospective")

    def add(self, user_id, text, in_days=None, when_topic=None):
        if in_days is None and not when_topic: in_days = 1
        dup = self.store.search(when_topic or text, k=1, where={"user_id": user_id, "status": "pending"}, min_score=0.85)
        if dup: return None                                           # don't schedule the same reminder twice
        due = (CLOCK.now() + timedelta(days=in_days)).isoformat() if in_days is not None else None
        return self.store.add(when_topic or text, user_id=user_id, kind="time" if due else "event", due=due, note=text, status="pending")

    def due(self, user_id):
        rows = self.store.all({"user_id": user_id, "kind": "time", "status": "pending"})
        return [r for r in rows if datetime.fromisoformat(r["meta"]["due"]) <= CLOCK.now()]

    def triggered_by(self, user_id, message, threshold=0.30):
        return self.store.search(message, k=2, where={"user_id": user_id, "kind": "event", "status": "pending"}, min_score=threshold)

    def mark(self, rid, status="delivered"): self.store.update(rid, status=status, delivered_at=ts())


# Notebook cell 41
CONSENT = {}


# Notebook cell 41
def set_consent(user_id, allowed): CONSENT[user_id] = bool(allowed)


# Notebook cell 41
def scrub(text, names=()):
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<EMAIL>", text)
    text = re.sub(r"(?<!\w)\+?\d[\d\s().-]{8,}\d", "<PHONE>", text)
    for n in names:
        if n: text = re.sub(rf"\b{re.escape(n)}\b", "<NAME>", text, flags=re.I)
    return text


# Notebook cell 41
COACH_STYLE_SYSTEM = "You are a concise, encouraging Python/ML coach. Explain with a tiny runnable example."


# Notebook cell 41
JUDGE_PROMPT = """Rate this tutoring reply from 1-5 as TRAINING DATA for a coaching model.
5 = accurate, concise, pedagogically strong (intuition + tiny example), contains NO personal info.
Return JSON {"score": int, "reason": str}."""


# Notebook cell 41
class ParametricCandidates:
    def __init__(self):
        self.store = VectorStore("param"); self.audit = []
    def _log(self, user_id, decision, reason): self.audit.append({"ts": ts(), "user": user_id, "decision": decision, "reason": reason})

    def consider(self, user_id, user_msg, assistant_msg, thumbs_up=None, correction=None, names=()):
        if not CONSENT.get(user_id, False):                                    # GATE 1
            self._log(user_id, "REJECT", "no consent"); return "rejected: no consent"
        u, a = scrub(user_msg, names), scrub(assistant_msg, names)             # GATE 2
        if correction:                                                         # user fixed the answer → preference pair (DPO-style)
            self.store.add(u, user_id=user_id, kind="preference", prompt=u, chosen=scrub(correction, names), rejected=a)
            self._log(user_id, "ACCEPT", "preference pair (user correction)"); return "accepted: preference pair"
        if thumbs_up is False:
            self._log(user_id, "REJECT", "thumbs-down"); return "rejected: thumbs-down"
        j = llm_json(JUDGE_PROMPT, {"user": u, "assistant": a}, default={"score": 0, "reason": "judge failed"})   # GATE 3
        if int(j.get("score", 0)) < 4:
            self._log(user_id, "REJECT", f"judge {j.get('score')}: {j.get('reason')}"); return f"rejected: judge {j.get('score')}"
        if self.store.search(u, k=1, where={"kind": "sft"}, min_score=0.92):    # GATE 4
            self._log(user_id, "REJECT", "near-duplicate"); return "rejected: duplicate"
        self.store.add(u, user_id=user_id, kind="sft", prompt=u, completion=a, judge=int(j["score"]), thumbs_up=thumbs_up)
        self._log(user_id, "ACCEPT", f"sft (judge {j['score']})"); return "accepted: sft example"

    def export(self, path="/content/studybuddy_candidates"):
        os.makedirs(path, exist_ok=True)
        sft = [{"messages": [{"role": "system", "content": COACH_STYLE_SYSTEM}, {"role": "user", "content": r["meta"]["prompt"]},
                             {"role": "assistant", "content": r["meta"]["completion"]}]} for r in self.store.all({"kind": "sft"})]
        pref = [{"prompt": r["meta"]["prompt"], "chosen": r["meta"]["chosen"], "rejected": r["meta"]["rejected"]} for r in self.store.all({"kind": "preference"})]
        with open(f"{path}/sft.jsonl", "w") as f:  [f.write(json.dumps(x) + "\n") for x in sft]
        with open(f"{path}/preferences.jsonl", "w") as f: [f.write(json.dumps(x) + "\n") for x in pref]
        return {"sft_examples": len(sft), "preference_pairs": len(pref), "path": path}


# Notebook cell 44
class MemoryManager:
    """One object that owns every memory store — the single place to save / load / forget."""
    def __init__(self):
        self.working, self.names = {}, {}
        self.semantic, self.episodic, self.procedural = SemanticMemory(), EpisodicMemory(), ProceduralMemory()
        self.external, self.prospective, self.param = ExternalMemory(), ProspectiveMemory(), ParametricCandidates()
        seed_procedures(self.procedural)
        for t, d in COURSE_DOCS.items(): self.external.ingest(t, d)

    def wm(self, user_id, session_id):
        return self.working.setdefault((user_id, session_id), WorkingMemory())

    def stores(self):
        return {"semantic": self.semantic.store, "episodic": self.episodic.store, "procedural": self.procedural.store,
                "external": self.external.store, "prospective": self.prospective.store, "param": self.param.store}


# Notebook cell 45
COACH_SYSTEM = """You are StudyBuddy, a warm, concise Python & ML coach (max ~120 words per reply).
Use the MEMORY sections below to personalise. Never ask for things you already know.
Tools: save_fact (durable facts only: goals, level, preferences, deadlines, constraints — not chit-chat or one-off questions),
search_course_material (concept questions; cite the [source]), set_reminder (when asked to remind or you agree to follow up),
recall_past_sessions (only if the student refers to earlier sessions and EPISODES is not enough).
Follow a matching PLAYBOOK. If REMINDERS are listed, mention them naturally. Never reveal information about other students."""


# Notebook cell 45
CONSOLIDATE_PROMPT = """You are the memory-consolidation module of a tutoring agent. Read the session transcript and extract what is worth remembering.
Return JSON with keys:
 "episode": {"summary": 2-3 factual sentences, "outcome": "progress"|"stuck"|"mixed", "tags": [short topic tags]},
 "facts": [durable facts about the student (goal, level, preferences, deadlines, constraints), short, third person; skip anything in known_facts],
 "procedures": [{"trigger": "situation where this teaching move applies", "steps": ["..."], "scope": "student"|"any"}]  -- ONLY teaching moves that visibly WORKED,
 "reminders": [{"text": "...", "in_days": integer|null, "when_topic": string|null}]  -- only follow-ups explicitly requested or agreed.
Use empty lists when nothing qualifies."""


# Notebook cell 45
class StudyBuddy:
    def __init__(self, mm): self.mm, self.last_turn, self.trace = mm, {}, []

    def register_user(self, user_id, display_name, learn_consent=False):
        self.mm.names[user_id] = display_name; set_consent(user_id, learn_consent)

    def _log(self, icon, text): self.trace.append(f"     {icon} {text}")

    # ---------- deterministic reads ----------
    def build_context(self, user_id, msg):
        mm, parts = self.mm, []
        facts = mm.semantic.render(user_id, msg)
        eps = mm.episodic.recall(user_id, msg, k=2) if mm.episodic.count(user_id) else []
        procs = mm.procedural.recall(user_id, msg, k=2)
        due, evt = mm.prospective.due(user_id), mm.prospective.triggered_by(user_id, msg)
        self._log("📖", f"READ semantic: {len(facts)} facts | episodic: {len(eps)} | procedural: {len(procs)} playbooks")
        parts.append("## STUDENT PROFILE (semantic)\n" + ("\n".join(f"- {f}" for f in facts) or "(nothing known yet)"))
        parts.append("## EPISODES (what happened before)\n" + ("\n".join(f"- [{h['meta']['ts'][:10]}] {h['text']}" for h in eps) or "(none)"))
        parts.append("## PLAYBOOKS (procedural)\n" + ("\n".join("- " + ProceduralMemory.fmt(h) for h in procs) or "(none)"))
        reminders = [r for r in due] + [{"id": h["id"], "meta": h["meta"]} for h in evt]
        if reminders:
            self._log("⏰", f"REMINDERS surfaced: {[r['meta']['note'] for r in reminders]}")
            parts.append("## REMINDERS to deliver now\n" + "\n".join(f"- {r['meta']['note']}" for r in reminders))
            for r in reminders: mm.prospective.mark(r["id"])
        return "\n\n".join(parts), [h["id"] for h in procs]

    # ---------- agent-triggered tools ----------
    def tools_for(self, user_id):
        mm = self.mm
        def save_fact(fact, category="general"):
            r = mm.semantic.upsert(user_id, fact, category); self._log("✍️", f"WRITE semantic → {r['action']}: {fact}"); return r["action"]
        def search_course_material(query):
            hits = mm.external.search(query, k=2); self._log("🔎", f"SEARCH external: {query!r} → {[h['meta']['title'] for h in hits]}")
            return ExternalMemory.fmt(hits) or "no results"
        def set_reminder(text, in_days=None, when_topic=None):
            rid = mm.prospective.add(user_id, text, in_days, when_topic)
            self._log("📌", f"WRITE prospective → {'scheduled' if rid else 'duplicate skipped'}: {text} (in_days={in_days}, topic={when_topic})")
            return "reminder scheduled" if rid else "already scheduled"
        def recall_past_sessions(query):
            hits = mm.episodic.recall(user_id, query, k=3); self._log("🕰️", f"READ episodic (tool): {query!r} → {len(hits)}")
            return "\n".join(f"[{h['meta']['ts'][:10]}] {h['text']}" for h in hits) or "no past sessions"
        S = {"type": "string"}
        return [Tool("save_fact", "Save a durable fact about the student.", {"fact": S, "category": {"type": "string", "enum": ["goal", "preference", "level", "constraint", "personal", "general"]}}, save_fact, ["fact"]),
                Tool("search_course_material", "Search the course library for a concept.", {"query": S}, search_course_material),
                Tool("set_reminder", "Schedule a reminder. Use in_days for time-based, when_topic for 'next time we talk about X'.", {"text": S, "in_days": {"type": "integer"}, "when_topic": S}, set_reminder, ["text"]),
                Tool("recall_past_sessions", "Look up earlier study sessions with this student.", {"query": S}, recall_past_sessions)]

    # ---------- one conversational turn ----------
    def chat(self, user_id, session_id, user_msg, verbose=True):
        self.trace = []; wm = self.mm.wm(user_id, session_id)
        ctx, proc_ids = self.build_context(user_id, user_msg)
        name = self.mm.names.get(user_id, user_id)
        system = {"role": "system", "content": f"{COACH_SYSTEM}\n\nToday: {CLOCK.now():%A %d %b %Y}. You are talking to {name}.\n\n{ctx}"}
        messages = [system, *wm.messages(), {"role": "user", "content": user_msg}]
        reply = run_agent(messages, self.tools_for(user_id))
        wm.add("user", user_msg); wm.add("assistant", reply)
        self.last_turn[(user_id, session_id)] = {"user": user_msg, "assistant": reply, "procs": proc_ids}
        if verbose:
            print(f"👤 {name}: {user_msg}"); [print(t) for t in self.trace]; print(f"🤖 StudyBuddy: {reply}\n")
        return reply

    # ---------- feedback → procedural stats + parametric candidates ----------
    def give_feedback(self, user_id, session_id, thumbs_up=None, correction=None):
        t = self.last_turn[(user_id, session_id)]
        if thumbs_up is not None:
            for pid in t["procs"]: self.mm.procedural.feedback(pid, thumbs_up)
        res = self.mm.param.consider(user_id, t["user"], t["assistant"], thumbs_up, correction, names=[self.mm.names.get(user_id, "")])
        print(f"   👍 feedback ({'up' if thumbs_up else 'down' if thumbs_up is False else 'correction'}) → procedural stats updated; parametric: {res}\n")

    # ---------- end-of-session consolidation ("sleep") ----------
    def end_session(self, user_id, session_id):
        mm, wm = self.mm, self.mm.wm(user_id, session_id)
        transcript = "\n".join(f"{m['role']}: {m['content']}" for m in wm.full)
        data = llm_json(CONSOLIDATE_PROMPT, {"known_facts": mm.semantic.render(user_id), "transcript": transcript}, default={})
        print(f"🌙 CONSOLIDATING session {session_id} for {user_id}")
        ep = data.get("episode") or {}
        if ep.get("summary"):
            mm.episodic.record(user_id, session_id, ep["summary"], ep.get("outcome", "mixed"), ep.get("tags", []))
            print(f"   🗓️  episodic  : {ep['summary']}")
        for f in data.get("facts", []):
            print(f"   🧩 semantic  : {mm.semantic.upsert(user_id, f)['action']} — {f}")
        for p in data.get("procedures", []):
            if p.get("trigger") and p.get("steps"):
                mm.procedural.learn(p["trigger"], p["steps"], "student" if p.get("scope") == "student" else "global", user_id, source="learned")
                print(f"   🛠️  procedural: WHEN {p['trigger']} → {' → '.join(p['steps'])}")
        for r in data.get("reminders", []):
            if r.get("text") and (r.get("in_days") is not None or r.get("when_topic")):
                rid = mm.prospective.add(user_id, r["text"], r.get("in_days"), r.get("when_topic"))
                print(f"   📌 prospective: {'scheduled' if rid else 'already scheduled'} — {r['text']}")
        del mm.working[(user_id, session_id)]            # working memory is ephemeral by design
        print()
        return data


# Notebook cell 65
def save_all(mm, d="/content/memory_db"):
    os.makedirs(d, exist_ok=True)
    for name, st in mm.stores().items(): st.save(f"{d}/{name}.json")
    json.dump({"clock": CLOCK.now().isoformat(), "consent": CONSENT, "names": mm.names, "audit": mm.param.audit}, open(f"{d}/meta.json", "w"))
    return {n: len(s.rows) for n, s in mm.stores().items()}


# Notebook cell 65
def load_all(d="/content/memory_db"):
    new = MemoryManager()
    for name, st in new.stores().items(): st.load(f"{d}/{name}.json")
    meta = json.load(open(f"{d}/meta.json"))
    CLOCK.t = datetime.fromisoformat(meta["clock"]); CONSENT.update(meta["consent"]); new.names = meta["names"]; new.param.audit = meta["audit"]
    return new


# Notebook cell 65
def forget_user(mm, user_id):
    counts = {n: s.delete_where({"user_id": user_id}) for n, s in mm.stores().items()}
    mm.names.pop(user_id, None); CONSENT.pop(user_id, None)
    return counts
