import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, useLocation, useNavigate } from 'react-router'
import App from './App'
import type { RelocationPlan } from './api/relocationPlan'

const plan: RelocationPlan = {
  id: 'shared-find-plan',
  title: 'Move our family',
  phases: [
    { id: 'prepare', title: 'Prepare', position: 10 },
    { id: 'settle', title: 'Settle', position: 20 },
  ],
  tasks: [
    {
      id: 'pack', title: 'Pack boxes', description: null, phase_id: 'prepare', categories: ['logistics'],
      status: 'not_started', assignees: [], start_date: null, due_date: null, priority: 'medium',
      dependency_task_ids: [], blocked: false,
    },
    {
      id: 'deposit', title: 'Pay deposit', description: null, phase_id: 'settle', categories: ['financial'],
      status: 'completed', assignees: [], start_date: null, due_date: null, priority: 'medium',
      dependency_task_ids: [], blocked: false,
    },
  ],
  milestones: [],
  decisions: [],
}

function response(body: unknown, ok = true): Response {
  return { ok, status: ok ? 200 : 500, json: async () => body } as Response
}

function mockRequests(customPlan = plan) {
  return vi.fn((path: string) => Promise.resolve(response(
    path === '/api/relocation-plan'
      ? customPlan
      : { task_id: 'pack', task_title: 'Pack boxes', phase_id: 'prepare', phase_title: 'Prepare', why: ['Actionable'] },
  )))
}

function HistoryProbe() {
  const location = useLocation()
  const navigate = useNavigate()
  return <><output data-testid="location">{location.pathname}</output><button onClick={() => navigate(-1)}>Back</button></>
}

afterEach(() => {
  sessionStorage.clear()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView
})

