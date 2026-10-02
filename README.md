# VAULT MYSQL ENTERPRISE LAB v3
> IVAN AJENJO MORALES — Secure Dynamic Credentials Architecture
> 
> <img width="2048" height="1152" alt="image_20260926_180701" src="https://github.com/user-attachments/assets/b0a7ad33-5a03-4a23-a1e5-69eb00e73949" />

## [0] VISIÓN ENTERPRISE
Laboratorio de nivel productivo que elimina secretos estáticos. Zero Trust by design.

<img width="1920" height="1280" alt="833764345_1131819572637670_5838256882613986189_n-solo-en-3d-titulo-y-autor" src="https://github.com/user-attachments/assets/84fd1b78-6b74-4130-b907-b8dea35eb647" />

### Componentes Core
1.  **Kubernetes Orquestador** [K8S] — Orquesta despliegues, auto-healing, secretos efímeros vía Vault Agent Injector.
2.  **CI/CD Pipeline** [GH Actions] — Build -> Test -> Vault Auth (JWT) -> Deploy. Sin .env en repo.
3.  **HashiCorp Vault Bunker** [VAULT] — Motor database, roles dinámicos, lease & revocation.
4.  **MySQL Motores** [DB] — 2 instancias: primary + replica. Usuarios de corta vida.

### Flujo TTL 15m — 1-2-3
1. App inicia -> Agent solicita credencial -> Vault crea `app_ro_{{timestamp}}`
2. MySQL valida -> App conecta -> Trabaja
3. 15m después -> Lease expira -> Vault ejecuta `REVOKE` -> Credencial muerta. App renueva automáticamente.

```
[CI/CD] --JWT--> [Vault] --CREATE USER--> [MySQL Motores]
   |               ^  | TTL 15m
   +--deploy--> [K8s Pod + Agent Sidecar] --dynamic creds--+
```
### 🚀 Cómo arrancar el laboratorio desde la máquina anfitriona (Tu PC)

Sigue estos pasos en la terminal de tu sistema operativo (Linux, macOS o WSL en Windows) para levantar todo el entorno de confianza cero de forma 100% automatizada:

**1. Clonar el repositorio y acceder al directorio**
```bash
git clone https://github.com
cd laboratorio-empresarial-de-MySQL-de-boveda
```

**2. Asegurar permisos de ejecución para el script automatizador**
Antes de levantar la infraestructura, es necesario otorgarle permisos de ejecución al script local para que Docker pueda ejecutarlo correctamente:
```bash
chmod +x ./scripts/vault-init.sh
```

**3. Desplegar la infraestructura con Docker Compose**
Lanza el entorno completo. Docker Compose se encargará de gestionar el ciclo de vida y el orden de arranque de forma inteligente gracias a las condiciones de salud (*healthchecks*):
```bash
docker compose up --build
```

**4. ¿Qué ocurre entre bastidores de forma automática?**
* **`mysql_master`** inicia su aprovisionamiento y activa su verificación de salud interna.
* **`vault_bunker`** arranca en modo desarrollo, autodesellado y exponiendo el puerto `8200`.
* **`vault_init`** se acopla a la red de Vault, comprueba mediante Netcat que MySQL ya acepta conexiones y valida que la API de Vault responda correctamente.
* El script ejecuta de un tirón el aprovisionamiento: habilita el motor `database`, registra el *plugin* de MySQL, crea las políticas y los roles dinámicos con **TTL de 15 minutos**, e imprime una credencial de prueba en los logs.
* **`app_enterprise_agent`** detecta que la inicialización ha terminado con éxito (`service_completed_successfully`) e inicia de forma segura sin secretos cableados en el repositorio.

### 🔄 Lógica de Reconexión Automática ante el REVOKE de 15 minutos (Python)

En una arquitectura **Zero Trust**, las credenciales tienen un tiempo de vida corto (TTL). A los 15 minutos exactos, Vault ejecutará de forma automática un comando `REVOKE` en MySQL, destruyendo el usuario temporal que usaba nuestra aplicación. Si el código no está preparado, la app se colgará con un error de autenticación.

Para solucionar esto de manera transparente, la aplicación debe capturar el fallo de conexión, recargar las nuevas credenciales efímeras que el Sidecar de Vault actualiza en el archivo `/vault/secrets/database` y reestablecer el pool de conexiones en caliente.

