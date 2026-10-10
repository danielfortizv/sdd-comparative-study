# E-Commerce Demo — Stage 1

Aplicación web de comercio electrónico desarrollada con React, TypeScript y FastAPI. Incluye catálogo de productos, carrito local, registro/inicio de sesión y un checkout completamente simulado.

> El checkout es únicamente demostrativo: no procesa pagos ni realiza cargos reales.

## Requisitos

- Python 3.10 o superior.
- Node.js 18 o superior.
- npm.

## Estructura

```text
Tessl/
├── backend/     # API FastAPI
├── frontend/    # Aplicación React + TypeScript
└── specs/       # Especificaciones de Stage 1
```

## 1. Ejecutar el backend

Abre una terminal en la carpeta `backend`:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

En macOS o Linux, la activación del entorno cambia a:

```bash
source .venv/bin/activate
```

El backend quedará disponible en:

- API: `http://127.0.0.1:8000`
- Documentación Swagger: `http://127.0.0.1:8000/docs`

## 2. Ejecutar el frontend

Sin detener el backend, abre una segunda terminal en la carpeta `frontend`:

```powershell
cd frontend
npm ci
npm run dev
```

Abre `http://localhost:3000` en el navegador.

Si `npm ci` no puede ejecutarse porque no existe un archivo lock, usa:

```powershell
npm install
```

## Compilar el frontend

Para comprobar la compilación de producción:

```powershell
cd frontend
npm run build
```

El resultado se genera en `frontend/dist`.

Para previsualizar la compilación:

```powershell
npm run preview
```

## Consideraciones

- El frontend espera que la API esté disponible en `http://127.0.0.1:8000/api`.
- Los productos, usuarios y sesiones se almacenan en memoria para esta demostración.
- Al reiniciar el backend se eliminan las cuentas y sesiones creadas durante la ejecución.
- Las imágenes del catálogo se cargan desde URLs externas, por lo que requieren conexión a Internet.
- No se necesita configurar una base de datos ni variables de entorno.

## Flujo de prueba rápido

1. Abre el catálogo.
2. Agrega un producto disponible al carrito.
3. Entra al carrito y selecciona **Proceed to Checkout**.
4. Registra una cuenta o inicia sesión.
5. Confirma la compra simulada.
6. Verifica el resumen de confirmación.

