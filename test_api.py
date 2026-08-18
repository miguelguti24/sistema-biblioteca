import os
from app import app, init_db, DB_NAME

if os.path.exists(DB_NAME):
    os.remove(DB_NAME)

init_db()
client = app.test_client()

# Autenticación
r = client.post("/auth/registro", json={
    "nombre": "Miguel Gutiérrez",
    "email": "miguel@example.com",
    "password": "clave123"
})
assert r.status_code == 201
token = r.get_json()["token"]
headers = {"Authorization": f"Bearer {token}"}

assert client.post("/auth/login", json={
    "email": "miguel@example.com",
    "password": "clave123"
}).status_code == 200

assert client.post("/auth/login", json={
    "email": "miguel@example.com",
    "password": "incorrecta"
}).status_code == 401

# Libros
assert client.post("/libros", json={
    "titulo": "Cien años de soledad",
    "autor": "Gabriel García Márquez",
    "genero": "Novela",
    "anio": 1967
}).status_code == 401  # sin token debe fallar

assert client.post("/libros", json={
    "titulo": "Cien años de soledad",
    "autor": "Gabriel García Márquez",
    "genero": "Novela",
    "anio": 1967
}, headers=headers).status_code == 201

assert client.get("/libros").status_code == 200  # lectura sin token, es pública
assert client.get("/libros/buscar?autor=García").status_code == 200

# Préstamos
assert client.post("/prestamos", json={
    "usuario_id": 1,
    "libro_id": 1
}, headers=headers).status_code == 201

assert client.post("/prestamos", json={
    "usuario_id": 1,
    "libro_id": 1
}, headers=headers).status_code == 400  # el libro ya no está disponible

assert client.put("/prestamos/1/devolver", headers=headers).status_code == 200

if os.path.exists(DB_NAME):
    os.remove(DB_NAME)

print("Todas las pruebas pasaron correctamente.")
