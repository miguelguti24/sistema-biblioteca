from flask import Flask, jsonify, request
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

app = Flask(__name__)
app.json.ensure_ascii = False 

@app.after_request
def agregar_cabeceras_cors(response):
    """
    Permite que el frontend pueda hacer peticiones a esta API sin ser bloqueado por el navegador.
    """
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


@app.route("/<path:ruta>", methods=["OPTIONS"])
def manejar_opciones_cors(ruta):
    """El navegador manda esta petición 'preflight' antes de POST/PUT/DELETE."""
    return "", 204

DB_NAME = "biblioteca.db"

# Clave secreta usada para firmar los tokens JWT.

SECRET_KEY = "clave-secreta-biblioteca-2026"
TOKEN_EXPIRACION_HORAS = 8

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        fecha_registro TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS libros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        autor TEXT NOT NULL,
        genero TEXT,
        anio INTEGER,
        disponible INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS prestamos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        libro_id INTEGER NOT NULL,
        fecha_prestamo TEXT NOT NULL,
        fecha_devolucion TEXT,
        estado TEXT NOT NULL DEFAULT 'activo',
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
        FOREIGN KEY (libro_id) REFERENCES libros(id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()

def error(mensaje, codigo=400):
    return jsonify({"error": mensaje}), codigo



# AUTENTICACIÓN CON JWT

def generar_token(usuario_id, email):
    """Crea un token JWT firmado, válido por TOKEN_EXPIRACION_HORAS."""
    payload = {
        "usuario_id": usuario_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRACION_HORAS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def token_requerido(f):
    """
    Decorador que protege un endpoint: exige un token JWT válido
    en el header 'Authorization: Bearer <token>'.
    
    """
    @wraps(f)
    def decorador(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return error("Falta el token de autenticación (header Authorization: Bearer <token>)", 401)

        token = auth_header.split(" ", 1)[1]

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return error("El token expiró, inicia sesión de nuevo", 401)
        except jwt.InvalidTokenError:
            return error("Token inválido", 401)

        request.usuario_actual = payload
        return f(*args, **kwargs)

    return decorador

@app.get("/")
def home():
    return jsonify({
        "mensaje": "API de Gestión de Biblioteca funcionando",
        "recursos": ["/auth/registro", "/auth/login", "/libros", "/usuarios", "/prestamos"]
    })



@app.post("/auth/registro")
def registro():
    """Crea una cuenta de usuario nueva, con la contraseña encriptada."""
    datos = request.get_json(silent=True) or {}
    nombre = datos.get("nombre")
    email = datos.get("email")
    password = datos.get("password")

    if not nombre or not email or not password:
        return error("nombre, email y password son obligatorios")
    if len(password) < 6:
        return error("La contraseña debe tener al menos 6 caracteres")

    password_hash = generate_password_hash(password)

    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO usuarios (nombre, email, password_hash, fecha_registro) VALUES (?,?,?,?)",
            (nombre, email, password_hash, datetime.now().strftime("%Y-%m-%d"))
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return error("El email ya está registrado")
    conn.close()

    token = generar_token(nuevo_id, email)
    return jsonify({
        "mensaje": "Usuario registrado correctamente",
        "id": nuevo_id,
        "token": token
    }), 201


@app.post("/auth/login")
def login():
    """Verifica email y contraseña, y devuelve un token JWT si son correctos."""
    datos = request.get_json(silent=True) or {}
    email = datos.get("email")
    password = datos.get("password")

    if not email or not password:
        return error("email y password son obligatorios")

    conn = get_connection()
    usuario = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    conn.close()

    if usuario is None or not check_password_hash(usuario["password_hash"], password):
        return error("Email o contraseña incorrectos", 401)

    token = generar_token(usuario["id"], usuario["email"])
    return jsonify({
        "mensaje": "Inicio de sesión exitoso",
        "token": token
    })

@app.get("/libros")
def obtener_libros():
    conn = get_connection()
    filas = conn.execute("SELECT * FROM libros ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(fila) for fila in filas])

@app.get("/libros/<int:libro_id>")
def obtener_libro(libro_id):
    conn = get_connection()
    libro = conn.execute("SELECT * FROM libros WHERE id = ?", (libro_id,)).fetchone()
    conn.close()
    if libro is None:
        return error("Libro no encontrado", 404)
    return jsonify(dict(libro))

@app.get("/libros/buscar")
def buscar_libros():
    titulo = request.args.get("titulo")
    autor = request.args.get("autor")
    genero = request.args.get("genero")
    consulta = "SELECT * FROM libros WHERE 1=1"
    parametros = []
    if titulo:
        consulta += " AND titulo LIKE ?"
        parametros.append(f"%{titulo}%")
    if autor:
        consulta += " AND autor LIKE ?"
        parametros.append(f"%{autor}%")
    if genero:
        consulta += " AND genero LIKE ?"
        parametros.append(f"%{genero}%")
    consulta += " ORDER BY titulo"
    conn = get_connection()
    libros = conn.execute(consulta, parametros).fetchall()
    conn.close()
    return jsonify([dict(libro) for libro in libros])

@app.post("/libros")
@token_requerido
def agregar_libro():
    datos = request.get_json(silent=True) or {}
    if not datos.get("titulo") or not datos.get("autor"):
        return error("titulo y autor son obligatorios")
    try:
        anio = int(datos["anio"]) if datos.get("anio") is not None else None
    except (ValueError, TypeError):
        return error("anio debe ser un número")
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO libros (titulo, autor, genero, anio, disponible)
        VALUES (?, ?, ?, ?, 1)
    """, (datos["titulo"], datos["autor"], datos.get("genero", ""), anio))
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return jsonify({"mensaje": "Libro agregado correctamente", "id": nuevo_id}), 201

@app.put("/libros/<int:libro_id>")
@token_requerido
def actualizar_libro(libro_id):
    datos = request.get_json(silent=True) or {}
    conn = get_connection()
    libro = conn.execute("SELECT * FROM libros WHERE id = ?", (libro_id,)).fetchone()
    if libro is None:
        conn.close()
        return error("Libro no encontrado", 404)
    titulo = datos.get("titulo", libro["titulo"])
    autor = datos.get("autor", libro["autor"])
    genero = datos.get("genero", libro["genero"])
    anio = datos.get("anio", libro["anio"])
    try:
        if anio is not None:
            anio = int(anio)
    except (ValueError, TypeError):
        conn.close()
        return error("anio debe ser un número")
    conn.execute("""UPDATE libros SET titulo=?, autor=?, genero=?, anio=? WHERE id=?""",
                 (titulo, autor, genero, anio, libro_id))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Libro actualizado correctamente"})

@app.delete("/libros/<int:libro_id>")
@token_requerido
def eliminar_libro(libro_id):
    conn = get_connection()
    libro = conn.execute("SELECT * FROM libros WHERE id = ?", (libro_id,)).fetchone()
    if libro is None:
        conn.close()
        return error("Libro no encontrado", 404)
    activo = conn.execute(
        "SELECT id FROM prestamos WHERE libro_id=? AND estado='activo'", (libro_id,)
    ).fetchone()
    if activo:
        conn.close()
        return error("No se puede eliminar un libro con un préstamo activo")
    conn.execute("DELETE FROM libros WHERE id=?", (libro_id,))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Libro eliminado correctamente"})

@app.get("/usuarios")
@token_requerido
def obtener_usuarios():
    conn = get_connection()
    usuarios = conn.execute(
        "SELECT id, nombre, email, fecha_registro FROM usuarios ORDER BY id"
    ).fetchall()
    conn.close()
    return jsonify([dict(usuario) for usuario in usuarios])

@app.get("/prestamos")
@token_requerido
def obtener_prestamos():
    conn = get_connection()
    prestamos = conn.execute("""
        SELECT p.id, u.nombre AS usuario, u.email, l.titulo AS libro,
               p.fecha_prestamo, p.fecha_devolucion, p.estado
        FROM prestamos p
        INNER JOIN usuarios u ON u.id = p.usuario_id
        INNER JOIN libros l ON l.id = p.libro_id
        ORDER BY p.id DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(p) for p in prestamos])

@app.post("/prestamos")
@token_requerido
def crear_prestamo():
    datos = request.get_json(silent=True) or {}
    usuario_id, libro_id = datos.get("usuario_id"), datos.get("libro_id")
    if not usuario_id or not libro_id:
        return error("usuario_id y libro_id son obligatorios")
    conn = get_connection()
    usuario = conn.execute("SELECT id FROM usuarios WHERE id=?", (usuario_id,)).fetchone()
    if usuario is None:
        conn.close()
        return error("Usuario no encontrado", 404)
    libro = conn.execute("SELECT * FROM libros WHERE id=?", (libro_id,)).fetchone()
    if libro is None:
        conn.close()
        return error("Libro no encontrado", 404)
    if not libro["disponible"]:
        conn.close()
        return error("El libro no está disponible")
    conn.execute("""
        INSERT INTO prestamos (usuario_id,libro_id,fecha_prestamo,estado)
        VALUES (?,?,?,'activo')
    """, (usuario_id, libro_id, datetime.now().strftime("%Y-%m-%d")))
    conn.execute("UPDATE libros SET disponible=0 WHERE id=?", (libro_id,))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Préstamo registrado correctamente"}), 201

@app.put("/prestamos/<int:prestamo_id>/devolver")
@token_requerido
def devolver_prestamo(prestamo_id):
    conn = get_connection()
    prestamo = conn.execute("SELECT * FROM prestamos WHERE id=?", (prestamo_id,)).fetchone()
    if prestamo is None:
        conn.close()
        return error("Préstamo no encontrado", 404)
    if prestamo["estado"] == "devuelto":
        conn.close()
        return error("El préstamo ya fue devuelto")
    conn.execute("""UPDATE prestamos SET estado='devuelto', fecha_devolucion=? WHERE id=?""",
                 (datetime.now().strftime("%Y-%m-%d"), prestamo_id))
    conn.execute("UPDATE libros SET disponible=1 WHERE id=?", (prestamo["libro_id"],))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Libro devuelto correctamente"})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