Aquí tienes el código de producción en **Python** listo para implementar en el componente `./app`:

```python
import os
import time
import mysql.connector
from mysql.connector import pooling, Error

DB_HOST = os.getenv("DB_HOST", "mysql-master")
DB_NAME = os.getenv("DB_NAME", "app")
SECRETS_PATH = "/vault/secrets/database"

def cargar_credenciales_vault():
    """Lee y parsea el archivo de secretos inyectado y actualizado por Vault Agent"""
    print("[App] Leyendo credenciales frescas desde Vault Sidecar...")
    creds = {}
    try:
        with open(SECRETS_PATH, "r") as f:
            for linea in f:
                if "export " in linea:
                    # Limpia la línea y extrae la clave/valor (ej: export DB_USER="v-token-...")
                    partes = linea.replace("export ", "").replace('"', '').strip().split("=")
                    if len(partes) == 2:
                        creds[partes[0]] = partes[1]
        return creds.get("DB_USER"), creds.get("DB_PASSWORD")
    except Exception as e:
        print(f"[ERROR] No se pudo leer el archivo de secretos de Vault: {e}")
        return None, None

class EnterpriseConnectionManager:
    def __init__(self):
        self.pool = None
        self.inicializar_pool_conexiones()

    def inicializar_pool_conexiones(self):
        """Crea el pool de conexiones inicial cargando los secretos efímeros"""
        user, password = cargar_credenciales_vault()
        if not user or not password:
            print("[Critical] No hay credenciales disponibles para arrancar.")
            return False

        try:
            # Creamos un pool de conexiones para optimizar el rendimiento
            self.pool = pooling.MySQLConnectionPool(
                pool_name="enterprise_pool",
                pool_size=5,
                host=DB_HOST,
                database=DB_NAME,
                user=user,
                password=password
            )
            print("[App] Pool de conexiones establecido con credenciales de Vault.")
            return True
        except Error as e:
            print(f"[ERROR] Fallo al crear el pool de MySQL: {e}")
            return False

    def ejecutar_consulta(self, query):
        """Ejecuta consultas capturando el REVOKE y aplicando reconexión en caliente"""
        for intento in range(3): # Máximo 3 reintentos de recuperación
            try:
                if not self.pool:
                    self.inicializar_pool_conexiones()
                
                conexion = self.pool.get_connection()
                cursor = conexion.cursor(dictionary=True)
                cursor.execute(query)
                resultado = cursor.fetchall()
                cursor.close()
                conexion.close()
                return resultado

            except (Error, Exception) as e:
                # El código 1045 es "Access Denied" -> Indica que el TTL expiró y Vault ejecutó el REVOKE
                if hasattr(e, 'errno') and e.errno == 1045:
                    print(f"\n[⚠️ ALERT] TTL de 15 min expirado (REVOKE detectado). Intento de recuperación {intento + 1}/3...")
                    # Tiempo de gracia mínimo para asegurar que el Sidecar ya escribió el nuevo par de secretos
                    time.sleep(2) 
                    self.inicializar_pool_conexiones()
                else:
                    print(f"[ERROR] Error de base de datos no relacionado con TTL: {e}")
                    raise e
        
        raise Exception("[Fatal] Incapaz de reconectar con MySQL tras la revocación de Vault.")

# =========================================================================
# PRUEBA DE FLUIDO CONTINUO (Simulación de ciclo de vida)
# =========================================================================
if __name__ == "__main__":
    manager = EnterpriseConnectionManager()
    
    print("[App] Entrando en bucle de trabajo continuo...")
    while True:
        try:
            # Simula transacciones de la app cada 30 segundos
            data = manager.ejecutar_consulta("SELECT NOW() as hora_servidor, USER() as usuario_actual;")
            print(f"[OK] Transacción exitosa -> Usuario en uso: {data[0]['usuario_actual']} | Hora: {data[0]['hora_servidor']}")
            time.sleep(30)
        except KeyboardInterrupt:
            print("[App] Laboratorio finalizado por el usuario.")
            break
```

## Quick Start
`docker compose up --build`
Vault UI: http://localhost:8200 | MySQL: 3307

Autor: IVAN AJENJO MORALES — v3 Enterprise
