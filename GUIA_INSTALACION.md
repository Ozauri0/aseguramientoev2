# Guía de Instalación Paso a Paso
## Aseguramiento de Identidad y Gestión de Secretos

Esta guía asume que estás en una máquina con **Ubuntu/Debian** (o derivado como Linux Mint, Pop!_OS, Kali, etc.). Si usas otra distribución, los nombres de paquetes pueden cambiar ligeramente.

> **Requisito previo:** Tener acceso a una cuenta con privilegios de `sudo`.

---

## 1. Instalar Docker Engine y docker-compose

### 1.1 Actualizar el sistema e instalar dependencias

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
```

### 1.2 Añadir la clave GPG oficial de Docker

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
```

> Si usas **Debian** en vez de Ubuntu, reemplaza `ubuntu` por `debian` en la URL de arriba.

### 1.3 Configurar el repositorio de Docker

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

### 1.4 Instalar Docker

```bash
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 1.5 Verificar que Docker funciona

```bash
sudo docker run hello-world
```

Debería mostrar un mensaje de éxito de Docker.

### 1.6 (Opcional pero recomendado) Usar Docker sin `sudo`

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Luego cierra sesión y vuelve a abrir la terminal para que los cambios surtan efecto.

### 1.7 Verificar docker-compose

```bash
docker compose version
```

Debe mostrar algo como `Docker Compose version v2.x.x`.

---

## 2. Instalar OpenSSL (si no está instalado)

```bash
sudo apt-get install -y openssl
openssl version
```

---

## 3. Preparar el proyecto

### 3.1 Ir a la carpeta del proyecto

```bash
cd aseguramiento
```

> Asegúrate de que estés en la misma carpeta donde están los archivos `docker-compose.yml`, `README.md`, etc.

### 3.2 Generar secretos seguros

```bash
openssl rand -hex 32
```

Copia el resultado. Ábrelo con un editor (por ejemplo `nano .env`) y pega la clave en `FLASK_SECRET_KEY` y otra distinta en `TOKEN_SECRET_KEY`.

Ejemplo rápido con `sed` (reemplaza `TU_FLASK_KEY` y `TU_TOKEN_KEY` por los valores reales que generaste):

```bash
sed -i 's/cambiar-por-llave-generada-con-openssl-rand-hex-32/TU_FLASK_KEY/' .env
sed -i 's/cambiar-por-otra-llave-generada-con-openssl-rand-hex-32/TU_TOKEN_KEY/' .env
```

### 3.3 Proteger el archivo `.env`

```bash
chmod 600 .env
```

### 3.4 Verificar que `.env` está excluido de git

```bash
cat .gitignore | grep ".env"
```

Debe aparecer `.env` en la salida.

---

## 4. Generar certificados PKI (si no existen)

Los certificados ya vienen generados en el proyecto, pero si necesitas regenerarlos:

```bash
cd pki
chmod +x gen-certs.sh
./gen-certs.sh
cd ..
```

Esto crea:
- `pki/ca-cert.pem` (tu Autoridad Certificadora)
- `pki/ldap-cert/ldap-cert.pem` (certificado del servidor LDAP)
- `pki/ldap-cert/ldap-key.pem` (clave privada del servidor)

---

## 5. Levantar los servicios

### 5.1 Construir e iniciar contenedores

```bash
docker compose up --build -d
```

Esto descarga la imagen de OpenLDAP, construye la imagen de la app Flask y levanta ambos servicios en segundo plano.

### 5.2 Verificar que los contenedores están corriendo

```bash
docker ps
```

Debes ver dos contenedores:
- `openldap`
- `crud_app`

### 5.3 Ver logs en tiempo real (útil para depurar)

```bash
docker logs -f openldap
docker logs -f crud_app
```

Puedes abrir dos terminales para ver ambos al mismo tiempo, o usa `Ctrl+C` para salir de los logs.

---

## 6. Verificaciones de seguridad

### 6.1 Verificar LDAPS en puerto 636

```bash
openssl s_client -connect localhost:636 -CAfile pki/ca-cert.pem
```

Busca al final:
```
Verify return code: 0 (ok)
```

Si dice `0 (ok)`, el certificado es válido y la cadena de confianza funciona.

### 6.2 Verificar que la app responde

Abre tu navegador en:
```
http://localhost:5000
```

O usa `curl`:
```bash
curl -I http://localhost:5000
```

Debe retornar `HTTP/1.1 200 OK`.

### 6.3 Verificar que las contraseñas se almacenan con SSHA

Primero, crea un usuario desde la interfaz web (`http://localhost:5000/crear`).

Luego ejecuta:

```bash
docker exec openldap ldapsearch \
  -x -H ldaps://localhost:636 \
  -D "cn=admin,dc=example,dc=org" \
  -w "SuperSecretLdapAdmin123!" \
  -b "ou=users,dc=example,dc=org" \
  userPassword
```

> **Nota:** Si cambiaste `LDAP_ADMIN_PASSWORD` en el `.env`, usa esa contraseña en el parámetro `-w`.

