import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, useLocation, useNavigate } from 'react-router'
import App from './App'
import type { RelocationPlan, RelocationTaskRecommendation } from './api/relocationPlan'

const plan: RelocationPlan = {
  id: 'recommendation-plan',
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

function recommendation(taskId: string | null): RelocationTaskRecommendation {
  const task = plan.tasks.find((candidate) => candidate.id === taskId)
  return {
    status: taskId ? 'recommended' : 'no_actionable_task',
    task_id: taskId,
    task_title: task?.title ?? null,
    phase_id: task?.phase_id ?? null,
    phase_title: plan.phases.find((phase) => phase.id === task?.phase_id)?.title ?? null,
    why: ['It is actionable.'],
    why_now: 'It is ready now.',
    directly_unblocks_task_ids: [],
    ranking_factors: null,
  }
}

const parentPlan: RelocationPlan = {
  ...plan,
  tasks: [
    {
      id: 'parent', title: 'Reengage with the realtor', description: null, phase_id: 'prepare', categories: ['housing'],
      status: 'completed', assignees: ['Anne', 'Joe'], start_date: null, due_date: null, priority: 'high',
      dependency_task_ids: [], blocked: false, is_parent: true, subtask_count: 1, completed_subtask_count: 1,
      automatic_status: 'completed', stored_status: 'not_started', manual_status_override: null,
    },
    {
      id: 'child', title: 'Contact the realtor', description: null, phase_id: 'prepare', categories: ['housing'],
      status: 'completed', assignees: ['Anne', 'Joe'], start_date: null, due_date: null, priority: 'medium',
      dependency_task_ids: [], blocked: false, parent_task_id: 'parent', subtask_position: 0,
    },
  ],
}

const childRecommendation: RelocationTaskRecommendation = {
  status: 'recommended', candidate_type: 'task', task_id: 'child', task_title: 'Contact the realtor',
  phase_id: 'prepare', phase_title: 'Prepare', why: ['Completing it unlocks 1 Task.'], why_now: '',
  directly_unblocks_task_ids: [], ranking_factors: null,
  signals: [{
    kind: 'inherited_decision_preparation', decision_id: 'decision', decision_title: 'Choose how to market our home',
    preparation_task_id: 'parent', preparation_task_title: 'Reengage with the realtor', parent_task_id: 'parent',
    parent_task_title: 'Reengage with the realtor', blocked_task_id: null, blocked_task_title: null,
    dependency_path_task_ids: ['child'],
  }],
}

function response(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body } as Response
}

