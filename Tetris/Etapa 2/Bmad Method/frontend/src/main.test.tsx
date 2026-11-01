import { describe, test, expect } from 'vitest'

describe('Entry Point main.tsx', () => {
  test('renders without crashing', async () => {
    // Create a container with id root
    const root = document.createElement('div')
    root.id = 'root'
    document.body.appendChild(root)

    // Clear any previous mock or side-effects and dynamically import main.tsx
    await import('./main')

    expect(document.getElementById('root')).toBeTruthy()
  })
})
