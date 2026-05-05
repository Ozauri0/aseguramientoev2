# Plan de Implementación
## Aseguramiento de Identidad y Gestión de Secretos

### 1. Arquitectura General

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Usuario       │────────▶│  Aplicación CRUD │────────▶│   OpenLDAP      │
│   (Navegador)   │◀────────│  (Flask/Python)  │◀────────│   (LDAPS:636)   │
└─────────────────┘  HTTPS  └──────────────────│   TLS   └─────────────────┘
                              │
                              ▼
                        ┌──────────────────┐
                        │   Servidor de    │
                        │   Correo SMTP    │
                        │   (STARTTLS)     │
                        └──────────────────┘
```

### 2. Componentes y Tecnologías

| Componente | Tecnología | Justificación |
|------------|-----------|---------------|
| Contenedores | Docker / Podman | Virtualización ligera, portabilidad |
| Orquestación | docker-compose.yml | Declarativo, reproduceble |
| Directorio | OpenLDAP (osixia/openldap) | Estándar de industria para identidades |
| App CRUD | Flask + ldap3 + Python 3.11 | Ligera, fácil de entender y auditar |
| PKI | OpenSSL | Control total de la cadena de confianza |
| Token Recovery | HMAC-SHA256 (secrets/hmac) | Integridad y autenticidad comprobable |
| Correo | smtplib + STARTTLS | Cifrado en tránsito para notificaciones |
| Secretos | Variables de entorno + `.env` | Separación de código y configuración sensible |

### 3. Estructura de Directorios

```
.
├── PLAN.md                  # Este archivo
├── EXPLICACION.md           # Guía para defensa grupal
├── docker-compose.yml       # Orquestación de servicios
├── .env                     # Secretos (NO versionar)
├── .env.example             # Plantilla de variables
├── .gitignore               # Excluir secretos
├── pki/
│   ├── gen-certs.sh         # Script de generación de CA y certs
│   ├── ca-cert.pem          # Certificado de la CA
│   └── ldap-cert/           # Certificados del servidor LDAP
├── openldap/
│   └── certs/               # Certificados montados en el contenedor
└── app/
    ├── Dockerfile
    ├── requirements.txt
    ├── app.py                 # Aplicación Flask
    └── templates/
        ├── base.html
        ├── index.html
        ├── recuperar.html
        └── restablecer.html
```

### 4. Pasos de Implementación

#### Paso 1: Infraestructura Base
1. Crear `docker-compose.yml` con servicios `openldap` y `app`.
2. Configurar red bridge interna para comunicación contenedor-contenedor.
3. Definir volúmenes persistentes para datos LDAP.

#### Paso 2: PKI y LDAPS
1. Ejecutar `pki/gen-certs.sh` para crear:
   - Clave privada de la CA.
   - Certificado autofirmado de la CA.
   - CSR y certificado firmado para el servidor LDAP (CN=openldap).
2. Montar certificados en el contenedor OpenLDAP.
3. Configurar OpenLDAP para escuchar en `636` con `LDAP_TLS_VERIFY_CLIENT=try`.
4. Asegurar que la aplicación cargue `ca-cert.pem` y valide el certificado del servidor (`validate=ssl.CERT_REQUIRED`).

#### Paso 3: Aplicación CRUD
1. Implementar con Flask rutas para:
   - Listar usuarios (READ).
   - Crear usuario (CREATE).
   - Editar usuario (UPDATE).
   - Eliminar usuario (DELETE).
2. Conectar a OpenLDAP vía `ldap3` usando `use_ssl=True` y `tls=Tls(validate=ssl.CERT_REQUIRED, ca_certs_file='/app/certs/ca-cert.pem')`.
3. Almacenar contraseñas con `{SSHA}` utilizando `ldap3.utils.hashed.hashed_password`.

#### Paso 4: Flujo de Recuperación Segura
1. **Solicitud**: Usuario ingresa su `uid` o `mail`.
2. **Generación de Token**:
   - Payload: `{"uid": "usuario", "exp": timestamp+900}`.
   - Firma: `HMAC-SHA256(payload, SECRET_KEY)`.
   - URL: `/restablecer?token=<payload_base64>.<firma_hex>`.
3. **Envío**: Correo con el enlace usando SMTP + STARTTLS.
4. **Validación**:
   - Verificar firma HMAC.
   - Verificar expiración (`exp`).
   - Verificar que el `uid` existe en LDAP.
5. **Restablecimiento**: Generar contraseña temporal aleatoria, hashear con SSHA, actualizar LDAP y notificar por correo.

#### Paso 5: Gestión de Secretos
1. Crear `.env` con permisos `600`.
2. Inyectar variables vía `env_file` en `docker-compose.yml`.
3. Agregar `.env` a `.gitignore`.
4. Documentar en `EXPLICACION.md` el principio de **menor privilegio** y **separación de secretos**.

#### Paso 6: Documentación y Entregables
1. Completar Matriz de Trazabilidad (Tabla 1) en `EXPLICACION.md`.
2. Responder las 3 Preguntas de Reflexión con argumentos legales y técnicos.
3. Incluir instrucciones claras en `README.md` (levantar, probar, verificar).

### 5. Criterios de Validación

- [ ] `docker compose up` levanta ambos servicios sin errores.
- [ ] `openssl s_client -connect localhost:636 -CAfile pki/ca-cert.pem` devuelve `Verify return code: 0 (ok)`.
- [ ] La app puede crear un usuario y la contraseña aparece como `{SSHA}...` en LDAP.
- [ ] El token de recuperación caduca a los 15 minutos.
- [ ] No existen strings de contraseñas ni secretos en el código fuente.
- [ ] El archivo `.env` tiene permisos `600` y está en `.gitignore`.

### 6. Consideraciones de Seguridad Adicionales

- **Podman rootless**: Si se usa Podman, ejecutar `podman-compose up` sin privilegios de root. Los contenedores corren con UID del usuario host, reduciendo el impacto de un escape.
- **Reducción de superficie de ataque**: La app corre como usuario no-root dentro del contenedor (`USER app`).
- **No downgrade TLS**: Rechazar conexiones LDAP que no presenten certificado válido.
- **Auditoría**: Los logs de slapd deben mostrar conexiones en puerto 636 y binds con éxito/fraude.

---

*Plan creado para la actividad formativa: Aseguramiento de Identidad y Gestión de Secretos.*
