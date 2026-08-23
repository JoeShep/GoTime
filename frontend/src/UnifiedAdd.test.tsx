import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'
import App from './App'
import type { RelocationPlan } from './api/relocationPlan'

const milestone = {
  id: 'moving-day', title: 'Reach moving day', description: null,
  target_earliest_date: null, target_latest_date: null,
  status: 'pending' as const, achieved_at: null,
}

const plan: RelocationPlan = {
  id: 'unified-add-plan',
  title: 'Move our family',
  phases: [
    { id: 'prepare', title: 'Prepare', position: 10 },
    { id: 'move', title: 'Move', position: 20 },
  ],
  tasks: [{
    id: 'pack', title: 'Pack boxes', description: null, phase_id: 'prepare', categories: ['logistics'],
    status: 'not_started', assignees: [], start_date: null, due_date: null, priority: 'medium',
    dependency_task_ids: [], blocked: false,
  }],
  milestones: [milestone],
  decisions: [],
}

function response(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response
}

function recommendation() {
  return {
    status: 'recommended', task_id: 'pack', task_title: 'Pack boxes',
    phase_id: 'prepare', phase_title: 'Prepare', why: ['Actionable'], why_now: 'Ready',
    directly_unblocks_task_ids: [], ranking_factors: null,
  }
}

function mockRequests(initial = plan) {
  return vi.fn((path: string, init?: RequestInit) => {
    if (path === '/api/relocation-plan/recommendation') return Promise.resolve(response(recommendation()))
    if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(initial))
    return Promise.resolve(response(initial))
  })
}

async function openAdd() {
  const add = await screen.findByRole('button', { name: 'Add' })
  fireEvent.click(add)
  return { add, menu: screen.getByRole('menu', { name: 'Add' }) }
}

beforeEach(() => {
  sessionStorage.setItem('gotime:plan:unified-add-plan:expansion', JSON.stringify({
    version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [],
  }))
})

afterEach(() => {
  sessionStorage.clear()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView
})

