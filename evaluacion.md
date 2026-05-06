# Actividad Formativa · Trabajo en Equipo
## Aseguramiento de Identidad y Gestión de Secretos

**Entornos de Contenedores · Security by Design**

👥 2-3 estudiantes 🛡️ Security by Design ✅ Autoevaluación 📌 Actividad formativa

---

## 📋 1. Descripción de la Actividad

Formar equipos de 2 o 3 estudiantes para realizar una simulación de implementación de un sistema de recuperación de contraseñas. El objetivo es construir un flujo de trabajo profesional donde la seguridad no sea un añadido, sino la base del diseño (Security by Design).

Los equipos deberán conectar una aplicación web con un servidor de identidades centralizado, garantizando la protección de los datos en tránsito, en reposo y la gestión segura de secretos.

### 🎯 Objetivo de aprendizaje

Construir un sistema de recuperación de contraseñas donde una aplicación web CRUD gestione usuarios en OpenLDAP, con cifrado en tránsito (LDAPS), tokens firmados HMAC-SHA256 para recuperación, y protección de secretos mediante variables de entorno.

---

## 🔒 2. Requerimientos Técnicos Obligatorios

### A. Infraestructura y Virtualización Ligera

- **Motor de Contenedores**: Los estudiantes pueden utilizar Docker o Podman (se recomienda explorar el modo rootless en Podman para mayor seguridad).
- **Orquestación**: El despliegue debe realizarse mediante un archivo `docker-compose.yml` (o compatible) que levante:
  1. Un servidor OpenLDAP.
  2. Una aplicación web CRUD para la gestión de usuarios.

### B. Capa de Transporte y Cifrado (PKI)

- **Implementación de LDAPS**: El servidor LDAP debe estar configurado obligatoriamente en el puerto 636.
- **Gestión de Certificados**:
  - Generar una Autoridad Certificadora (CA) propia mediante OpenSSL.
  - Firmar los certificados del servidor con dicha CA.
- **Validación Estricta**: La aplicación CRUD debe cargar el certificado de la CA y validar la identidad del servidor LDAP.

### C. Criptografía en el Proceso de Recuperación

- **Token HMAC-SHA256**: La URL de recuperación debe incluir un token generado con una llave secreta de alta entropía.
- **Atributos del Token**: Debe ser temporal (expiración de 15 minutos) y vinculado al UID del usuario.
- **Hashing en LDAP**: Las contraseñas en el directorio deben almacenarse con esquemas modernos (mínimo SSHA).

### D. Notificación Segura y Gestión de Secretos

- **Envío de Correo**: La contraseña temporal o el enlace debe enviarse mediante una cuenta de correo real configurada con STARTTLS o SMTPs.
- **Secretos (No Hardcoding)**:
  - Las credenciales del correo, la contraseña del administrador de LDAP y la SecretKey del token no deben estar escritas en el código.
  - Deben inyectarse mediante variables de entorno desde el host hacia el contenedor (ej. archivos `.env` protegidos).

### ✅ Buenas prácticas recomendadas

- Usa Podman rootless para reducir el impacto de una eventual fuga en el contenedor.
- Genera la SecretKey del token con `openssl rand -hex 32`.
- Protege el archivo `.env` con permisos `600`.
- Añade `.env` al `.gitignore` para evitar subidas accidentales.

---

## 📊 3. Entregable: Matriz de Trazabilidad y Análisis

Los equipos deben entregar un breve reporte que incluya la siguiente tabla de cumplimiento:

| Control Técnico | Implementación Realizada | Función NIST 2.0 | Art. Ley 21.459 Relacionado |
|---|---|---|---|
| Cifrado de canal | LDAPS / TLS 1.3 | Proteger (PR) | Art. 3 (Interceptación) |
| Integridad de URL | Token HMAC-SHA256 | Identificar (ID) | Art. 2 (Acceso Ilícito) |
| Manejo de Secretos | Variables de entorno / .env | Proteger (PR) | Art. 2 (Exceder permisos) |

*Tabla 1: Matriz de trazabilidad de controles de seguridad*

---

## 🤔 4. Preguntas de Reflexión (Criterio de Ingeniería)

### 1. Responsabilidad Legal