describe('shared Find', () => {
  async function clearIncompatibleFilterWithFind() {
    const filter = await screen.findByRole('button', { name: 'Filter by categories' })
    fireEvent.click(filter)
    fireEvent.click(screen.getByLabelText('Logistics'))
    fireEvent.click(document.body)
    fireEvent.click(screen.getByRole('button', { name: 'Find' }))
    const input = await screen.findByRole('combobox', { name: 'Search task titles' })
    fireEvent.change(input, { target: { value: 'deposit' } })
    fireEvent.click(screen.getByRole('option', { name: /Pay deposit/ }))
    return screen.findByText('Category filter cleared to show “Pay deposit.”')
  }

  it('is available on Now and Plan while the inline Plan finder is absent', async () => {
    vi.stubGlobal('fetch', mockRequests())
    const { unmount } = render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    expect(await screen.findByRole('button', { name: 'Find' })).toBeVisible()
    expect(screen.queryByRole('combobox', { name: 'Find a task' })).not.toBeInTheDocument()
    unmount()

    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    expect(await screen.findByRole('button', { name: 'Filter by categories' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Find' })).toBeVisible()
    expect(screen.queryByRole('combobox', { name: 'Find a task' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Find' }).closest('.family-navigation-wrap'))
      .toHaveClass('d-flex', 'align-items-center')
    expect(screen.getByRole('button', { name: 'Find' })).toHaveClass('shared-find-trigger')
  })

  it('loads a current snapshot, focuses search, shows context, and supports keyboard selection', async () => {
    let resolvePanel!: (value: Response) => void
    const panelResponse = new Promise<Response>((resolve) => { resolvePanel = resolve })
    let planRequests = 0
    const fetchMock = vi.fn((path: string) => {
      if (path === '/api/relocation-plan') {
        planRequests += 1
        return planRequests === 1 ? Promise.resolve(response(plan)) : panelResponse
      }
      return Promise.resolve(response({ task_id: 'pack', task_title: 'Pack boxes', phase_id: 'prepare', phase_title: 'Prepare', why: ['Actionable'] }))
    })
    vi.stubGlobal('fetch', fetchMock)
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    await screen.findByRole('button', { name: 'Filter by categories' })

    fireEvent.click(screen.getByRole('button', { name: 'Find' }))
    const dialog = await screen.findByRole('dialog', { name: 'Find a task' })
    expect(within(dialog).getByRole('status')).toHaveTextContent('Loading tasks')
    resolvePanel(response(plan))
    const input = await within(dialog).findByRole('combobox', { name: 'Search task titles' })
    await waitFor(() => expect(input).toHaveFocus())
    expect(fetchMock.mock.calls.filter(([path]) => path === '/api/relocation-plan')).toHaveLength(2)

    fireEvent.change(input, { target: { value: 'PAY' } })
    const result = within(dialog).getByRole('option', { name: /Pay deposit/ })
    expect(result).toHaveTextContent('Settle')
    expect(result).toHaveTextContent('Completed')
    fireEvent.keyDown(input, { key: 'ArrowDown' })
    expect(input).toHaveAttribute('aria-activedescendant', 'shared-find-result-deposit')
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(await screen.findByRole('article', { name: 'Pay deposit' })).toHaveFocus()
  })

  it('shows empty and error states', async () => {
    vi.stubGlobal('fetch', mockRequests())
    const { unmount } = render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: 'Find' }))
    const input = await screen.findByRole('combobox', { name: 'Search task titles' })
    fireEvent.change(input, { target: { value: 'missing' } })
    expect(screen.getByRole('status')).toHaveTextContent('No matching tasks.')
    unmount()

    vi.stubGlobal('fetch', vi.fn((path: string) => path === '/api/relocation-plan'
      ? Promise.resolve(response({ detail: 'failed' }, false))
      : Promise.resolve(response({ task_id: 'pack', task_title: 'Pack boxes', phase_id: 'prepare', phase_title: 'Prepare', why: [] }))))
    render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: 'Find' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('failed')
  })

  it('closes explicitly, with Escape, and by backdrop while returning focus', async () => {
    vi.stubGlobal('fetch', mockRequests())
    render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    const trigger = await screen.findByRole('button', { name: 'Find' })

    for (const close of ['button', 'escape', 'backdrop']) {
      trigger.focus()
      fireEvent.click(trigger)
      const dialog = await screen.findByRole('dialog', { name: 'Find a task' })
      if (close === 'button') fireEvent.click(screen.getAllByRole('button', { name: 'Close' }).at(-1)!)
      if (close === 'escape') fireEvent.keyDown(document, { key: 'Escape', code: 'Escape', keyCode: 27 })
      if (close === 'backdrop') fireEvent.click(document.querySelector('.offcanvas-backdrop')!)
      await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Find a task' })).not.toBeInTheDocument())
      expect(trigger).toHaveFocus()
    }
  })

  it('navigates from Now to Plan once and Back returns to Now', async () => {
    vi.stubGlobal('fetch', mockRequests())
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    render(<MemoryRouter initialEntries={['/now']}><App /><HistoryProbe /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: 'Find' }))
    const input = await screen.findByRole('combobox', { name: 'Search task titles' })
    fireEvent.change(input, { target: { value: 'pack' } })
    fireEvent.click(screen.getByRole('option', { name: /Pack boxes/ }))

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/plan'))
    expect(await screen.findByRole('article', { name: 'Pack boxes' })).toHaveClass('is-found')
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(await screen.findByTestId('location')).toHaveTextContent('/now')
  })

  it('uses the mobile bottom Find trigger for the existing cross-route targeting flow', async () => {
    vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
      matches: false,
      media: query,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })))
    vi.stubGlobal('fetch', mockRequests())
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    const navigation = screen.getByRole('navigation', { name: 'Mobile primary' })
    const find = within(navigation).getByRole('button', { name: 'Find' })
    fireEvent.click(find)
    expect(find).toHaveAttribute('aria-pressed', 'true')
    const input = await screen.findByRole('combobox', { name: 'Search task titles' })
    fireEvent.change(input, { target: { value: 'deposit' } })
    fireEvent.click(screen.getByRole('option', { name: /Pay deposit/ }))

    const task = await screen.findByRole('article', { name: 'Pay deposit' })
    expect(task).toHaveFocus()
    expect(task).toHaveClass('is-found')
    expect(screen.getByRole('button', { name: 'Completed (1)' })).toHaveAttribute('aria-expanded', 'true')
  })

  it('does not add redundant history when selecting on Plan', async () => {
    vi.stubGlobal('fetch', mockRequests())
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    render(<MemoryRouter initialEntries={['/now', '/plan']} initialIndex={1}><App /><HistoryProbe /></MemoryRouter>)
    await screen.findByRole('button', { name: 'Filter by categories' })
    fireEvent.click(screen.getByRole('button', { name: 'Find' }))
    const input = await screen.findByRole('combobox', { name: 'Search task titles' })
    fireEvent.change(input, { target: { value: 'pack' } })
    fireEvent.click(screen.getByRole('option', { name: /Pack boxes/ }))
    await screen.findByRole('article', { name: 'Pack boxes' })
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(await screen.findByTestId('location')).toHaveTextContent('/now')
  })

  it('preserves compatible filters and clears incompatible filters only on selection', async () => {
    vi.stubGlobal('fetch', mockRequests())
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    const filter = await screen.findByRole('button', { name: 'Filter by categories' })
    fireEvent.click(filter)
    fireEvent.click(screen.getByLabelText('Logistics'))
    fireEvent.click(document.body)

    fireEvent.click(screen.getByRole('button', { name: 'Find' }))
    let input = await screen.findByRole('combobox', { name: 'Search task titles' })
    fireEvent.change(input, { target: { value: 'pack' } })
    expect(filter).toHaveTextContent('Categories (1)')
    fireEvent.click(screen.getByRole('option', { name: /Pack boxes/ }))
    expect(filter).toHaveTextContent('Categories (1)')
    await waitFor(() => expect(sessionStorage.getItem('gotime:plan:shared-find-plan:filters')).toContain('logistics'))

    fireEvent.click(screen.getByRole('button', { name: 'Find' }))
    input = await screen.findByRole('combobox', { name: 'Search task titles' })
    fireEvent.change(input, { target: { value: 'deposit' } })
    expect(filter).toHaveTextContent('Categories (1)')
    fireEvent.click(screen.getByRole('option', { name: /Pay deposit/ }))
    await waitFor(() => expect(filter).toHaveTextContent(/^Categories$/))
    await waitFor(() => expect(sessionStorage.getItem('gotime:plan:shared-find-plan:filters')).toContain('"categories":[]'))
    expect(await screen.findByText('Category filter cleared to show “Pay deposit.”')).toBeVisible()
  })

  it('opens only the destination phase and completed subsection and consumes the highlight once', async () => {
    vi.stubGlobal('fetch', mockRequests())
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    const rendered = render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: 'Find' }))
    const input = await screen.findByRole('combobox', { name: 'Search task titles' })
    fireEvent.change(input, { target: { value: 'deposit' } })
    fireEvent.click(screen.getByRole('option', { name: /Pay deposit/ }))

    const settle = await screen.findByRole('button', { name: /Settle 0 remaining · 1 completed/ })
    await waitFor(() => expect(settle).toHaveAttribute('aria-expanded', 'true'))
    expect(screen.getByRole('button', { name: 'Completed (1)' })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: /Prepare 1 remaining/ })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('article', { name: 'Pay deposit' })).toHaveClass('is-found')

    rendered.unmount()
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    const restored = await screen.findByRole('article', { name: 'Pay deposit' })
    expect(restored).not.toHaveClass('is-found')
  })

  it('dismisses the incompatible-filter notice explicitly and on the next filter change', async () => {
    vi.stubGlobal('fetch', mockRequests())
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    const notice = await clearIncompatibleFilterWithFind()
    fireEvent.click(within(notice.closest('[role="status"]')!).getByRole('button', { name: 'Close alert' }))
    await waitFor(() => expect(screen.queryByText(/Category filter cleared/)).not.toBeInTheDocument())

    const nextNotice = await clearIncompatibleFilterWithFind()
    expect(nextNotice).toBeVisible()
    const filter = screen.getByRole('button', { name: 'Filter by categories' })
    fireEvent.click(filter)
    fireEvent.click(screen.getByLabelText('Financial'))
    expect(screen.queryByText(/Category filter cleared/)).not.toBeInTheDocument()
  })

  it('automatically dismisses the filter notice after six seconds with a controlled timer', async () => {
    vi.stubGlobal('fetch', mockRequests())
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    const timers: Array<{ callback: TimerHandler; delay?: number }> = []
    const nativeSetTimeout = window.setTimeout.bind(window)
    vi.spyOn(window, 'setTimeout').mockImplementation(((callback: TimerHandler, delay?: number, ...args: unknown[]) => {
      timers.push({ callback, delay })
      return nativeSetTimeout(callback, delay, ...args)
    }) as typeof window.setTimeout)
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    await clearIncompatibleFilterWithFind()
    const dismissal = timers.find((timer) => timer.delay === 6000)
    expect(dismissal).toBeDefined()
    const callback = dismissal!.callback
    if (typeof callback === 'function') act(() => (callback as () => void)())
    await waitFor(() => expect(screen.queryByText(/Category filter cleared/)).not.toBeInTheDocument())
  })

  it('drops the transient notice on a new Find action and does not restore it after routing', async () => {
    vi.stubGlobal('fetch', mockRequests())
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    await clearIncompatibleFilterWithFind()
    fireEvent.click(screen.getByRole('button', { name: 'Find' }))
    expect(screen.queryByText(/Category filter cleared/)).not.toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: 'Close' }).at(-1)!)
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Find a task' })).not.toBeInTheDocument())
    fireEvent.click(screen.getByRole('link', { name: 'Now' }))
    await screen.findByText('What should I do next?')
    fireEvent.click(screen.getByRole('link', { name: 'Plan' }))
    await screen.findByRole('button', { name: 'Filter by categories' })
    expect(screen.queryByText(/Category filter cleared/)).not.toBeInTheDocument()
  })
})
