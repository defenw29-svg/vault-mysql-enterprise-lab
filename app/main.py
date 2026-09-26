"""
Enterprise App v3 — IVAN AJENJO
Vault Dynamic Credentials + MySQL Motores
TTL 15m Flow 1-2-3
"""
import os, time, hvac
import mysql.connector

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "root-ivan-v3")

def get_dynamic_creds():
    client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    # 1. Solicita credencial dinámica
    creds = client.secrets.database.generate_credentials(name="app-ro")
    print(f"[1] Creds generadas: {creds['data']['username']} TTL={creds['lease_duration']}s")
    # 2. Conecta
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=3306,
        user=creds['data']['username'],
        password=creds['data']['password'],
        database="enterprise_db"
    )
    return conn, creds

def main():
    while True:
        conn, lease = get_dynamic_creds()
        cursor = conn.cursor()
        cursor.execute("SELECT NOW(), USER();")
        print(f"[2] Conectado OK -> {cursor.fetchone()}")
        # 3. TTL 15m - esperar y revocar
        ttl = lease['lease_duration']
        print(f"[3] Esperando TTL {ttl}s antes de revocar...")
        time.sleep(min(ttl, 900))
        conn.close()
        print("[!] Lease expirado, renovando...")

if __name__ == "__main__":
    main()
