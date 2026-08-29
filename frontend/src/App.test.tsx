import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'
import App, { experimentsEnabled } from './App'

vi.mock('./NowPage', () => ({ NowPage: () => <h1>Now content</h1> }))
vi.mock('./PlanPage', () => ({ PlanPage: () => <h1>Plan content</h1> }))

afterEach(() => vi.unstubAllGlobals())

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

describe('application routes', () => {
  it('keeps normal Now and Plan routes available while the experiment area is off', () => {
    expect(experimentsEnabled).toBe(false)
    renderAt('/now')
    expect(screen.getByRole('heading', { name: 'Now content' })).toBeVisible()
    fireEvent.click(screen.getByRole('link', { name: 'Plan' }))
    expect(screen.getByRole('heading', { name: 'Plan content' })).toBeVisible()
  })

  it('redirects the root to Now and marks its navigation active', async () => {
    const { container } = renderAt('/')
    expect(await screen.findByRole('heading', { name: 'Now content' })).toBeVisible()
    expect(container.querySelector('.app-shell')).toHaveClass(
      'pt-2',
      'py-sm-5',
    )
    expect(container.querySelector('.app-container')).toHaveClass(
      'pt-0',
      'py-sm-4',
    )
    expect(container.querySelector('.next-step-card > .card-body')).toHaveClass(
      'pt-2',
      'p-sm-4',
      'p-md-5',
    )
    expect(container.querySelector('.family-navigation-wrap')).toHaveClass(
      'pt-0',
      'pt-sm-3',
      'mb-3',
      'mb-sm-0',
    )
    expect(screen.getByRole('navigation', { name: 'Primary' })).toHaveClass(
      'family-navigation',
    )
    expect(screen.getByRole('link', { name: 'Now' })).toHaveClass('active')
    expect(screen.getByRole('link', { name: 'Now' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('link', { name: 'Plan' })).not.toHaveClass('active')
    expect(screen.getByRole('link', { name: 'Plan' })).not.toHaveAttribute(
      'aria-current',
    )
  })

  it('renders Plan directly and supports normal link navigation', () => {
    renderAt('/plan')
    expect(screen.getByRole('heading', { name: 'Plan content' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Plan' })).toHaveClass('active')
    expect(screen.getByRole('link', { name: 'Plan' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    fireEvent.click(screen.getByRole('link', { name: 'Now' }))
    expect(screen.getByRole('heading', { name: 'Now content' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Now' })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })

  it('uses normal not-found behavior for unknown and disabled experiment routes', () => {
    const { rerender } = renderAt('/missing')
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeVisible()
    rerender(<MemoryRouter initialEntries={['/experiments']}><App /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeVisible()
  })
})