Deberías ver algo como:
```
userPassword:: {SSHA}xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Eso confirma que las contraseñas NO están en texto plano.

### 6.4 Verificar que no hay secretos hardcodeados en el código

```bash
grep -ri "password\|secret\|key" app/app.py | grep -v "os.environ.get"
```

No debería mostrar valores reales, solo referencias a variables de entorno.

### 6.5 Verificar permisos del archivo `.env`

```bash
ls -la .env
```

Debe mostrar:
```
-rw------- 1 tu_usuario tu_usuario ... .env
```

---

## 7. Probar el flujo de recuperación de contraseña

### 7.1 Crear un usuario con correo

Ve a `http://localhost:5000/crear` y crea un usuario con:
- UID: `jperez`
- CN: `Juan`
- SN: `Pérez`
- Mail: `tu_correo_real@gmail.com` (si vas a probar SMTP real)
- Contraseña: cualquiera

### 7.2 Solicitar recuperación

Ve a `http://localhost:5000/recuperar`, ingresa `jperez` y envía.

**Si configuraste SMTP correctamente en `.env`:**
- Revisa tu bandeja de entrada (y spam).

**Si NO configuraste SMTP (modo demostración):**
- La app mostrará un mensaje de advertencia con el enlace completo.
- Copia ese enlace.

### 7.3 Usar el enlace de recuperación

Pega el enlace en el navegador. Debe llevar a una página para ingresar nueva contraseña.

### 7.4 Verificar expiración del token (opcional)

Para probar que el token expira después de 15 minutos, puedes:

**Opción A (esperar 15 minutos):**
- Simplemente espera y luego intenta usar el mismo enlace.

**Opción B (adelantar el reloj del contenedor):**
```bash
docker exec -u root crud_app date -s "+20 minutes"
```

Luego intenta acceder al enlace. Debe decir: *"El enlace de recuperación es inválido o ha expirado."*

---

## 8. Comandos útiles para el día a día

### Ver estado de los contenedores
```bash
docker compose ps
```

### Detener los servicios
```bash
docker compose down
```

### Detener y borrar datos (LDAP se vacía)
```bash
docker compose down -v
```

### Reconstruir la app después de cambiar código
```bash
docker compose up --build -d
```

### Entrar al contenedor de LDAP para diagnóstico
```bash
docker exec -it openldap bash
```

### Entrar al contenedor de la app
```bash
docker exec -it crud_app bash
```

---

## 9. Opción alternativa: Podman rootless (más seguro)

Si prefieres usar **Podman** en lugar de Docker (modo rootless recomendado por la actividad):

### 9.1 Instalar Podman y podman-compose

```bash
sudo apt-get install -y podman podman-compose
```

### 9.2 Verificar modo rootless

```bash
podman info | grep rootless
```

Debe decir `rootless: true`.

### 9.3 Levantar con podman-compose

```bash
podman-compose up --build -d
```

> **Nota:** La sintaxis es casi idéntica a docker-compose. Podman rootless no requiere daemon ni privilegios de root.

---

## 10. Troubleshooting

### Error: "Cannot connect to the Docker daemon"

Tu usuario no está en el grupo `docker`. Ejecuta:
```bash
sudo usermod -aG docker $USER
```
Luego **cierra sesión y vuelve a entrar** (o reinicia).

### Error: "Port 5000 already in use"

Otra aplicación está usando el puerto 5000. Puedes cambiar el puerto en `docker-compose.yml`:
```yaml
ports:
  - "5001:5000"
```
Y luego acceder a `http://localhost:5001`.

### Error: "Verify return code: 19 (self signed certificate)"

Esto pasa si usas un certificado autofirmado sin la CA. Verifica que estás pasando `-CAfile pki/ca-cert.pem` en el comando `openssl s_client`.

### Error: "SMTP authentication failed"

Si usas Gmail, necesitas una **Contraseña de Aplicación** (no tu contraseña normal). Generarla en: https://myaccount.google.com/apppasswords

También verifica que `SMTP_PORT` sea `587` para STARTTLS.

### Error: "ModuleNotFoundError" dentro del contenedor

El contenedor no se reconstruyó después de cambiar `requirements.txt`. Ejecuta:
```bash
docker compose up --build -d
```

---

## 11. Checklist final de entrega

Antes de presentar tu trabajo, verifica:

- [ ] `docker compose up --build -d` levanta sin errores.
- [ ] `openssl s_client -connect localhost:636 -CAfile pki/ca-cert.pem` retorna `Verify return code: 0 (ok)`.
- [ ] La app web carga en `http://localhost:5000`.
- [ ] Creas un usuario y la contraseña aparece como `{SSHA}...` en LDAP.
- [ ] Solicitas recuperación de contraseña y recibes un enlace (o se muestra en pantalla si no hay SMTP).
- [ ] El enlace funciona dentro de 15 minutos.
- [ ] El enlace caduca después de 15 minutos.
- [ ] No hay contraseñas ni secretos escritos directamente en `app/app.py`.
- [ ] El archivo `.env` tiene permisos `600` y está listado en `.gitignore`.
- [ ] Completaste la **Matriz de Trazabilidad** en `EXPLICACION.md`.
- [ ] Respondiste las **3 Preguntas de Reflexión** en `EXPLICACION.md`.

---

*Guía creada para la actividad formativa: Aseguramiento de Identidad y Gestión de Secretos.*
