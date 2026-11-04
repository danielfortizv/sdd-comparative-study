import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
// Global responsive, accessible styling (Task 13): theme tokens + layout.
import './styles/global.css';

const rootElement = document.getElementById('root');
if (rootElement) {
  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
