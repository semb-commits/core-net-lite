# core-net-lite
# Author: sdev
# Educational simulation of core network DB using SQLite

import sqlite3
import random
import time
import hashlib

DB = 'core.db'
MCC_MNC = "51010" # Indonesia Telkomsel dummy

BASE_COORDS = {
    "Jakarta": (-6.2000, 106.8166),
    "Bandung": (-6.9175, 107.6191),
    "Surabaya": (-7.2575, 112.7521),
    "Medan": (3.5952, 98.6722),
    "Semarang": (-6.9667, 110.4167)
}

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
        city TEXT NOT NULL,
        location TEXT NOT NULL,
        tac TEXT NOT NULL,
        latitude REAL,
        longitude REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS session (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        imsi TEXT NOT NULL,
        cell_id TEXT NOT NULL,
        s_tmsi TEXT,
        start_time TEXT DEFAULT CURRENT_TIMESTAMP,
        end_time TEXT,
        FOREIGN KEY(imsi) REFERENCES subscriber(imsi),
        FOREIGN KEY(cell_id) REFERENCES cell(cell_id)
    )''')

    # Index biar query cepet kalau data udah banyak
    c.execute("CREATE INDEX IF NOT EXISTS idx_imsi ON session(imsi)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_city ON cell(city)")

    conn.commit()
    conn.close()

def seed_cells_kota(kota="Jakarta", n=150):
    if kota not in BASE_COORDS:
        print(f"[-] Kota {kota} belum ada di database")
        return

    lat0, lon0 = BASE_COORDS[kota]
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("DELETE FROM cell WHERE city =?", (kota,))

    cells = []
    for i in range(1, n+1):
        cell_id = f"{kota[:3].upper()}{i:03d}"
        lat = round(lat0 + random.uniform(-0.15, 0.15), 4)
        lon = round(lon0 + random.uniform(-0.15, 0.15), 4)
        tac = f"01{random.randint(0xA0, 0xFF):X}"
        location = f"{kota} Area {i}"
        cells.append((cell_id, kota, location, tac, lat, lon))

    c.executemany("INSERT INTO cell VALUES (?,?,?,?,?,?)", cells)
    conn.commit()
    conn.close()
    print(f"[+] {n} cell untuk {kota} berhasil di-generate")

def generate_imsi(msisdn):
    return MCC_MNC + msisdn[-8:]

def generate_s_tmsi(imsi):
    h = hashlib.md5(imsi.encode()).hexdigest()
    return "0x" + h[:8].upper()

def print_s1ap_log(event, imsi, cell_id, tac, location, city, s_tmsi=None):
    print("\n[S1AP Message]")
    print(f" Procedure Code: id-{event}")
    print(f" protocolIEs:")
    print(f" Item 0: id-eNB-UE-S1AP-ID")
    print(f" eNB-UE-S1AP-ID: 0x{random.randint(1, 9999):04X}")
    print(f" Item 1: id-IMSI")
    print(f" IMSI: {imsi}")
    print(f" Item 2: id-TAI")
    print(f" TAI")
    print(f" plmn-ID: {MCC_MNC[:3]} {MCC_MNC[3:]}")
    print(f" TAC: 0x{tac}")
    print(f" Item 3: id-EUTRAN-CGI")
    print(f" EUTRAN-CGI")
    print(f" plmn-ID: {MCC_MNC[:3]} {MCC_MNC[3:]}")
    print(f" cell-ID: {cell_id}")
    print(f" Item 4: id-Location")
    print(f" City: {city}, Location: {location}")
    if s_tmsi:
        print(f" Item 5: id-S-TMSI")
        print(f" S-TMSI: {s_tmsi}")
    print("[/S1AP]\n")

def add_subscriber():
    msisdn = input("Paste nomor HP: ").strip()
    if not msisdn.isdigit():
        print("[-] Nomor HP harus angka aja")
        return

    imsi = generate_imsi(msisdn)
    s_tmsi = generate_s_tmsi(imsi)

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        loading("Registering subscriber")
        c.execute("INSERT INTO subscriber (imsi, msisdn) VALUES (?,?)", (imsi, msisdn))

        loading("Selecting target cell")
        c.execute("SELECT cell_id, location, tac, city FROM cell ORDER BY RANDOM() LIMIT 1")
        cell_id, location, tac, city = c.fetchone()

        loading("Creating session")
        c.execute("INSERT INTO session (imsi, cell_id, s_tmsi) VALUES (?,?,?)", (imsi, cell_id, s_tmsi))
        conn.commit()

        print(f"\n[+] Attach Success!")
        print(f" MSISDN : {msisdn}")
        print(f" IMSI : {imsi}")
        print(f" Cell ID : {cell_id}")
        print(f" Location: {city} - {location}")
        print_s1ap_log("initialUEMessage", imsi, cell_id, tac, location, city, s_tmsi)

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
    print_s1ap_log("UEContextRelease", imsi, "-", "-")

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
    c.execute("SELECT cell_id, location, tac, city FROM cell ORDER BY RANDOM() LIMIT 1")
    new_cell, new_loc, new_tac, new_city = c.fetchone()

    loading("Executing handover")
    c.execute("UPDATE session SET end_time = CURRENT_TIMESTAMP WHERE imsi =? AND end_time IS NULL", (imsi,))
    c.execute("INSERT INTO session (imsi, cell_id, s_tmsi) VALUES (?,?,?)",
              (imsi, new_cell, generate_s_tmsi(imsi + str(random.randint(1,999)))))
    conn.commit()
    conn.close()
    print(f"[+] Handover success!")
    print_s1ap_log("handoverNotification", imsi, new_cell, new_tac, new_loc, new_city)

def show_all():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT s.msisdn, s.imsi, s.status, c.city, c.location, c.tac, c.latitude, c.longitude,
                        se.cell_id, se.s_tmsi, se.start_time, se.end_time
                 FROM session se
                 JOIN subscriber s ON se.imsi = s.imsi
                 JOIN cell c ON se.cell_id = c.cell_id
                 ORDER BY se.start_time DESC LIMIT 100''')
    rows = c.fetchall()
    conn.close()

    print("\n=== Session Log (Last 100) ===")
    print(f"{'MSISDN':<15} {'IMSI':<15} {'Status':<9} {'City':<12} {'Location':<18} {'TAC':<6} {'Cell':<9} {'S-TMSI':<12} {'Start'}")
    print("-"*125)
    for row in rows:
        print(f"{row[0]:<15} {row[1]:<15} {row[2]:<9} {row[3]:<12} {row[4]:<18} {row[5]:<6} {row[8]:<9} {row[9]:<12} {row[10]}")

def city_menu():
    print("\n=== Pilih Kota untuk Generate Cell ===")
    for i, kota in enumerate(BASE_COORDS.keys(), 1):
        print(f"{i}. {kota}")
    print("6. Kembali")
    choice = input("Pilih: ")

    kota_list = list(BASE_COORDS.keys())
    if choice.isdigit() and 1 <= int(choice) <= len(kota_list):
        kota = kota_list[int(choice)-1]
        n = input(f"Jumlah cell untuk {kota} [default 150]: ").strip()
        n = int(n) if n.isdigit() else 150
        seed_cells_kota(kota, n)
    elif choice == "6":
        return
    else:
        print("[-] Pilihan tidak valid")

def main():
    init_db()
    while True:
        print("\n=== core-net-lite by sdev ===")
        print("1. Attach Subscriber")
        print("2. Detach Subscriber")
        print("3. Handover")
        print("4. Lihat Semua Data")
        print("5. Generate Cell per Kota")
        print("6. Keluar")
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
            city_menu()
        elif choice == '6':
            print("Exiting...")
            break
        else:
            print("[-] Pilihan tidak valid")

if __name__ == "__main__":
    main()
