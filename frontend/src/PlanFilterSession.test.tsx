import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, useLocation, useNavigate } from 'react-router'
import App from './App'
import { RelocationPlan } from './RelocationPlan'
import type { RelocationPlan as RelocationPlanData } from './api/relocationPlan'

const plan: RelocationPlanData = {
  id: 'filter-session-plan',
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

function response(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body } as Response
}

function mockRequests() {
  vi.stubGlobal('fetch', vi.fn((path: string) => Promise.resolve(response(
    path === '/api/relocation-plan'
      ? plan
      : { task_id: 'pack', task_title: 'Pack boxes', phase_id: 'prepare', phase_title: 'Prepare', why: ['Actionable'] },
  ))))
}

function HistoryControls() {
  const location = useLocation()
  const navigate = useNavigate()
  return <><output data-testid="route">{location.pathname}</output><button onClick={() => navigate(-1)}>History back</button><button onClick={() => navigate(1)}>History forward</button></>
}

afterEach(() => {
  sessionStorage.clear()
  vi.unstubAllGlobals()
})

describe('category filters as Plan session state', () => {
  it('restores ordered filters, filtered counts, and the pre-filter expansion snapshot after remount', async () => {
    mockRequests()
    const first = render(<RelocationPlan />)
    const filter = await screen.findByRole('button', { name: 'Filter by categories' })
    fireEvent.click(filter)
    fireEvent.click(screen.getByLabelText('Logistics'))
    expect(screen.getByRole('button', { name: /Prepare 1 remaining · 0 completed/ })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.queryByRole('button', { name: /Settle/ })).not.toBeInTheDocument()
    await waitFor(() => expect(JSON.parse(sessionStorage.getItem('gotime:plan:filter-session-plan:filters')!))
      .toEqual({ version: 1, categories: ['logistics'] }))
    first.unmount()

    render(<RelocationPlan />)
    const restored = await screen.findByRole('button', { name: 'Filter by categories' })
    expect(restored).toHaveTextContent('Categories (1)')
    expect(screen.getByRole('button', { name: /Prepare 1 remaining · 0 completed/ })).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(restored)
    expect(screen.getByLabelText('Logistics')).toBeChecked()
    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }))
    expect(screen.getByRole('button', { name: /Prepare 1 remaining · 0 completed/ })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('button', { name: /Settle 0 remaining · 1 completed/ })).toHaveAttribute('aria-expanded', 'false')
  })

  it.each([
    ['malformed', '{'],
    ['stale', JSON.stringify({ version: 0, categories: ['logistics'] })],
    ['duplicate', JSON.stringify({ version: 1, categories: ['logistics', 'logistics'] })],
    ['unknown', JSON.stringify({ version: 1, categories: ['unknown'] })],
  ])('ignores %s stored filter state', async (_name, stored) => {
    mockRequests()
    sessionStorage.setItem('gotime:plan:filter-session-plan:filters', stored)
    render(<RelocationPlan />)
    expect(await screen.findByRole('button', { name: 'Filter by categories' })).toHaveTextContent(/^Categories$/)
    expect(screen.getAllByRole('button', { name: /remaining ·/ })).toHaveLength(2)
  })

  it('restores filters before route-level scroll restoration', async () => {
    mockRequests()
    sessionStorage.setItem('gotime:plan:filter-session-plan:filters', JSON.stringify({ version: 1, categories: ['financial'] }))
    sessionStorage.setItem('gotime:plan:filter-session-plan:expansion', JSON.stringify({
      version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [],
    }))
    sessionStorage.setItem('gotime:plan:filter-session-plan:scroll', JSON.stringify({ version: 1, y: 250 }))
    Object.defineProperty(document.documentElement, 'scrollHeight', { configurable: true, value: 1000 })
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 400 })
    const scrollTo = vi.fn()
    vi.stubGlobal('scrollTo', scrollTo)
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)

    const filter = await screen.findByRole('button', { name: 'Filter by categories' })
    expect(filter).toHaveTextContent('Categories (1)')
    expect(screen.queryByRole('button', { name: /Prepare/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Settle 0 remaining · 1 completed/ })).toHaveAttribute('aria-expanded', 'true')
    expect(scrollTo).toHaveBeenCalledWith({ top: 250, left: 0, behavior: 'auto' })
  })

  it('preserves filters through Now/Plan navigation and browser Back and Forward', async () => {
    mockRequests()
    render(<MemoryRouter initialEntries={['/plan']}><App /><HistoryControls /></MemoryRouter>)
    const filter = await screen.findByRole('button', { name: 'Filter by categories' })
    fireEvent.click(filter)
    fireEvent.click(screen.getByLabelText('Logistics'))
    await waitFor(() => expect(sessionStorage.getItem('gotime:plan:filter-session-plan:filters')).toContain('logistics'))

    fireEvent.click(screen.getByRole('link', { name: 'Now' }))
    await screen.findByText('What should I do next?')
    fireEvent.click(screen.getByRole('button', { name: 'History back' }))
    await waitFor(() => expect(screen.getByTestId('route')).toHaveTextContent('/plan'))
    expect(await screen.findByRole('button', { name: 'Filter by categories' })).toHaveTextContent('Categories (1)')
    fireEvent.click(screen.getByRole('button', { name: 'History forward' }))
    await waitFor(() => expect(screen.getByTestId('route')).toHaveTextContent('/now'))
    fireEvent.click(screen.getByRole('link', { name: 'Plan' }))
    expect(await screen.findByRole('button', { name: 'Filter by categories' })).toHaveTextContent('Categories (1)')
  })
})
