/// <reference types="vite/client" />

// Tipado de las variables de entorno de Vite usadas por el frontend (Etapa 3, Tarea 26).
// `VITE_API_BASE_URL` permite sobreescribir el origen base de la API en desarrollo local
// (p. ej. "http://localhost:8000"); en producción se deja SIN definir para usar un origen
// RELATIVO (cadena vacía), de modo que Nginx haga reverse-proxy de `/api` al backend.
// Esto solo añade tipos (no cambia comportamiento ni lógica de la aplicación).
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
