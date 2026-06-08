# core-net-lite
# Author: sdev
# Educational simulation of core network DB using SQLite

import sqlite3
import random
import time
import hashlib
import hmac

DB = 'core.db'

OPERATORS = {
    "1": {"name": "Telkomsel", "mcc_mnc": "51010"},
    "2": {"name": "Indosat", "mcc_mnc": "51001"},
    "3": {"name": "XL Axiata", "mcc_mnc": "51011"},
    "4": {"name": "Smartfren", "mcc_mnc": "51009"},
    "5": {"name": "Tri", "mcc_mnc": "51089"}
}

BASE_COORDS = {
    "Jakarta": (-6.2000, 106.8166),
    "Bandung": (-6.9175, 107.6191),
    "Surabaya": (-7.2575, 112.7521),
    "Medan": (3.5952, 98.6722),
    "Semarang": (-6.9667, 110.4167)
}

MCC_MNC = "51010" # Default, bakal di-override pas startup
K_KEY = "1234567890ABCDEF1234567890ABCDEF" # Dummy Ki key

def loading(msg="Processing"):
    print(f"{msg}", end="", flush=True)
    for _ in range(3):
        time.sleep(0.3)
        print(".", end="", flush=True)
    print(" Done!")

def select_operator():
    print("\n=== Pilih Operator ===")
    for k, v in OPERATORS.items():
        print(f"{k}. {v['name']} - {v['mcc_mnc']}")
    choice = input("Pilih: ")
    op = OPERATORS.get(choice, OPERATORS["1"])
    print(f"[+] Operator terpilih: {op['name']} [{op['mcc_mnc']}]")
    return op['mcc_mnc']

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscriber (
        imsi TEXT PRIMARY KEY,
        msisdn TEXT UNIQUE NOT NULL,
        ki TEXT NOT NULL,
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
        rand TEXT,
        xres TEXT,
        kasme TEXT,
        start_time TEXT DEFAULT CURRENT_TIMESTAMP,
        end_time TEXT,
        FOREIGN KEY(imsi) REFERENCES subscriber(imsi),
        FOREIGN KEY(cell_id) REFERENCES cell(cell_id)
    )''')
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

def milenage(ki, rand):
    xres = hmac.new(bytes.fromhex(ki), bytes.fromhex(rand), hashlib.md5).hexdigest()[:16]
    kasme = hmac.new(bytes.fromhex(ki), bytes.fromhex(rand + xres), hashlib.sha256).hexdigest()[:32]
    return xres, kasme

def print_s1ap_log(event, **kwargs):
    print("\n[S1AP Message]")
    print(f" Procedure Code: id-{event}")
    print(f" protocolIEs:")
    for i, (k, v) in enumerate(kwargs.items(), 0):
        print(f" Item {i}: id-{k}")
        print(f" {k}: {v}")
    print("[/S1AP]\n")

def nas_auth_procedure(imsi, ki):
    print("\n--- NAS Authentication Procedure ---")
    rand = format(random.getrandbits(128), '032x').upper()
    xres, kasme = milenage(ki, rand)

    print_s1ap_log("downlinkNASTransport",
                   NAS_Message="Authentication Request",
                   RAND=rand)

    res = input("Masukkan RES [enter untuk auto-OK]: ").strip()
    if not res:
        res = xres

    if res == xres:
        print("[+] Authentication Success")
        print_s1ap_log("uplinkNASTransport",
                       NAS_Message="Authentication Response",
                       RES=res)
        return rand, xres, kasme
    else:
        print("[-] Authentication Failed")
        return None, None, None

def nas_smc_procedure():
    print("\n--- NAS Security Mode Command ---")
    print_s1ap_log("downlinkNASTransport",
                   NAS_Message="Security Mode Command",
                   Ciphering="AES128",
                   Integrity="NIA2")
    print("[+] Security Mode Complete")
    print_s1ap_log("uplinkNASTransport",
                   NAS_Message="Security Mode Complete")

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
        c.execute("INSERT OR IGNORE INTO subscriber (imsi, msisdn, ki) VALUES (?,?,?)", (imsi, msisdn, K_KEY))

        c.execute("SELECT ki FROM subscriber WHERE imsi =?", (imsi,))
        ki = c.fetchone()[0]

        loading("Selecting target cell")
        c.execute("SELECT cell_id, location, tac, city FROM cell ORDER BY RANDOM() LIMIT 1")
        cell_id, location, tac, city = c.fetchone()

        rand, xres, kasme = nas_auth_procedure(imsi, ki)
        if not rand:
            print("[-] Attach rejected: Auth failed")
            return

        nas_smc_procedure()

        loading("Creating session")
        c.execute("INSERT INTO session (imsi, cell_id, s_tmsi, rand, xres, kasme) VALUES (?,?,?,?,?,?)",
                  (imsi, cell_id, s_tmsi, rand, xres, kasme))
        conn.commit()

        print(f"\n[+] Attach Success!")
        print(f" MSISDN : {msisdn}")
        print(f" IMSI : {imsi}")
        print(f" PLMN-ID: {MCC_MNC[:3]} {MCC_MNC[3:]}")
        print(f" Cell ID : {cell_id}")
        print(f" Location: {city} - {location}")
        print_s1ap_log("initialUEMessage",
                       IMSI=imsi,
                       PLMN_ID=f"{MCC_MNC[:3]} {MCC_MNC[3:]}",
                       TAC=tac,
                       CellID=cell_id,
                       S_TMSI=s_tmsi)

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
    print_s1ap_log("UEContextRelease", Cause="User Detach", IMSI=imsi)

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
    c.execute("INSERT INTO session (imsi, cell_id, s_tmsi, rand, xres, kasme) VALUES (?,?,?,?,?,?)",
              (imsi, new_cell, generate_s_tmsi(imsi + str(random.randint(1,999))), None, None, None))
    conn.commit()
    conn.close()
    print(f"[+] Handover success!")
    print_s1ap_log("handoverNotification",
                   IMSI=imsi,
                   PLMN_ID=f"{MCC_MNC[:3]} {MCC_MNC[3:]}",
                   TargetCell=new_cell,
                   TAC=new_tac,
                   City=new_city)

def show_all():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT s.msisdn, s.imsi, s.status, c.city, c.location, c.tac,
                        se.cell_id, se.s_tmsi, se.start_time
                 FROM session se
                 JOIN subscriber s ON se.imsi = s.imsi
                 JOIN cell c ON se.cell_id = c.cell_id
                 WHERE se.end_time IS NULL
                 ORDER BY se.start_time DESC LIMIT 100''')
    rows = c.fetchall()
    conn.close()
    print(f"\n=== Active Sessions - PLMN {MCC_MNC[:3]} {MCC_MNC[3:]} ===")
    print(f"{'MSISDN':<15} {'IMSI':<15} {'Status':<9} {'City':<12} {'Location':<18} {'TAC':<6} {'Cell':<9} {'S-TMSI'}")
    print("-"*110)
    for row in rows:
        print(f"{row[0]:<15} {row[1]:<15} {row[2]:<9} {row[3]:<12} {row[4]:<18} {row[5]:<6} {row[6]:<9} {row[7]}")

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
    global MCC_MNC
    MCC_MNC = select_operator()
    init_db()
    while True:
        print(f"\n=== core-net-lite by sdev | Operator: {MCC_MNC} ===")
        print("1. Attach Subscriber")
        print("2. Detach Subscriber")
        print("3. Handover")
        print("4. Lihat Active Sessions")
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
