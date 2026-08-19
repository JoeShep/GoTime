import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'
import App from './App'

vi.mock('./NowPage', () => ({ NowPage: () => <h1>Now content</h1> }))
vi.mock('./PlanPage', () => ({ PlanPage: () => <h1>Plan content</h1> }))

afterEach(() => vi.unstubAllGlobals())

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

describe('application routes', () => {
  it('redirects the root to Now and marks its navigation active', async () => {
    renderAt('/')
    expect(await screen.findByRole('heading', { name: 'Now content' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Now' })).toHaveClass('active')
    expect(screen.getByRole('link', { name: 'Plan' })).not.toHaveClass('active')
  })

  it('renders Plan directly and supports normal link navigation', () => {
    renderAt('/plan')
    expect(screen.getByRole('heading', { name: 'Plan content' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Plan' })).toHaveClass('active')
    fireEvent.click(screen.getByRole('link', { name: 'Now' }))
    expect(screen.getByRole('heading', { name: 'Now content' })).toBeVisible()
  })

  it('uses normal not-found behavior for unknown and disabled experiment routes', () => {
    const { rerender } = renderAt('/missing')
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeVisible()
    rerender(<MemoryRouter initialEntries={['/experiments']}><App /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeVisible()
  })
})
