# Sistema de Gestión de Biblioteca - Full Stack

Proyecto de backend en Python y Flask para administrar libros, usuarios y préstamos, con autenticación mediante JSON Web Tokens (JWT) y un frontend en HTML/CSS/JavaScript puro conectado a la API.

# Tecnologías
Backend: Python 3, Flask, SQLite, SQL, API REST
Autenticación: JWT (JSON Web Tokens), hashing de contraseñas con Werkzeug Security
Frontend: HTML, CSS y JavaScript (sin frameworks), consumiendo la API con `fetch`

# Funcionalidades
CRUD de libros
Búsqueda por título, autor y género
Registro e inicio de sesión de usuarios con contraseña encriptada
Autenticación por token JWT en las operaciones que modifican datos
Control de disponibilidad
Préstamos y devoluciones
Validaciones y manejo de errores
Relaciones entre tablas

# Seguridad

Las contraseñas nunca se guardan en texto plano: se almacenan encriptadas con `werkzeug.security.generate_password_hash`.

Al registrarse o iniciar sesión, la API devuelve un token JWT que expira después de 8 horas. Ese token se debe enviar en el header `Authorization` de cada petición a un endpoint protegido:

```
Authorization: Bearer <token>
```

Endpoints públicos (no requieren token): consultar y buscar libros.
Endpoints protegidos (requieren token): registrar/editar/eliminar libros, ver usuarios, crear y devolver préstamos.

# Ejecutar el backend

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

API: `http://127.0.0.1:5000`

# Ejecutar el frontend

Con el backend corriendo, simplemente se abre el archivo `index.html` con doble clic. No necesita instalación ni servidor adicional.

Desde ahí se puede:
- Crear una cuenta o iniciar sesión
- Ver el catálogo de libros (visible sin iniciar sesión)
- Agregar libros, prestarlos y marcarlos como devueltos (requiere sesión iniciada)


