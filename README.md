# Memory Observatory · Maya’s AI Learning Buddy

A redesigned learning workspace with **Django + Streamlit frontends**, one **LangGraph backend**, **Mem0 OSS / Cloud**, and **OpenRouter**.

Public Streamlit app: https://ai-learning-buddy-fde.streamlit.app/

## What changed

- Seven named memory cards, with contents and observed READ / WRITE / ADD / UPDATE / ERROR status.
- Per-response operation traces, retrieved records and similarity scores, graph-node durations.
- An original local Lottie animation; reduced-motion support; responsive purple/teal interface.
- Real LangGraph `InMemorySaver` threads and the new notebook's node order: **recall → external → respond → consolidate**.
- Fixed the uploaded notebook's literal backspace characters in regex patterns, which prevented preference/event/reminder detection.
- Answers remain visible when a memory write fails; the UI reports the storage failure instead of silently discarding the turn.
- Latest **stable** Python selection from Python.org, rather than treating the first RSS entry as necessarily stable.
- Server-side key support: teammates can use an owner-configured demo key without seeing it.
- A Django frontend and JSON API with CSRF protection, isolated visitor sessions, idle cleanup, and no credentials in cookies or response payloads.

## Run Streamlit (existing public deployment)

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Streamlit Community Cloud continues to run `app.py` from `main`. It cannot run a Django web server. GitHub changes update the existing Streamlit application after Cloud rebuilds it.

### Owner's demo key — hosted app

Open Streamlit Cloud → app settings → **Secrets** and set:

```toml
OPEN_ROUTER_KEY = "your-openrouter-key"
# Optional: use the exact hosted Mem0 mode from the new notebook:
# MEM0_API_KEY = "your-mem0-platform-key"
```

Do not commit real secrets. `.streamlit/secrets.example.toml` is only a template. A local `.env` does **not** configure your hosted Streamlit app. With an owner key configured, public visitors use its credits. Remove the secret to stop that behavior. Keys typed into the sidebar override the server key for that visitor.

### Local environment

Copy `.env.example` to `.env`, then set `OPEN_ROUTER_KEY`. Local `.env` and Streamlit `secrets.toml` are ignored by Git. For Cloud mode, also provide `MEM0_API_KEY`. The OpenRouter key alone supports **Mem0 OSS**; it does not authenticate Mem0 Platform.

## Run Django

```bash
python -m pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py runserver
```

Open http://127.0.0.1:8000. Click **Connection settings → Start learning session**. If the key is configured in the server environment, visitors can leave the key blank. The Django version has the same engine and memory behavior as Streamlit, plus its own custom HTML/CSS/JS interface.

Production command (one worker is intentional for this in-memory classroom demo):

```bash
python -m gunicorn observatory.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 4 --timeout 180
```

Configure a stable `DJANGO_SECRET_KEY`, exact `DJANGO_ALLOWED_HOSTS`, HTTPS origin(s) in `DJANGO_CSRF_TRUSTED_ORIGINS`, and `DJANGO_SECURE_COOKIES=1` behind HTTPS. The Dockerfile and Procfile can be used with a Python/container hosting service. The Django version is **not automatically hosted at the Streamlit URL**.

### API

| Route | Method | Behavior |
|---|---|---|
| `/api/state` | GET | Current session state and seven cards |
| `/api/connect` | POST | Create an isolated lab; key may come from server environment |
| `/api/chat` | POST | `{"question":"..."}` → response, stages, memory records, trace |
| `/api/new-thread` | POST | Clear working context by starting a new thread; retain memories |
| `/api/refresh` | POST | Refresh Mem0 records, including pending Cloud writes |
| `/api/complete-task` | POST | `{"id":"..."}` → manually mark an intention complete |
| `/health/` | GET | Server health |

POST requests require the session's CSRF cookie and `X-CSRFToken` header. User IDs are generated server-side and cannot be selected in request payloads. The public deployment is an educational demo, not a production multi-tenant platform.

## Seven categories

| Type | Backend meaning |
|---|---|
| **Parametric** | OpenRouter model invoked; pretrained weights unchanged |
| **Working** | LangGraph checkpointed messages for this lesson |
| **Semantic** | Mem0 fact storage, search and native memory events |
| **Episodic** | Reported study experiences and heuristically classified Mem0 records |
| **Procedural** | Explicit preferences/rules included in the response prompt |
| **External** | Real public API lookup, source URL and timestamp |
| **Prospective** | Pending intentions and manual completion; **no notification scheduler** |

Cards show state. Only the trace shows executed operations. Retrieval is not proof of model attention. Labels are application-level heuristics, not seven independent Mem0 products. Mem0 Cloud processing can be asynchronous; ADD_CALL is not represented as a confirmed new record.

## Class walkthrough

Introduce Maya → report a struggle → set a teaching preference → request an explanation → recall yesterday → fetch current Python version → record a future intention → ask about current conversation → report mastery. Then start a **new conversation** and ask what the buddy remembers: working context resets, retained memory does not.

You can freely discuss any learning topic; the sample prompts are shortcuts only. The model may misremember or fail to extract a fact. Inspect records and errors rather than assuming success.

## Notebook alignment and files

`reference/Memory_Observatory.ipynb` preserves your new notebook's source cells, with outputs removed. `observatory_core.py` adapts its globals into isolated instances. Graph order, checkpointer, memory classifications, registries and operation dashboard match its architecture. Differences are documented above; this is a web-app adaptation, not a claim of byte-identical notebook execution. The notebook's FastAPI demonstration is replaced by the requested Django API.

- `observatory_core.py`: shared graph, Mem0 adapter, registries, traces.
- `app.py`: Streamlit entry point, used by the existing public URL.
- `observatory/`: Django settings, routes and API views.
- `templates/index.html`, `static/observatory/`: custom Django UI and original Lottie asset.
- `ui_parts.py`: shared card/trace markup for Streamlit.
- `test_observatory.py`: lifecycle, failure handling, stable-version selection, isolation and CSRF tests.
- `notebook_core.py`, `engine.py`, `mem0_backend.py`, `test_memory.py`: retained first-notebook implementation for comparison; no longer the active UI backend.

## State lifetime and limits

Local registries and LangGraph checkpoints are in memory. Each OSS lab has a separate temporary Qdrant directory. New conversation retains memory; reconnecting creates a new lab. Django expires idle labs after two hours when new connections arrive, capped at 40 active labs. A server restart clears in-process state. Cloud records remain under the generated visitor ID, but automatic identity recovery across browser restarts is not implemented. Downloads are inspection exports, not restoration backups. Mem0 inspector reads at most 100 records per refresh, suitable for a small class demo. No background reminders, durable cross-device identity, model training, or production authentication is implied.

Mem0 optional NLP/BM25 packages are not needed for vector recall. Provider rate limits, paid embeddings, missing credits and free-model availability can still block live requests; errors are shown without exposing secrets. The CDN supplies the Lottie player; the JSON animation itself is local and original. Chat remains functional if that animation cannot load.

## Validate

```bash
python -m unittest -v test_observatory test_memory
python manage.py check
```