function mockRequests(nextRecommendation: RelocationTaskRecommendation, nextPlan = plan) {
  return vi.fn((path: string) => Promise.resolve(response(
    path.startsWith('/api/relocation-plan/recommendation?') ? nextRecommendation : nextPlan,
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

describe('cross-route Recommendation targeting', () => {
  it('shows one compact View task button only for a stable recommended Task ID', async () => {
    vi.stubGlobal('fetch', mockRequests(recommendation('pack')))
    const first = render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    const button = await screen.findByRole('button', { name: 'View task' })
    expect(button).toHaveClass('recommendation-task-link')
    expect(button.closest('.primary-recommendation')).toBeInTheDocument()
    expect(button.closest('.primary-recommendation')).not.toHaveAttribute('role', 'button')
    first.unmount()

    vi.stubGlobal('fetch', mockRequests(recommendation(null)))
    render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    await screen.findByRole('heading', { name: 'No task is actionable right now' })
    expect(screen.queryByRole('button', { name: 'View task' })).not.toBeInTheDocument()
  })

  it('pushes Plan once, preserves a compatible filter, reveals once, saves position, and Back returns to Now', async () => {
    sessionStorage.setItem('gotime:plan:recommendation-plan:filters', JSON.stringify({ version: 1, categories: ['logistics'] }))
    vi.stubGlobal('fetch', mockRequests(recommendation('pack')))
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    render(<MemoryRouter initialEntries={['/now']}><App /><HistoryProbe /></MemoryRouter>)

    fireEvent.click(await screen.findByRole('button', { name: 'View task' }))
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/plan'))
    const task = await screen.findByRole('article', { name: 'Pack boxes' })
    await waitFor(() => expect(task).toHaveFocus())
    expect(task).toHaveClass('is-found')
    expect(screen.getByRole('button', { name: /Prepare 1 remaining/ })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: 'Filter by categories' })).toHaveTextContent('Categories (1)')
    expect(screen.queryByText(/Category filter cleared/)).not.toBeInTheDocument()
    await waitFor(() => expect(sessionStorage.getItem('gotime:plan:recommendation-plan:scroll')).not.toBeNull())

    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/now'))
  })

  it('clears an incompatible filter and opens the completed destination without changing unrelated phases', async () => {
    sessionStorage.setItem('gotime:plan:recommendation-plan:filters', JSON.stringify({ version: 1, categories: ['logistics'] }))
    vi.stubGlobal('fetch', mockRequests(recommendation('deposit')))
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)

    fireEvent.click(await screen.findByRole('button', { name: 'View task' }))
    const task = await screen.findByRole('article', { name: 'Pay deposit' })
    await waitFor(() => expect(task).toHaveFocus())
    expect(screen.getByRole('button', { name: /Settle 0 remaining · 1 completed/ })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: 'Completed (1)' })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: /Prepare 1 remaining/ })).toHaveAttribute('aria-expanded', 'false')
    expect(await screen.findByText('Category filter cleared to show “Pay deposit.”')).toBeVisible()
    await waitFor(() => expect(sessionStorage.getItem('gotime:plan:recommendation-plan:filters')).toContain('"categories":[]'))
  })

  it('does not replay Recommendation focus or highlighting after later Plan navigation', async () => {
    vi.stubGlobal('fetch', mockRequests(recommendation('pack')))
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    const first = render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: 'View task' }))
    expect(await screen.findByRole('article', { name: 'Pack boxes' })).toHaveClass('is-found')
    first.unmount()

    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    expect(await screen.findByRole('article', { name: 'Pack boxes' })).not.toHaveClass('is-found')
  })

  it('stays on Plan and shows a brief dismissible notice when the recommended Task disappeared', async () => {
    vi.stubGlobal('fetch', mockRequests({
      ...recommendation('pack'),
      task_id: 'removed-task',
      task_title: 'Removed task',
    }))
    render(<MemoryRouter initialEntries={['/now']}><App /><HistoryProbe /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: 'View task' }))

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/plan'))
    const notice = await screen.findByText('The recommended task is no longer available.')
    expect(notice).toBeVisible()
    fireEvent.click(within(notice.closest('[role="status"]')!).getByRole('button', { name: 'Close alert' }))
    await waitFor(() => expect(screen.queryByText('The recommended task is no longer available.')).not.toBeInTheDocument())
    expect(screen.getByTestId('location')).toHaveTextContent('/plan')
  })

  it('targets the parent through the established reveal path while preserving the child action', async () => {
    vi.stubGlobal('fetch', mockRequests(childRecommendation, parentPlan))
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    const first = render(<MemoryRouter initialEntries={['/now']}><App /><HistoryProbe /></MemoryRouter>)

    const parentLink = await screen.findByRole('button', { name: 'View parent task Reengage with the realtor' })
    parentLink.focus()
    expect(parentLink).toHaveFocus()
    fireEvent.keyDown(parentLink, { key: 'Enter', code: 'Enter' })
    parentLink.click()
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/plan'))
    const parent = await screen.findByRole('article', { name: 'Reengage with the realtor' })
    await waitFor(() => expect(parent).toHaveFocus())
    expect(parent).toHaveClass('is-found')
    expect(screen.getByRole('button', { name: /Prepare 0 remaining · 1 completed/ })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: 'Completed (1)' })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: /1 of 1 required subtask completed/ })).toHaveAttribute('aria-expanded', 'true')
    first.unmount()

    vi.stubGlobal('fetch', mockRequests(childRecommendation, parentPlan))
    render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: 'View task' }))
    const child = await screen.findByRole('article', { name: 'Contact the realtor' })
    await waitFor(() => expect(child).toHaveFocus())
    expect(child).toHaveClass('is-found')
  })
})
