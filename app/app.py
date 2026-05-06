import os
import hmac
import hashlib
import json
import base64
import secrets
import string
import smtplib
import ssl as ssl_lib
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

from flask import Flask, render_template, request, redirect, url_for, flash
from ldap3 import Server, Connection, ALL, Tls, MODIFY_REPLACE
from ldap3.utils.hashed import hashed
import ldap3

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# =====================
# Configuración desde variables de entorno
# =====================
TOKEN_SECRET_KEY = os.environ.get("TOKEN_SECRET_KEY", "token-secret-change-me").encode()
LDAP_URI = os.environ.get("LDAP_URI", "ldaps://openldap:636")
LDAP_BIND_DN = os.environ.get("LDAP_BIND_DN", "cn=admin,dc=example,dc=org")
LDAP_BIND_PASSWORD = os.environ.get("LDAP_BIND_PASSWORD", "admin")
LDAP_BASE_DN = os.environ.get("LDAP_BASE_DN", "dc=example,dc=org")
LDAP_USER_BASE_DN = os.environ.get("LDAP_USER_BASE_DN", f"ou=users,{LDAP_BASE_DN}")
CA_CERT_PATH = os.environ.get("CA_CERT_PATH", "/app/certs/ca-cert.pem")

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)

APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")


def get_ldap_connection():
    """Establece conexión LDAPS validando el certificado de la CA."""
    tls = Tls(
        validate=ssl_lib.CERT_REQUIRED,
        ca_certs_file=CA_CERT_PATH,
        version=ssl_lib.PROTOCOL_TLS_CLIENT,
    )
    server = Server(LDAP_URI, use_ssl=True, tls=tls, get_info=ALL)
    conn = Connection(
        server,
        user=LDAP_BIND_DN,
        password=LDAP_BIND_PASSWORD,
        auto_bind=True,
    )
    return conn


def ensure_users_ou(conn):
    """Asegura que exista la OU=users en LDAP."""
    if not conn.search(LDAP_BASE_DN, f"(ou=users)", attributes=["ou"]):
        conn.add(
            LDAP_USER_BASE_DN,
            ["organizationalUnit", "top"],
            {"ou": "users"},
        )


@app.route("/")
def index():
    conn = get_ldap_connection()
    ensure_users_ou(conn)
    conn.search(
        LDAP_USER_BASE_DN,
        "(objectClass=inetOrgPerson)",
        attributes=["uid", "cn", "sn", "mail", "userPassword"],
    )
    users = []
    for entry in conn.entries:
        users.append({
            "uid": entry.uid.value if entry.uid else "",
            "cn": entry.cn.value if entry.cn else "",
            "sn": entry.sn.value if entry.sn else "",
            "mail": entry.mail.value if entry.mail else "",
            "has_password": bool(entry.userPassword.value) if entry.userPassword else False,
        })
    conn.unbind()
    return render_template("index.html", users=users)


@app.route("/crear", methods=["GET", "POST"])
def crear():
    if request.method == "POST":
        uid = request.form["uid"].strip()
        cn = request.form["cn"].strip()
        sn = request.form["sn"].strip()
        mail = request.form["mail"].strip()
        password = request.form["password"]

        if not all([uid, cn, sn, password]):
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for("crear"))

        conn = get_ldap_connection()
        ensure_users_ou(conn)

        dn = f"uid={uid},{LDAP_USER_BASE_DN}"
        password_hash = hashed(ldap3.HASHED_SALTED_SHA, password)
        attributes = {
            "objectClass": ["inetOrgPerson", "top"],
            "uid": uid,
            "cn": cn,
            "sn": sn,
            "mail": mail,
            "userPassword": password_hash,
        }
        if conn.add(dn, attributes=attributes):
            flash("Usuario creado correctamente.", "success")
        else:
            flash(f"Error al crear usuario: {conn.result['description']}", "danger")
        conn.unbind()
        return redirect(url_for("index"))
    return render_template("crear.html")


@app.route("/editar/<uid>", methods=["GET", "POST"])
def editar(uid):
    dn = f"uid={uid},{LDAP_USER_BASE_DN}"
    conn = get_ldap_connection()

    if request.method == "POST":
        cn = request.form["cn"].strip()
        sn = request.form["sn"].strip()
        mail = request.form["mail"].strip()
        password = request.form["password"]

        changes = {
            "cn": [(MODIFY_REPLACE, [cn])],
            "sn": [(MODIFY_REPLACE, [sn])],
            "mail": [(MODIFY_REPLACE, [mail])],
        }
        if password:
            password_hash = hashed(ldap3.HASHED_SALTED_SHA, password)
            changes["userPassword"] = [(MODIFY_REPLACE, [password_hash])]

        if conn.modify(dn, changes):
            flash("Usuario actualizado correctamente.", "success")
        else:
            flash(f"Error al actualizar: {conn.result['description']}", "danger")
        conn.unbind()
        return redirect(url_for("index"))

    conn.search(dn, "(objectClass=inetOrgPerson)", attributes=["uid", "cn", "sn", "mail"])
    if not conn.entries:
        conn.unbind()
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("index"))
    user = conn.entries[0]
    conn.unbind()
    return render_template("editar.html", user=user)


