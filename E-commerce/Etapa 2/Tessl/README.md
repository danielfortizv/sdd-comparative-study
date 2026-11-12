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

---

# Stage 2: Product Reviews and Moderation (English)

The application has been extended with high-signal product reviews supporting star ratings (1-5), comments, optional image uploads, and a full moderator workflow.

## Demo Moderator Credentials

- **Username**: `moderator`
- **Password**: `moderator`

## Startup Instructions

### 1. Run the backend
```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 2. Run the frontend
```powershell
cd frontend
npm run dev
```

Open `http://localhost:3000` (or the local dev port shown by Vite) in your browser.

## Testing the Stage 2 Features

1. **Browse and View Reviews**:
   - On the product catalog, click the **Reviews** button on any product (e.g., *Premium Ergonomic Keyboard*). You will see the existing approved mock reviews and their star ratings.

2. **Submit a Review**:
   - In the reviews modal, if you are not signed in, you will be prompted to sign in.
   - Register or sign in with any test user (e.g., username: `john_doe`, password: `password123`).
   - Fill out the **Write a Product Review** form: select a star rating (1-5), type a comment, and optionally select an image file (under 2MB).
   - Click **Submit Review**. A message will confirm the submission is pending moderation.
   - Note that your submitted review is hidden from the public list for now.

3. **Moderate the Review**:
   - Sign out and sign in using the Moderator credentials:
     - **Username**: `moderator`
     - **Password**: `moderator`
   - Notice the new **Moderation Dashboard** tab appears in the top navigation header.
   - Go to the **Moderation Dashboard** to see all pending reviews in the queue, complete with the rating, comment, and your attached image preview.
   - Click **Approve** on your review.

4. **Verify Public Visibility**:
   - Switch back to the **Catalog** tab.
   - Click **Reviews** on the product you reviewed.
   - The newly approved review is now fully visible to all visitors of the catalog!


