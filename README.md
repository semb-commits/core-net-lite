# core-net-lite
**Author: sdev**

Lightweight SQLite simulation of a telecom core network database for educational purposes.  
Users only need to paste a phone number. IMSI, session, and cell assignment are generated automatically.

## Features
- Add subscribers using only a phone number
- Auto-generate IMSI from MSISDN
- Auto-assign subscribers to random cells for session simulation
- View all active subscriber sessions
- Built with Python 3 and SQLite3. No external dependencies

## Installation & Usage
```bash
git clone https://github.com/semb-commits/core-net-lite
cd core-net-lite
python3 core-tool.py
