# Aseguramiento de Identidad y Gestión de Secretos

Proyecto de la actividad formativa: sistema de recuperación de contraseñas con OpenLDAP, LDAPS, tokens HMAC-SHA256 y gestión de secretos por variables de entorno.

---

## Requisitos

- Docker Engine **o** Podman (recomendado rootless)
- docker-compose **o** podman-compose
- OpenSSL (solo para regenerar certificados si es necesario)

---

## Estructura del proyecto

```
.
├── PLAN.md                  # Plan técnico de implementación
├── EXPLICACION.md           # Guía para defensa grupal (matriz + reflexiones)
├── README.md                # Este archivo
├── docker-compose.yml       # Orquestación de servicios
├── .env                     # Secretos (NO subir a git)
├── .env.example             # Plantilla de variables
├── .gitignore
├── pki/
│   ├── gen-certs.sh         # Generador de CA y certificados
│   ├── ca-cert.pem          # Certificado de la CA
│   └── ldap-cert/           # Certificado y clave del servidor LDAP
└── app/
    ├── Dockerfile
    ├── requirements.txt
    ├── app.py
    └── templates/
```

---

## Instrucciones de uso

### 1. Clonar o descargar el proyecto

```bash
cd aseguramiento
```

### 2. Preparar secretos

```bash
cp .env.example .env
chmod 600 .env
```

Edita `.env` con tus credenciales reales. Genera una `SECRET_KEY` segura:

```bash
openssl rand -hex 32
```

Pega el resultado en `TOKEN_SECRET_KEY` y `FLASK_SECRET_KEY`.

> **IMPORTANTE:** `.env` ya está en `.gitignore`. Nunca lo subas al repositorio.

### 3. Generar certificados PKI (ya incluidos)

Si necesitas regenerarlos:

```bash
./pki/gen-certs.sh
```

Esto crea:
- Una **CA propia** (`pki/ca-cert.pem`).
- Un **certificado firmado** para el servidor LDAP (`pki/ldap-cert/`).

### 4. Levantar servicios

**Con Docker:**
```bash
docker compose up --build -d
```

**Con Podman rootless:**
```bash
podman-compose up --build -d
```

### 5. Verificar LDAPS

```bash
openssl s_client -connect localhost:636 -CAfile pki/ca-cert.pem
```

Debe mostrar:
```
Verify return code: 0 (ok)
```

### 6. Acceder a la aplicación

Abre tu navegador en: `http://localhost:5000`

Funciones disponibles:
- **Crear / Editar / Eliminar** usuarios en OpenLDAP.
- **Recuperar contraseña**: genera un token HMAC-SHA256 con expiración de 15 minutos.

### 7. Probar recuperación de contraseña

1. Crea un usuario con correo electrónico.
2. Ve a **Recuperar Contraseña** e ingresa el UID.
3. Si SMTP no está configurado, la app mostrará el enlace en pantalla (modo demostración).
4. Copia el enlace y ábrelo en el navegador antes de 15 minutos.
5. Ingresa una nueva contraseña.

### 8. Verificar hashing en LDAP

```bash
docker exec openldap ldapsearch -x -H ldaps://localhost:636 -D "cn=admin,dc=example,dc=org" -w "SuperSecretLdapAdmin123!" -b "ou=users,dc=example,dc=org" userPassword
```

Debes ver contraseñas en formato `{SSHA}...`.

---

## Consideraciones de seguridad

- **LDAPS obligatorio**: La app rechazará conexiones LDAP sin TLS o con certificado inválido.
- **Validación estricta de certificados**: La app carga `ca-cert.pem` y valida la identidad del servidor.
- **Sin hardcoding**: Credenciales, claves y contraseñas se inyectan por variables de entorno.
- **Permisos**: `.env` debe tener permisos `600`; la app corre como usuario no-root en el contenedor.
- **Token seguro**: HMAC-SHA256 + expiración 15 min + vinculación a UID.

---

## Detener servicios

```bash
docker compose down
```

Para eliminar volúmenes (borra datos LDAP):
```bash
docker compose down -v
```

---

## Documentación adicional

- **Plan de implementación**: ver `PLAN.md`
- **Defensa grupal**: ver `EXPLICACION.md` (incluye Matriz de Trazabilidad y Preguntas de Reflexión)

---

*Actividad formativa – Aseguramiento de Identidad y Gestión de Secretos.*
