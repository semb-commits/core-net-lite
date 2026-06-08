# core-net-lite
# Author: sdev
# Educational simulation of core network DB using SQLite

import sqlite3
import random

DB = 'core.db'

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscriber (
        imsi TEXT PRIMARY KEY,
        msisdn TEXT UNIQUE NOT NULL,
        status TEXT DEFAULT 'ACTIVE'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS cell (
        cell_id TEXT PRIMARY KEY,
        location TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS session (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        imsi TEXT NOT NULL,
        cell_id TEXT NOT NULL,
        start_time TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(imsi) REFERENCES subscriber(imsi),
        FOREIGN KEY(cell_id) REFERENCES cell(cell_id)
    )''')

    c.execute("INSERT OR IGNORE INTO cell VALUES ('CELL001','Jakarta Selatan')")
    c.execute("INSERT OR IGNORE INTO cell VALUES ('CELL002','Bandung')")
    c.execute("INSERT OR IGNORE INTO cell VALUES ('CELL003','Surabaya')")
    conn.commit()
    conn.close()

def generate_imsi(msisdn):
    return '51010' + msisdn[-8:]

def add_subscriber():
    msisdn = input("Paste nomor HP: ").strip()
    if not msisdn.isdigit():
        print("[-] Nomor HP harus angka aja")
        return

    imsi = generate_imsi(msisdn)

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO subscriber (imsi, msisdn) VALUES (?,?)", (imsi, msisdn))
        c.execute("SELECT cell_id FROM cell ORDER BY RANDOM() LIMIT 1")
        cell_id = c.fetchone()[0]
        c.execute("INSERT INTO session (imsi, cell_id) VALUES (?,?)", (imsi, cell_id))
        conn.commit()
        print(f"[+] Subscriber ditambah!")
        print(f" MSISDN: {msisdn}")
        print(f" IMSI: {imsi}")
        print(f" Connected to: {cell_id}")
    except sqlite3.IntegrityError:
        print("[-] Nomor ini udah ada di database")
    finally:
        conn.close()

def show_all():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT s.msisdn, s.imsi, c.location, se.start_time
                 FROM session se
                 JOIN subscriber s ON se.imsi = s.imsi
                 JOIN cell c ON se.cell_id = c.cell_id
                 ORDER BY se.start_time DESC''')
    rows = c.fetchall()
    conn.close()

    print("\n=== Data Subscriber ===")
    for row in rows:
        print(f"HP: {row[0]} | IMSI: {row[1]} | Cell: {row[2]} | Time: {row[3]}")

def main():
    init_db()
    while True:
        print("\n=== core-net-lite by sdev ===")
        print("1. Tambah Subscriber dari Nomor HP")
        print("2. Lihat Semua Data")
        print("3. Keluar")
        choice = input("Pilih: ")

        if choice == '1':
            add_subscriber()
        elif choice == '2':
            show_all()
        elif choice == '3':
            break

if __name__ == "__main__":
    main()
