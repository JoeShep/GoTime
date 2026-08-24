import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, useLocation, useNavigate } from 'react-router'
import App from './App'
import { mobileBottomContentGutter, mobileBottomNavigationHeight } from './mobileNavigationLayout'

vi.mock('./NowPage', () => ({ NowPage: () => <h1>Now content</h1> }))
vi.mock('./PlanPage', () => ({ PlanPage: () => <h1>Plan content</h1> }))

function setMedia({ desktop = false, reduced = false } = {}) {
  vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
    matches: query === '(min-width: 576px)' ? desktop : reduced,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })))
}

function HistoryProbe() {
  const location = useLocation()
  const navigate = useNavigate()
  return <><output data-testid="route">{location.pathname}</output><button onClick={() => navigate(-1)}>Back</button></>
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('persistent mobile bottom navigation', () => {
  it('renders one labelled, equal-target mobile landmark without provisional header controls', () => {
    setMedia()
    const { container } = render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    const navigation = screen.getByRole('navigation', { name: 'Mobile primary' })
    const targets = [
      ...within(navigation).getAllByRole('link'),
      within(navigation).getByRole('button', { name: 'Find' }),
    ]

    expect(targets.map((target) => target.textContent)).toEqual(['Now', 'Plan', 'Find'])
    expect(targets).toHaveLength(3)
    targets.forEach((target) => expect(target).toHaveClass('mobile-bottom-navigation-target'))
    expect(within(navigation).getByRole('link', { name: 'Now' })).toHaveAttribute('aria-current', 'page')
    expect(within(navigation).getByRole('link', { name: 'Plan' })).not.toHaveAttribute('aria-current')
    expect(within(navigation).getByRole('button', { name: 'Find' })).toHaveAttribute('aria-expanded', 'false')
    expect(container.querySelector('.family-navigation-wrap')).not.toBeInTheDocument()
    expect(container.querySelector('.app-shell')).not.toHaveClass('pb-5')
    expect(container.querySelector('.app-container')).not.toHaveClass('pb-4')
    expect(container.querySelector('.next-step-card > .card-body')).not.toHaveClass('pb-4')
  })

  it('uses one safe-area-aware 64px accommodation with a small gutter and 44px targets', () => {
    setMedia()
    const { container } = render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    const shell = container.querySelector<HTMLElement>('.app-shell')!
    const navigation = screen.getByRole('navigation', { name: 'Mobile primary' })

    expect(mobileBottomNavigationHeight).toBe('4rem')
    expect(mobileBottomContentGutter).toBe('1rem')
    expect(shell.style.getPropertyValue('--mobile-bottom-navigation-height')).toBe('4rem')
    expect(shell.style.getPropertyValue('--mobile-bottom-content-gutter')).toBe('1rem')
    expect(navigation).toHaveClass('mobile-bottom-navigation')
  })

  it('uses the shared mobile page frame for short Now and not-found content', () => {
    setMedia()
    const now = render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)

    expect(now.container.querySelector('.app-shell > .app-container > .next-step-card')).toBeInTheDocument()
    now.unmount()

    const missing = render(<MemoryRouter initialEntries={['/missing']}><App /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
    expect(missing.container.querySelector('.app-shell > .app-container > .next-step-card')).toBeInTheDocument()
    expect(missing.container.querySelector('.app-shell .alert')).toHaveClass('mb-0', 'mb-sm-3')
  })

  it('retains only the accepted desktop header at the sm breakpoint and above', () => {
    setMedia({ desktop: true })
    const { container } = render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)

    expect(screen.getByRole('navigation', { name: 'Primary' })).toHaveClass('family-navigation')
    expect(screen.getByRole('link', { name: 'Plan' })).toHaveAttribute('aria-current', 'page')
    expect(screen.queryByRole('navigation', { name: 'Mobile primary' })).not.toBeInTheDocument()
    expect(container.querySelector('.family-navigation-wrap')).toHaveClass('pt-sm-3', 'mb-sm-0')
    expect(container.querySelector('.app-container')).toHaveClass('py-sm-4')
    expect(container.querySelector('.next-step-card > .card-body')).toHaveClass('p-sm-4')
  })

  it('navigates normally while active taps scroll without adding history', async () => {
    setMedia()
    const scrollTo = vi.fn()
    vi.stubGlobal('scrollTo', scrollTo)
    render(<MemoryRouter initialEntries={['/plan', '/now']} initialIndex={1}><App /><HistoryProbe /></MemoryRouter>)
    const navigation = screen.getByRole('navigation', { name: 'Mobile primary' })

    fireEvent.click(within(navigation).getByRole('link', { name: 'Now' }))
    expect(scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: 'smooth' })
    expect(screen.getByTestId('route')).toHaveTextContent('/now')
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    await waitFor(() => expect(screen.getByTestId('route')).toHaveTextContent('/plan'))

    fireEvent.click(within(screen.getByRole('navigation', { name: 'Mobile primary' })).getByRole('link', { name: 'Now' }))
    await waitFor(() => expect(screen.getByTestId('route')).toHaveTextContent('/now'))
  })

  it('scrolls active destinations immediately when reduced motion is requested', () => {
    setMedia({ reduced: true })
    const scrollTo = vi.fn()
    vi.stubGlobal('scrollTo', scrollTo)
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)

    fireEvent.click(within(screen.getByRole('navigation', { name: 'Mobile primary' })).getByRole('link', { name: 'Plan' }))
    expect(scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: 'auto' })
  })

  it('opens the one Find panel, exposes pressed state, layers inert navigation beneath it, and restores focus', async () => {
    setMedia()
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true, status: 200, json: async () => ({ phases: [], tasks: [] }) } as Response)))
    render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    const navigation = screen.getByRole('navigation', { name: 'Mobile primary' })
    const find = within(navigation).getByRole('button', { name: 'Find' })
    find.focus()
    fireEvent.click(find)

    expect(await screen.findByRole('dialog', { name: 'Find a task' })).toHaveAttribute('id', 'shared-find-panel')
    expect(find).toHaveAttribute('aria-expanded', 'true')
    expect(find).toHaveAttribute('aria-pressed', 'true')
    expect(navigation).toHaveAttribute('inert')
    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape', keyCode: 27 })
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Find a task' })).not.toBeInTheDocument())
    expect(find).toHaveFocus()
  })
})
