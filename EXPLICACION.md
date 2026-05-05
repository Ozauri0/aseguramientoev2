# Explicación para Defensa Grupal
## Aseguramiento de Identidad y Gestión de Secretos

---

## 1. Visión General del Sistema

Este proyecto implementa un sistema de **recuperación de contraseñas** basado en los principios de **Security by Design**. No se trata de añadir seguridad al final, sino de construir cada componente asumiendo que puede ser atacado.

**Flujo resumido:**
1. La aplicación web CRUD se comunica con OpenLDAP exclusivamente por **LDAPS (636)**.
2. Toda la cadena de confianza PKI es controlada por nosotros: generamos nuestra propia **CA** y firmamos el certificado del servidor.
3. Cuando un usuario olvida su contraseña, se genera un **token HMAC-SHA256** temporal (15 min) vinculado a su UID.
4. El enlace se envía por correo electrónico usando **STARTTLS**.
5. Ningún secreto (contraseñas, claves API, tokens) está hardcodeado; todo se inyecta por **variables de entorno**.

---

## 2. Decisiones de Arquitectura

### 2.1 Contenedores y Orquestación

- **Docker / Podman**: Elegimos contenedores porque ofrecen aislamiento de procesos sin el overhead de una VM completa. Si se usa **Podman en modo rootless**, el contenedor corre con el UID del usuario del host. Esto significa que, incluso si un atacante escapa del contenedor, no tiene privilegios de root en el host.
- **docker-compose.yml**: Define la infraestructura como código. Cualquier miembro del equipo puede reproducir el entorno con un solo comando.

### 2.2 PKI y LDAPS

**¿Por qué no usar LDAP en puerto 389 sin cifrar?**
Porque las credenciales viajarían en texto plano. En un entorno de red compartida (como un datacenter o incluso una red Wi-Fi interna), un atacante con acceso a la interfaz de red podría capturar las contraseñas con un simple sniffing.

**¿Por qué crear nuestra propia CA en lugar de usar Let's Encrypt?**
Porque este es un entorno interno/contenedorizado. Let's Encrypt emite certificados para dominios públicos. Aquí controlamos toda la cadena de confianza: generamos la CA, distribuimos su certificado a la aplicación, y exigimos que el certificado del servidor esté firmado por esa CA. Esto evita ataques de **hombre en el medio (MitM)**.

### 2.3 Tokens HMAC-SHA256

**¿Por qué no usar JWT?**
JWT es un estándar válido, pero para este caso queríamos demostrar comprensión profunda del mecanismo criptográfico. HMAC-SHA256 nos permite:
- **Integridad**: Si un atacante modifica el UID o la expiración en el token, la firma no coincide.
- **Autenticidad**: Solo quien posee la `SECRET_KEY` puede generar un token válido.
- **Ligereza**: No requiere librerías pesadas; está implementado con la biblioteca estándar `hmac` de Python.

**¿Por qué 15 minutos?**
Es un balance entre usabilidad (dar tiempo al usuario de revisar su correo) y seguridad (limitar la ventana de exposición si el enlace es interceptado).

### 2.4 Hashing SSHA en LDAP

**¿Por qué SSHA y no MD5/SHA1?**
MD5 y SHA1 están rotos para propósitos de hashing de contraseñas (son demasiado rápidos y vulnerables a ataques de colisión). SSHA (Salted SHA) introduce un **salt** aleatorio por cada contraseña, lo que defeated tablas arcoíris y fuerza al atacante a recalcular hashes para cada usuario individualmente.

### 2.5 Gestión de Secretos

**¿Por qué variables de entorno?**
Porque separan la configuración sensible del código fuente. Si el repositorio es público o se filtra, el atacante no obtiene credenciales. Además, en un entorno de producción real, estas variables pueden ser inyectadas por un **Secret Manager** (HashiCorp Vault, AWS Secrets Manager, etc.) en lugar de un archivo `.env`.

---

## 3. Matriz de Trazabilidad y Cumplimiento