describe('unified Plan Add menu', () => {
  it('appears once on Plan, never on Now, and replaces all separate creation controls', async () => {
    vi.stubGlobal('fetch', mockRequests())
    const now = render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    await screen.findByText('What should I do next?')
    expect(screen.queryByRole('button', { name: 'Add' })).not.toBeInTheDocument()
    now.unmount()

    const { container } = render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    expect(await screen.findAllByRole('button', { name: 'Add' })).toHaveLength(1)
    expect(screen.queryByRole('button', { name: /Add task/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Add milestone/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Add decision/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add' }).closest('.plan-page-heading')).toContainElement(
      screen.getByRole('heading', { name: 'Family plan' }),
    )
    expect(container.querySelector('.plan-page-heading')).toHaveClass('flex-wrap', 'justify-content-between')
  })

  it('shows ordered mobile-safe copy and supports toggle, outside, Escape, and keyboard opening', async () => {
    vi.stubGlobal('fetch', mockRequests())
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    const { add, menu } = await openAdd()
    const items = within(menu).getAllByRole('menuitem')
    expect(items.map((item) => item.querySelector('strong')?.textContent)).toEqual(['Task', 'Milestone', 'Decision'])
    expect(items.map((item) => item.querySelector('span')?.textContent)).toEqual([
      'Something that needs to be done',
      'An important outcome or moment',
      'A choice that needs to be made',
    ])
    expect(menu).toHaveClass('plan-add-menu-list')
    expect(items.every((item) => item.classList.contains('dropdown-item'))).toBe(true)

    fireEvent.click(add)
    expect(screen.getByRole('menu', { name: 'Add' })).not.toHaveClass('show')
    fireEvent.keyDown(add, { key: 'ArrowDown' })
    expect(screen.getByRole('menu', { name: 'Add' })).toBeVisible()
    fireEvent.click(document.body)
    await waitFor(() => expect(screen.getByRole('menu', { name: 'Add' })).not.toHaveClass('show'))

    fireEvent.click(add)
    fireEvent.keyDown(screen.getByRole('menu'), { key: 'Escape' })
    expect(screen.getByRole('menu')).not.toHaveClass('show')
    expect(add).toHaveFocus()
  })

  it('opens each reused editor with initial focus and never remembers the canceled type', async () => {
    vi.stubGlobal('fetch', mockRequests())
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)

    let opened = await openAdd()
    fireEvent.click(within(opened.menu).getByRole('menuitem', { name: /Task/ }))
    expect(screen.getByRole('heading', { name: 'Add task' })).toBeVisible()
    expect(screen.getByLabelText('Title')).toHaveFocus()
    expect(opened.add).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(opened.add).toHaveFocus())

    opened = await openAdd()
    expect(within(opened.menu).getAllByRole('menuitem').every((item) => !item.hasAttribute('aria-selected'))).toBe(true)
    fireEvent.click(within(opened.menu).getByRole('menuitem', { name: /Milestone/ }))
    expect(screen.getByText('Add milestone')).toBeVisible()
    expect(screen.getByLabelText('Name')).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(opened.add).toHaveFocus())

    opened = await openAdd()
    fireEvent.click(within(opened.menu).getByRole('menuitem', { name: /Decision/ }))
    expect(screen.getByText('Add decision')).toBeVisible()
    expect(screen.getByLabelText('Decision')).toHaveFocus()
    expect(screen.getAllByLabelText(/Option \d/)).toHaveLength(2)
  })

  it('preserves unsaved values, scopes saving state, restores scroll on cancel, and coordinates Find', async () => {
    let resolveCreate: ((value: Response) => void) | undefined
    const pending = new Promise<Response>((resolve) => { resolveCreate = resolve })
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan/recommendation') return Promise.resolve(response(recommendation()))
      if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(plan))
      return pending
    })
    vi.stubGlobal('fetch', fetchMock)
    let y = 275
    Object.defineProperty(window, 'scrollY', { configurable: true, get: () => y })
    const scrollTo = vi.fn(({ top }: ScrollToOptions) => { y = Number(top) })
    vi.stubGlobal('scrollTo', scrollTo)
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    const find = await screen.findByRole('button', { name: 'Find' })
    fireEvent.click(find)
    await screen.findByRole('dialog', { name: 'Find a task' })
    const { menu } = await openAdd()
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Find a task' })).not.toBeInTheDocument())
    fireEvent.click(within(menu).getByRole('menuitem', { name: /Task/ }))
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Keep this draft' } })
    expect(find).toBeDisabled()
    fireEvent.click(find)
    expect(screen.queryByRole('dialog', { name: 'Find a task' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Title')).toHaveValue('Keep this draft')

    fireEvent.click(screen.getByRole('button', { name: 'Create task' }))
    expect(await screen.findByRole('button', { name: 'Creating…' })).toBeDisabled()
    expect(screen.getByLabelText('Status for Pack boxes')).not.toBeDisabled()
    resolveCreate?.(response(plan))
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Creating…' })).not.toBeInTheDocument())

    y = 275
    const reopened = await openAdd()
    fireEvent.click(within(reopened.menu).getByRole('menuitem', { name: /Task/ }))
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Cancel me' } })
    y = 40
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(scrollTo).toHaveBeenCalledWith({ top: 275, left: 0, behavior: 'auto' }))
    expect(sessionStorage.getItem('gotime:plan:unified-add-plan:scroll')).toContain('275')
  })

  it('reveals a created Task, preserves compatible filters, and updates its saved location', async () => {
    let updated = plan
    let y = 0
    Object.defineProperty(window, 'scrollY', { configurable: true, get: () => y })
    Object.defineProperty(Element.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(function (this: Element) { if (this.id.startsWith('task-')) y = 420 }),
    })
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan/recommendation') return Promise.resolve(response(recommendation()))
      if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(plan))
      if (path === '/api/relocation-plan/tasks' && init?.method === 'POST') {
        const body = JSON.parse(String(init.body))
        updated = { ...plan, tasks: [...plan.tasks, { ...body, blocked: false }] }
        return Promise.resolve(response(updated))
      }
      return Promise.resolve(response(updated))
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    const filter = await screen.findByRole('button', { name: 'Filter by categories' })
    fireEvent.click(filter)
    fireEvent.click(screen.getByLabelText('Logistics'))
    fireEvent.click(document.body)
    const { menu } = await openAdd()
    fireEvent.click(within(menu).getByRole('menuitem', { name: /Task/ }))
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Load truck' } })
    fireEvent.change(screen.getByLabelText('Phase'), { target: { value: 'move' } })
    const categories = screen.getByLabelText('Categories (optional)')
    fireEvent.click(categories)
    fireEvent.click(screen.getByLabelText('Logistics'))
    fireEvent.click(document.body)
    fireEvent.click(screen.getByRole('button', { name: 'Create task' }))

    const created = await screen.findByRole('article', { name: 'Load truck' })
    expect(created).toHaveFocus()
    expect(created).toHaveClass('is-found')
    expect(filter).toHaveTextContent('Categories (1)')
    expect(screen.getByRole('button', { name: /Move 1 remaining/ })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: /Prepare 1 remaining/ })).toHaveAttribute('aria-expanded', 'true')
    await waitFor(() => expect(sessionStorage.getItem('gotime:plan:unified-add-plan:scroll')).toContain('420'))
  })

  it('clears an incompatible Task filter with the established notice and does not replay highlight', async () => {
    let latest = plan
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    vi.stubGlobal('fetch', vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan/recommendation') return Promise.resolve(response(recommendation()))
      if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(latest))
      const body = JSON.parse(String(init?.body))
      latest = { ...plan, tasks: [...plan.tasks, { ...body, blocked: false }] }
      return Promise.resolve(response(latest))
    }))
    const rendered = render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    const filter = await screen.findByRole('button', { name: 'Filter by categories' })
    fireEvent.click(filter)
    fireEvent.click(screen.getByLabelText('Financial'))
    fireEvent.click(document.body)
    const { menu } = await openAdd()
    fireEvent.click(within(menu).getByRole('menuitem', { name: /Task/ }))
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Pack lamps' } })
    const categories = screen.getByLabelText('Categories (optional)')
    fireEvent.click(categories)
    fireEvent.click(screen.getByLabelText('Logistics'))
    fireEvent.click(document.body)
    fireEvent.click(screen.getByRole('button', { name: 'Create task' }))
    expect(await screen.findByText('Category filter cleared to show “Pack lamps.”')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Filter by categories' })).toHaveTextContent(/^Categories$/)
    await waitFor(() => expect(sessionStorage.getItem('gotime:plan:unified-add-plan:filters')).toContain('"categories":[]'))

    rendered.unmount()
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    expect(await screen.findByRole('article', { name: 'Pack lamps' })).not.toHaveClass('is-found')
  })

  it('creates and reveals Milestones and Decisions from their existing aggregate APIs', async () => {
    let latest = plan
    let y = 0
    Object.defineProperty(window, 'scrollY', { configurable: true, get: () => y })
    Object.defineProperty(Element.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(function (this: Element) { y = this.getAttribute('aria-labelledby')?.startsWith('milestone') ? 510 : 620 }),
    })
    vi.stubGlobal('fetch', vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan/recommendation') return Promise.resolve(response(recommendation()))
      if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(latest))
      const body = JSON.parse(String(init?.body))
      if (path === '/api/relocation-plan/milestones') {
        latest = { ...latest, milestones: [...latest.milestones, { ...body, status: 'pending', achieved_at: null }] }
      } else if (path === '/api/relocation-plan/decisions') {
        latest = { ...latest, decisions: [...latest.decisions, { ...body, status: 'unresolved', selected_option_id: null }] }
      }
      return Promise.resolve(response(latest))
    }))
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)

    let opened = await openAdd()
    fireEvent.click(within(opened.menu).getByRole('menuitem', { name: /Milestone/ }))
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Home sold' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save milestone' }))
    const createdMilestone = await screen.findByRole('article', { name: 'Home sold' })
    expect(createdMilestone).toHaveFocus()
    expect(createdMilestone).toHaveClass('is-found')
    await waitFor(() => expect(sessionStorage.getItem('gotime:plan:unified-add-plan:scroll')).toContain('510'))

    opened = await openAdd()
    fireEvent.click(within(opened.menu).getByRole('menuitem', { name: /Decision/ }))
    fireEvent.change(screen.getByLabelText('Decision'), { target: { value: 'Choose sale route' } })
    fireEvent.change(screen.getByLabelText('Option 1'), { target: { value: 'List publicly' } })
    fireEvent.change(screen.getByLabelText('Option 2'), { target: { value: 'Sell privately' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save decision' }))
    const createdDecision = await screen.findByRole('article', { name: 'Choose sale route' })
    await waitFor(() => expect(createdDecision).toHaveFocus())
    expect(createdDecision).toHaveClass('is-found')
    await waitFor(() => expect(sessionStorage.getItem('gotime:plan:unified-add-plan:scroll')).toContain('620'))
  })
})
