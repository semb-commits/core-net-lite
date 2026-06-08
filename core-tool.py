# core-net-lite
# Author: sdev
# Educational simulation of core network DB using SQLite

import sqlite3
import random
import time

DB = 'core.db'

def loading(msg="Processing"):
    print(f"{msg}", end="", flush=True)
    for _ in range(3):
        time.sleep(0.3)
        print(".", end="", flush=True)
    print(" Done!")

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
        location TEXT NOT NULL,
        latitude REAL,
        longitude REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS session (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        imsi TEXT NOT NULL,
        cell_id TEXT NOT NULL,
        start_time TEXT DEFAULT CURRENT_TIMESTAMP,
        end_time TEXT,
        FOREIGN KEY(imsi) REFERENCES subscriber(imsi),
        FOREIGN KEY(cell_id) REFERENCES cell(cell_id)
    )''')

    # Tambah lokasi + koordinat dummy
    cells = [
        ('CELL001','Jakarta Selatan', -6.2615, 106.8106),
        ('CELL002','Bandung', -6.9175, 107.6191),
        ('CELL003','Surabaya', -7.2575, 112.7521)
    ]
    c.executemany("INSERT OR IGNORE INTO cell VALUES (?,?,?,?)", cells)
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
        loading("Registering subscriber")
        c.execute("INSERT INTO subscriber (imsi, msisdn) VALUES (?,?)", (imsi, msisdn))

        loading("Selecting target cell")
        c.execute("SELECT cell_id, location FROM cell ORDER BY RANDOM() LIMIT 1")
        cell_id, location = c.fetchone()

        loading("Creating session")
        c.execute("INSERT INTO session (imsi, cell_id) VALUES (?,?)", (imsi, cell_id))
        conn.commit()

        print(f"\n[+] Attach Success!")
        print(f" MSISDN : {msisdn}")
        print(f" IMSI : {imsi}")
        print(f" Cell ID : {cell_id}")
        print(f" Location: {location}")

    except sqlite3.IntegrityError:
        print("[-] Nomor ini udah ada di database")
    finally:
        conn.close()

def detach_subscriber():
    msisdn = input("Masukkan nomor HP yang mau di-detach: ").strip()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT imsi FROM subscriber WHERE msisdn =?", (msisdn,))
    row = c.fetchone()

    if not row:
        print("[-] Nomor tidak ditemukan")
        conn.close()
        return

    imsi = row[0]
    loading("Detaching subscriber")
    c.execute("UPDATE session SET end_time = CURRENT_TIMESTAMP WHERE imsi =? AND end_time IS NULL", (imsi,))
    c.execute("UPDATE subscriber SET status = 'DETACHED' WHERE imsi =?", (imsi,))
    conn.commit()
    conn.close()
    print(f"[+] Subscriber {msisdn} berhasil di-detach")

def handover():
    msisdn = input("Masukkan nomor HP yang mau handover: ").strip()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT imsi FROM subscriber WHERE msisdn =? AND status = 'ACTIVE'", (msisdn,))
    row = c.fetchone()

    if not row:
        print("[-] Nomor tidak aktif atau tidak ditemukan")
        conn.close()
        return

    imsi = row[0]
    c.execute("SELECT cell_id, location FROM cell ORDER BY RANDOM() LIMIT 1")
    new_cell, new_loc = c.fetchone()

    loading("Executing handover")
    c.execute("UPDATE session SET end_time = CURRENT_TIMESTAMP WHERE imsi =? AND end_time IS NULL", (imsi,))
    c.execute("INSERT INTO session (imsi, cell_id) VALUES (?,?)", (imsi, new_cell))
    conn.commit()
    conn.close()
    print(f"[+] Handover success! Sekarang connect ke {new_cell} - {new_loc}")

def show_all():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT s.msisdn, s.imsi, s.status, c.location, c.latitude, c.longitude,
                        se.cell_id, se.start_time, se.end_time
                 FROM session se
                 JOIN subscriber s ON se.imsi = s.imsi
                 JOIN cell c ON se.cell_id = c.cell_id
                 ORDER BY se.start_time DESC''')
    rows = c.fetchall()
    conn.close()

    print("\n=== Session Log ===")
    print(f"{'MSISDN':<15} {'IMSI':<15} {'Status':<9} {'Location':<18} {'Cell':<8} {'Lat':<10} {'Lon':<10} {'Start':<20} {'End'}")
    print("-"*120)
    for row in rows:
        end = row[8] if row[8] else "-"
        print(f"{row[0]:<15} {row[1]:<15} {row[2]:<9} {row[3]:<18} {row[6]:<8} {row[4]:<10} {row[5]:<10} {row[7]:<20} {end}")

def main():
    init_db()
    while True:
        print("\n=== core-net-lite by sdev ===")
        print("1. Attach Subscriber")
        print("2. Detach Subscriber")
        print("3. Handover")
        print("4. Lihat Semua Data")
        print("5. Keluar")
        choice = input("Pilih: ")

        if choice == '1':
            add_subscriber()
        elif choice == '2':
            detach_subscriber()
        elif choice == '3':
            handover()
        elif choice == '4':
            show_all()
        elif choice == '5':
            print("Exiting...")
            break
        else:
            print("[-] Pilihan tidak valid")

if __name__ == "__main__":
    main()
