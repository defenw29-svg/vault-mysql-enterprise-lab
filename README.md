# VAULT MYSQL ENTERPRISE LAB v3
> IVAN AJENJO MORALES — Secure Dynamic Credentials Architecture
> 
> <img width="2048" height="1152" alt="image_20260926_180701" src="https://github.com/user-attachments/assets/b0a7ad33-5a03-4a23-a1e5-69eb00e73949" />

## [0] VISIÓN ENTERPRISE
Laboratorio de nivel productivo que elimina secretos estáticos. Zero Trust by design.

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


## Quick Start
`docker compose up --build`
Vault UI: http://localhost:8200 | MySQL: 3307

Autor: IVAN AJENJO MORALES — v3 Enterprise
