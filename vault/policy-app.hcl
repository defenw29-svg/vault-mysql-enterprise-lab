# VAULT POLICY — APP v3 — IVAN AJENJO
# Bunker Enterprise - Least Privilege + TTL 15m

path "database/creds/app-ro" {
  capabilities = ["read"]
}

path "database/creds/app-rw" {
  capabilities = ["read"]
}

path "sys/leases/renew" {
  capabilities = ["update"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}

# Deny root and management
path "sys/*" {
  capabilities = ["deny"]
}

# TTL enforcement note: role configured with default_ttl=15m max_ttl=1h
