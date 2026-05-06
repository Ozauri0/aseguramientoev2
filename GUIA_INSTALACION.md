# Guía de Instalación
## Aseguramiento de Identidad y Gestión de Secretos

> **Requisitos:** Docker Engine + docker-compose instalados.

---

## 1. Preparar secretos

Copia la plantilla y genera claves seguras:
```bash
cp .env.example .env && chmod 600 .env
```

Genera dos claves distintas y pégalas en `.env` (`FLASK_SECRET_KEY` y `TOKEN_SECRET_KEY`):
```bash
openssl rand -hex 32
```

---

## 2. Levantar los servicios

Los certificados PKI se generan automáticamente al primer arranque:
```bash
docker compose up --build -d
```

Verificar que los contenedores estén corriendo:
```bash
docker ps
```

---

## 3. Verificar certificados LDAPS

Extraer el certificado de la CA desde el volumen:
```bash
docker exec openldap cat /container/service/slapd/assets/certs/ca-cert.pem > /tmp/ca-cert.pem
```

Verificar la conexión TLS al puerto 636:
```bash
openssl s_client -connect localhost:636 -CAfile /tmp/ca-cert.pem
```

La respuesta debe mostrar `Verify return code: 0 (ok)`.

---

## 4. Acceder a la aplicación

Abre el navegador en:
```
http://localhost:5000
```

Rutas disponibles: `/crear`, `/editar/<uid>`, `/eliminar/<uid>`, `/login`, `/recuperar`, `/restablecer`.

---

## 5. Verificar hashing de contraseñas en LDAP

Comprueba que las contraseñas se almacenan como `{SSHA}...`:
```bash
docker exec openldap ldapsearch -x -H ldaps://localhost:636 \
  -D "cn=admin,dc=example,dc=org" -w "$(grep LDAP_ADMIN_PASSWORD .env | cut -d= -f2)" \
  -b "ou=users,dc=example,dc=org" userPassword
```

---

## 6. Entrar a los contenedores

Entrar al contenedor de LDAP:
```bash
docker exec -it openldap bash
```

Entrar al contenedor de la app:
```bash
docker exec -it crud_app sh
```

Ver logs en tiempo real:
```bash
docker logs -f crud_app
docker logs -f openldap
```

---

## 7. Comandos útiles

| Acción | Comando |
|--------|---------|
| Ver estado | `docker compose ps` |
| Detener servicios | `docker compose down` |
| Detener y borrar datos | `docker compose down -v` |
| Reconstruir tras cambios | `docker compose up --build -d` |

---

## 8. Checklist final

- [ ] `docker compose up --build -d` levanta sin errores.
- [ ] `openssl s_client` retorna `Verify return code: 0 (ok)`.
- [ ] La app carga en `http://localhost:5000`.
- [ ] Al crear un usuario, la contraseña aparece como `{SSHA}...` en LDAP.
- [ ] El flujo de recuperación genera un enlace válido por 15 minutos.
- [ ] No hay secretos hardcodeados en `app/app.py`.
- [ ] `.env` tiene permisos `600` y está en `.gitignore`.