| Control Técnico | Implementación Realizada | Función NIST 2.0 | Art. Ley 21.459 Relacionado |
|---|---|---|---|
| **Cifrado de canal** | LDAPS / TLS 1.3 entre app y OpenLDAP | **Proteger (PR)** | Art. 3 (Interceptación): Prohibición de interceptar datos en tránsito sin autorización. Al cifrar el canal, incluso si hay interceptación, los datos permanecen confidenciales. |
| **Integridad de URL** | Token HMAC-SHA256 con expiración y UID | **Identificar (ID)** | Art. 2 (Acceso Ilícito): La firma HMAC permite identificar si un enlace fue alterado. Un token inválido se rechaza, evitando que un atacante genere enlaces de recuperación para cuentas ajenas. |
| **Manejo de Secretos** | Variables de entorno / `.env` con permisos 600 | **Proteger (PR)** | Art. 2 (Exceder permisos): Al no hardcodear credenciales, se reduce el riesgo de que un atacante que acceda al código fuente (lectura no autorizada) pueda escalar privilegios hacia otros sistemas (LDAP, correo). |

**Relación con NIST Cybersecurity Framework 2.0:**
- **Proteger (PR)**: Controles diseñados para salvaguardar la información. Aquí entran el cifrado TLS, el hashing de contraseñas y la gestión de secretos.
- **Identificar (ID)**: Comprender el contexto de riesgo. El token HMAC permite *identificar* si una solicitud de recuperación es legítima o fraudulenta.

**Relación con Ley 21.459 (Infraestructura Crítica de la Información):**
- El artículo 2 tipifica el acceso ilícito y el exceder permisos. Nuestra implementación no solo previene, sino que también deja evidencia técnica (logs de token inválido, conexiones rechazadas) que puede usarse en una investigación.
- El artículo 3 sanciona la interceptación. El uso de LDAPS mitiga la materialidad del daño si ocurre una interceptación pasiva.

---

## 4. Preguntas de Reflexión

### 4.1 Responsabilidad Legal

> *Si el equipo utiliza Podman pero olvida configurar las ACLs en el servidor LDAP, permitiendo que un usuario externo lea todas las contraseñas del directorio: Según la Ley 21.459, ¿quién es el responsable legal del acceso ilícito: el atacante o el equipo por omisión de medidas de seguridad?*

**Respuesta:**

Ambos tienen responsabilidad, pero de naturaleza diferente:

1. **El atacante** comete un delito tipificado en el **Art. 2 de la Ley 21.459**: el *acceso ilícito* a un sistema informático. Su responsabilidad es **penal**.

2. **El equipo (o la organización)** incurre en una responsabilidad **civil y regulatoria** por **omisión de medidas de seguridad**. La Ley 21.459 y su reglamento exigen a los gestores de infraestructuras críticas implementar controles de seguridad proporcionales al riesgo. Si una auditoría demuestra que el equipo no configuró ACLs básicas (una medida de *due diligence* elemental), pueden enfrentar:
   - Multas por incumplimiento regulatorio.
   - Responsabilidad civil por daños a terceros si las contraseñas filtradas se usan para comprometer otros sistemas.
   - Acciones disciplinarias internas o contractuales.

**Analogía**: Si dejas la puerta de tu casa abierta y alguien entra a robar, el ladrón es penalmente culpable, pero tu aseguradora puede negar el pago por negligencia grave. En ciberseguridad, la omisión de controles básicos suele ser considerada **negligencia inexcusable**.

---

### 4.2 Seguridad de Artefactos

> *Si al editar el código con `vi` se genera un archivo de intercambio `.swp` que contiene una copia del archivo `.env` y este se sube accidentalmente a un servidor público, explique el riesgo de fuga de secretos y cómo mitigar este error humano.*

**Respuesta:**

**Riesgo:**
Un archivo `.swp` (swap) de `vi`/`vim` es una copia temporal del archivo en edición. Si se estaba editando `.env`, el `.swp` puede contener:
- Credenciales del administrador LDAP.
- `SECRET_KEY` para firmar tokens.
- Contraseña del servidor SMTP.