@app.route("/eliminar/<uid>", methods=["POST"])
def eliminar(uid):
    dn = f"uid={uid},{LDAP_USER_BASE_DN}"
    conn = get_ldap_connection()
    if conn.delete(dn):
        flash("Usuario eliminado correctamente.", "success")
    else:
        flash(f"Error al eliminar: {conn.result['description']}", "danger")
    conn.unbind()
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Endpoint para probar autenticación de contraseñas SSHA contra LDAP."""
    if request.method == "POST":
        uid = request.form["uid"].strip()
        password = request.form["password"]

        if not all([uid, password]):
            flash("Ingresa usuario y contraseña.", "danger")
            return redirect(url_for("login"))

        # Buscar el DN del usuario
        conn = get_ldap_connection()
        conn.search(
            LDAP_USER_BASE_DN,
            f"(uid={uid})",
            attributes=["uid"],
        )
        if not conn.entries:
            conn.unbind()
            flash("Usuario o contraseña incorrectos.", "danger")
            return redirect(url_for("login"))

        user_dn = conn.entries[0].entry_dn
        conn.unbind()

        # Intentar autenticar (bind) con las credenciales del usuario
        tls = Tls(
            validate=ssl_lib.CERT_REQUIRED,
            ca_certs_file=CA_CERT_PATH,
            version=ssl_lib.PROTOCOL_TLS_CLIENT,
        )
        server = Server(LDAP_URI, use_ssl=True, tls=tls, get_info=ALL)
        try:
            user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
            user_conn.unbind()
            flash(f"✅ Autenticación exitosa para '{uid}'. La contraseña es correcta.", "success")
        except Exception:
            flash("❌ Autenticación fallida. Usuario o contraseña incorrectos.", "danger")

        return redirect(url_for("login"))

    return render_template("login.html")


# =====================
# Flujo de recuperación
# =====================

def generate_recovery_token(uid: str) -> str:
    """Genera un token HMAC-SHA256 con expiración de 15 minutos."""
    exp = int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())
    payload = {"uid": uid, "exp": exp}
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")
    signature = hmac.new(TOKEN_SECRET_KEY, payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_recovery_token(token: str):
    """Verifica la firma y expiración de un token. Retorna uid o None."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        # Verificar firma
        expected_sig = hmac.new(TOKEN_SECRET_KEY, payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, signature):
            return None
        # Decodificar payload
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_json)
        # Verificar expiración
        if datetime.now(timezone.utc).timestamp() > payload["exp"]:
            return None
        return payload["uid"]
    except Exception:
        return None


def send_email(to_address: str, subject: str, body: str):
    """Envía correo usando STARTTLS."""
    if not all([SMTP_SERVER, SMTP_USER, SMTP_PASSWORD]):
        print("[WARN] SMTP no configurado. Correo no enviado.")
        return False
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_address
    context = ssl_lib.create_default_context()
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to_address], msg.as_string())
        return True
    except Exception as e:
        print(f"[ERROR] Enviando correo: {e}")
        return False


def generate_temp_password(length=12):
    """Genera una contraseña temporal aleatoria."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@app.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        uid = request.form["uid"].strip()
        if not uid:
            flash("Ingresa tu nombre de usuario (UID).", "danger")
            return redirect(url_for("recuperar"))

        conn = get_ldap_connection()
        conn.search(
            LDAP_USER_BASE_DN,
            f"(uid={uid})",
            attributes=["uid", "mail"],
        )
        if not conn.entries:
            conn.unbind()
            flash("Si el usuario existe, recibirás un correo con instrucciones.", "info")
            return redirect(url_for("recuperar"))

        user = conn.entries[0]
        mail = user.mail.value if user.mail else None
        conn.unbind()

        if not mail:
            flash("El usuario no tiene correo registrado.", "danger")
            return redirect(url_for("recuperar"))

        token = generate_recovery_token(uid)
        link = f"{APP_BASE_URL}/restablecer?token={token}"
        body = f"Hola {uid},\n\nPara restablecer tu contraseña, usa el siguiente enlace (válido por 15 minutos):\n\n{link}\n\nSi no solicitaste esto, ignora este mensaje."

        if send_email(mail, "Recuperación de contraseña", body):
            flash("Se ha enviado un enlace de recuperación a tu correo.", "success")
        else:
            # En entorno de demostración, mostramos el enlace en pantalla
            flash(f"Correo no configurado. Enlace de demostración: {link}", "warning")
        return redirect(url_for("recuperar"))

    return render_template("recuperar.html")


@app.route("/restablecer", methods=["GET", "POST"])
def restablecer():
    token = request.args.get("token", "")
    uid = verify_recovery_token(token)
    if not uid:
        flash("El enlace de recuperación es inválido o ha expirado.", "danger")
        return redirect(url_for("recuperar"))

    if request.method == "POST":
        new_password = request.form["password"]
        confirm = request.form["confirm"]
        if new_password != confirm:
            flash("Las contraseñas no coinciden.", "danger")
            return redirect(url_for("restablecer", token=token))

        dn = f"uid={uid},{LDAP_USER_BASE_DN}"
        conn = get_ldap_connection()
        password_hash = hashed(ldap3.HASHED_SALTED_SHA, new_password)
        if conn.modify(dn, {"userPassword": [(MODIFY_REPLACE, [password_hash])]}):
            flash("Contraseña restablecida correctamente.", "success")
        else:
            flash("Error al restablecer la contraseña.", "danger")
        conn.unbind()
        return redirect(url_for("index"))

    return render_template("restablecer.html", uid=uid)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
