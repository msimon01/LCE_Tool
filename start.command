#!/bin/bash
# Start unter macOS per Doppelklick (einmalig: chmod +x start.command)
cd "$(dirname "$0")"
( sleep 4; open http://localhost:8501 ) &
python3 -m streamlit run app.py --server.port 8501
read -p "Das Tool wurde beendet. Eingabetaste drücken ..."
