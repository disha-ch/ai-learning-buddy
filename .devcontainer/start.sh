#!/usr/bin/env bash
set -euo pipefail
if ! curl --fail --silent http://localhost:8501/_stcore/health >/dev/null; then
  nohup python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true > /tmp/learning-buddy-streamlit.log 2>&1 < /dev/null &
fi