Si el equipo utiliza Podman pero olvida configurar las ACLs en el servidor LDAP, permitiendo que un usuario externo lea todas las contraseñas del directorio: Según la Ley 21.459, ¿quién es el responsable legal del acceso ilícito: el atacante o el equipo por omisión de medidas de seguridad?

### 2. Seguridad de Artefactos

Si al editar el código con `vi` se genera un archivo de intercambio `.swp` que contiene una copia del archivo `.env` y este se sube accidentalmente a un servidor público, explique el riesgo de fuga de secretos y cómo mitigar este error humano.

### 3. Seguridad de Capas

¿Qué ventaja ofrece el uso de Podman rootless frente a Docker en caso de que un atacante logre una ejecución de código remoto (RCE) dentro del contenedor CRUD?

---

## ✅ 5. Pauta de Autoevaluación

### A. Infraestructura

| Criterio | ✅ Lo logré | 🔄 En progreso |
|---|---|---|
| El archivo `docker-compose.yml` levanta correctamente OpenLDAP y la aplicación CRUD | ✅ | |
| Se implementó Podman rootless (opcional pero valorado) | | 🔄 (documentado en README, requiere `podman-compose` instalado) |

### B. Capa de Transporte y Cifrado (PKI)

| Criterio | ✅ Lo logré | 🔄 En progreso |
|---|---|---|
| LDAPS configurado en puerto 636 | ✅ | |
| Se generó una CA propia con OpenSSL | ✅ | |
| Los certificados del servidor están firmados por la CA | ✅ | |
| La aplicación valida estrictamente el certificado (sin deshabilitar TLS) | ✅ | |

### C. Criptografía en el Proceso de Recuperación

| Criterio | ✅ Lo logré | 🔄 En progreso |
|---|---|---|
| Token HMAC-SHA256 implementado en URL de recuperación | ✅ | |
| El token expira después de 15 minutos | ✅ | |
| El token está vinculado al UID del usuario | ✅ | |
| Las contraseñas en LDAP usan SSHA (o superior) | ✅ | |

### D. Notificación Segura y Gestión de Secretos

| Criterio | ✅ Lo logré | 🔄 En progreso |
|---|---|---|
| Envío de correo configurado con STARTTLS o SMTPs | ✅ | |
| No hay secretos hardcodeados en el código fuente | ✅ | |
| Los secretos se inyectan mediante variables de entorno / `.env` | ✅ | |
| El archivo `.env` está en `.gitignore` y tiene permisos `600` | ✅ | |

### E. Análisis y Documentación

| Criterio | ✅ Lo logré | 🔄 En progreso |
|---|---|---|
| Se completó la Matriz de Trazabilidad (Tabla 1) | ✅ | |
| Se respondieron las 3 preguntas de reflexión | ✅ | |
| Se incluyen capturas de pantalla del funcionamiento | | 🔄 (pendiente agregar al repositorio) |
| El repositorio tiene README con instrucciones claras | ✅ | |

### 🎉 Autoevaluación

La actividad está completada en todos los criterios técnicos obligatorios (secciones A, B, C y D). El único ítem pendiente en la sección E es agregar capturas de pantalla del funcionamiento en producción.

---

## 🔬 6. Exploración Personal (Opcional)

Estas actividades no son obligatorias pero profundizan tu aprendizaje:

1. **Seguridad de Contraseñas**: Investigar por qué el almacenamiento en `{CLEARTEXT}` es una violación directa a las normas de cumplimiento internacionales (como PCI-DSS o GDPR).
2. **MFA**: ¿Cómo se podría integrar un segundo factor (OTP) en este flujo de recuperación para fortalecer el AAA?
3. **Auditoría con vi**: Practicar la búsqueda de patrones de error en los archivos de log de `slapd` utilizando comandos de búsqueda avanzada dentro del editor.

---

## 📚 7. Recursos de Apoyo

- OpenSSL: Cómo crear una CA propia y firmar certificados
- Podman rootless vs Docker: Comparativa de seguridad
- HMAC-SHA256: Implementación en Python/Node.js/PHP
- Ley 21.459: Infraestructura Crítica de la Información
- OpenLDAP con TLS: Guía de configuración LDAPS

---

*— Actividad Formativa: Aseguramiento de Identidad y Gestión de Secretos —*