Si este archivo se expone públicamente (por ejemplo, en un servidor web mal configurado o en un repositorio git público), un atacante puede:
1. Firmar tokens de recuperación arbitrarios (con `SECRET_KEY`).
2. Acceder al directorio LDAP como administrador.
3. Usar el SMTP para phishing desde la cuenta oficial.

**Mitigaciones:**

| Capa | Mitigación |
|---|---|
| **Preventiva** | Configurar `.gitignore` para excluir `*.swp`, `*.swo`, `.env`. |
| **Preventiva** | Usar `set noswapfile` en `~/.vimrc` o configurar `directory` para swap en `/tmp` privado. |
| **Preventiva** | No editar archivos de secretos directamente en servidores; usar Secret Managers o inyección de variables. |
| **Detectiva** | Escaneos automáticos de repositorios (GitHub Secret Scanning, TruffleHog, GitLeaks). |
| **Correctiva** | Rotación inmediata de todos los secretos expuestos (cambiar contraseñas, regenerar `SECRET_KEY`). |

---

### 4.3 Seguridad de Capas

> *¿Qué ventaja ofrece el uso de Podman rootless frente a Docker en caso de que un atacante logre una ejecución de código remoto (RCE) dentro del contenedor CRUD?*

**Respuesta:**

La ventaja principal es la **contención del impacto del escape de contenedor**.

**Docker (modo root por defecto):**
- El daemon de Docker corre como root.
- Los contenedores, aunque aislados, interactúan con un daemon privilegiado.
- Un RCE combinado con una vulnerabilidad de escape (por ejemplo, `runc` exploit, monturas de kernel, o capacidades peligrosas como `CAP_SYS_ADMIN`) puede dar al atacante **root en el host**.
- El atacante puede entonces:
  - Acceder a todos los demás contenedores.
  - Leer/modificar cualquier archivo del host.
  - Instalar persistencia (backdoors) a nivel del sistema operativo.

**Podman rootless:**
- No hay daemon central. El contenedor corre como el **UID/GID del usuario** que lo ejecuta.
- El kernel de Linux ve al proceso del contenedor como un proceso normal del usuario.
- Incluso si el atacante escapa, solo tiene los permisos de ese usuario en el host.
- No puede acceder a archivos de otros usuarios, ni a procesos privilegiados, ni instalar módulos del kernel.
- Además, Podman usa **user namespaces** por defecto, mapeando el root interno del contenedor a un UID no privilegiado en el host.

**Conclusión**: Podman rootless aplica el principio del **menor privilegio** a la capa de virtualización. Un RCE ya es grave, pero con Podman rootless se convierte en un incidente **contenido**; con Docker mal configurado, puede convertirse en un **compromiso total del host**.

---

## 5. Mensajes Clave para la Defensa

1. **"No confiamos en la red"**: Por eso ciframos todo, incluso dentro del mismo host (LDAPS en vez de LDAP).
2. **"No confiamos en el código"**: Los secretos nunca están en el código; el código es público por diseño, los secretos son privados por necesidad.
3. **"No confiamos en el usuario"**: El token expira en 15 minutos y está firmado. Un enlace robado del historial del navegador o interceptado de la red tiene vida limitada y no puede ser modificado.
4. **"No confiamos ni en nosotros mismos"**: Por eso usamos controles de prevención de errores humanos (`.gitignore`, permisos `600`, escaneo de secretos).

---

## 6. Checklist de Demostración (Para la defensa en vivo)

- [ ] Mostrar `docker compose ps` o `podman ps` con ambos contenedores activos.
- [ ] Mostrar `openssl s_client -connect localhost:636 -CAfile pki/ca-cert.pem` con `Verify return code: 0`.
- [ ] Crear un usuario en la app y verificar en LDAP que la contraseña está en `{SSHA}`.
- [ ] Solicitar recuperación de contraseña, mostrar el token en los logs y explicar sus componentes.
- [ ] Esperar 15 min (o adelantar el reloj del contenedor) y demostrar que el token expira.
- [ ] Mostrar `ls -la .env` con permisos `600` y confirmar que está en `.gitignore`.
- [ ] Explicar qué pasaría si cambiamos a Docker rootful vs Podman rootless.

---

*Documento preparado para la defensa grupal de la actividad formativa.*
