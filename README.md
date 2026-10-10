# 🧠 Maya’s AI Learning Buddy

**Streamlit + LangGraph + Mem0 OSS + OpenRouter.** An inspectable memory lab based on the supplied FDE Memory Masterclass notebook.

## Publish a public UI

The repository is deployment-ready; a GitHub repository alone does not host Python. Choose one:

- **Streamlit Community Cloud:** sign in at https://share.streamlit.io, create an app using repository `disha-ch/ai-learning-buddy`, branch `main`, file `app.py`, Python 3.11, and public visibility. No secrets need to be added; visitors enter their own OpenRouter keys.
- **Render:** use the included `render.yaml` as a Blueprint. It creates a public Python web service on the free plan (availability subject to your account). Visitor memory is isolated per Streamlit session, with a separate temporary Qdrant database. Free-service restarts clear temporary storage; export snapshots first.

Do not set a shared OpenRouter key for a public demo. There is no authentication or permanent user account system: the persona is Maya, but each visitor has a separate lab. Do not use this educational app for sensitive production records.

## Open the real UI

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/disha-ch/ai-learning-buddy?quickstart=1)

1. Click **Open in GitHub Codespaces**, then create the codespace. GitHub may show account usage/billing limits.
2. Wait for dependency installation. Streamlit starts automatically. Open **Ports → 8501 → Open in Browser** if it does not open automatically; keep the port private.
3. Paste your **OpenRouter API key** in the sidebar. Choose **Mem0 OSS (tutor version)** and click **Connect / restart lab**.
4. Send the guided turns, then open **Memory inspector** to see actual retrieved records and Mem0 ADD / UPDATE / DELETE events.

No Mem0 API key, OpenAI API key, or separate Qdrant server is required. Mem0 OSS runs locally; its LLM and embedding requests use OpenRouter. The key is never committed or included in memory exports.

### Run locally (Python 3.11+)
```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
Open http://localhost:8501. Enter the key in the sidebar. The UI never exposes a server-owned key or persists visitor keys to disk. `openrouter/free` may be rate-limited or lack a suitable available model; select another tool-capable OpenRouter model if necessary. Embeddings use `openai/text-embedding-3-small` (1536 dimensions), which may incur a small charge.

## What uses Mem0?

| Memory | Implementation | What the inspector shows |
|---|---|---|
| Semantic | **Mem0 OSS**, local Qdrant, history SQLite | Real `add` events, search results/scores, stored facts, update history |
| Episodic | Notebook `EpisodicMemory` | Reported study experiences, milestones, similarity and recency |
| Procedural | Notebook `ProceduralMemory` | Teaching playbooks, explicit preferences, feedback stats |
| Working | Notebook `WorkingMemory` | Recent messages, rolling summary, scratchpad |
| External | Notebook course RAG + Python.org tool | Tool calls, course sources, actual live lookup result |
| Prospective | Notebook `ProspectiveMemory` | Pending/delivered reminders and due dates |
| Parametric | Chat model's pretrained knowledge | Generation happens; weights never change. Optional candidates are not training. |

**Mem0 is the default semantic backend.** Choose “Notebook from-scratch” to compare the original ADD / UPDATE / NOOP implementation. Memory types describe behavior, not separate Mem0 product features. The UI labels memory that was *retrieved/included*; it cannot prove the model causally relied on a particular memory.

## Nine-turn exploration

1. Introduce Maya → inspect Mem0 facts.
2. Report yesterday’s nested-loop struggle → inspect an episode.
3. Ask for simple examples without jargon → inspect a student-specific procedure.
4. Ask about functions → pretrained knowledge with the explanation preference in context.
5. Ask about yesterday’s struggle → inspect retrieved episodes and scores.
6. Ask for the latest Python version → verify `latest_python_version` actually ran; failed lookup must not produce a guessed version.
7. Ask for a reminder tomorrow → inspect the prospective record.
8. Ask what you are discussing → inspect working-memory messages.
9. Report mastery → inspect updated current facts plus the milestone episode.

Then **End session + consolidate** and ask again to distinguish working memory from retained memory. **Advance one day**, then send “Hi” to trigger due reminders. Reminders are delivered during chat, not through a background notification service.

Use **Download memory snapshot** before closing. Restore with the same backend and embedding model. Mem0 restore recreates facts, with new IDs; it does not preserve original Mem0 update-history entries. Snapshots include up to 1,000 Mem0 facts, suitable for this small lab. Forgetting removes Maya’s current records, working memory and UI traces; downloaded snapshots remain separate copies and local Mem0 audit history may remain in the temporary database.

## Code walkthrough

- `notebook_core.py`: original definitions and constants copied verbatim, with source-cell references. Demonstration executions and installs omitted.
- `source_map.json`: notebook cell mapping.
- `engine.py`: four-node LangGraph: capture → retrieve → respond → inspect. Calls the original tool loop and memory classes.
- `mem0_backend.py`: adapted notebook Part 12 concept using current Mem0 2.2.1 APIs, explicit OpenRouter configuration, user-filtered retrieval, Qdrant storage and native history.
- `app.py`: actual Streamlit chat and memory inspector.
- `test_memory.py`: offline lifecycle tests; no live model quality claims.
- `.devcontainer/`: Codespaces setup and private Streamlit port.
- `Colab_Launcher.ipynb`: optional Colab launch instructions.

The notebook originally contains no LangGraph graph. Its bare `OpenAI()` client does not use its `OPEN_ROUTER_KEY` setting, and `openrouter/free` is not its embedding model. The adapter fixes both. Immediate episode/preference capture is an explicit addition so the nine-turn example is observable before end-of-session consolidation. Episode timestamps are ingestion time; relative event dates stay in the text. Mem0 native updates replace the notebook's semantic superseding logic in Mem0 mode.

## Scope and limitations

Educational app with isolated browser sessions, suitable for a small public demo with visitor-supplied keys; not a hardened production service. Each connection gets an isolated temporary Mem0/Qdrant directory. It retains facts across “End session” but a new connection starts a new lab; export snapshots for portability. Other stores and graph state are in process memory. There is no LangGraph persistent checkpointer, hosted deployment, scheduler or model fine-tuning. Failed turns roll back notebook state, but **Mem0 writes may already have committed**; inspect before retrying. Memory extraction/tool use is model-dependent. Basic candidate scrubbing is not comprehensive anonymization. Server resources/files may remain until process/environment cleanup. Keep API keys and personal snapshots out of Git.

## Tests
```bash
python -m unittest -v
```

References: [Mem0 OSS configuration](https://docs.mem0.ai/open-source/configuration), [LangGraph StateGraph](https://reference.langchain.com/python/langgraph/graph/state/StateGraph), [OpenRouter embeddings](https://openrouter.ai/docs/api/api-reference/embeddings/create-embeddings).
