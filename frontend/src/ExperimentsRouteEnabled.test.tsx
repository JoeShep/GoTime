import { render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.resetModules()
})

it('renders the Experiments route only after the exact frontend opt-in', async () => {
  vi.stubEnv('VITE_ENABLE_EXPERIMENTS', 'true')
  vi.doMock('./ExperimentsPage', () => ({
    default: () => <h1>Enabled experiments</h1>,
  }))
  const { default: App } = await import('./App')

  render(<MemoryRouter initialEntries={['/experiments']}><App /></MemoryRouter>)

  expect(await screen.findByRole('heading', { name: 'Enabled experiments' })).toBeVisible()
  expect(screen.queryByRole('link', { name: /Experiments/i })).not.toBeInTheDocument()
})
