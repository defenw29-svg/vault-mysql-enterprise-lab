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

## Quick Start
`docker compose up --build`
Vault UI: http://localhost:8200 | MySQL: 3307

Autor: IVAN AJENJO MORALES — v3 Enterprise
