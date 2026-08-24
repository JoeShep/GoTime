import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'
import App from './App'
import type { RelocationPlan } from './api/relocationPlan'
import { canonicalizePlanItemTitle } from './titleUniqueness'

const plan: RelocationPlan = {
  id: 'title-plan',
  title: 'Family plan',
  phases: [
    { id: 'prepare', title: 'Prepare', position: 10 },
    { id: 'move', title: 'Move', position: 20 },
  ],
  tasks: [
    {
      id: 'wash', title: 'Wash windows', description: null, phase_id: 'move', categories: ['housing'],
      status: 'completed', assignees: [], start_date: null, due_date: null, priority: 'medium',
      dependency_task_ids: [], blocked: false,
    },
    {
      id: 'pack', title: 'Pack boxes', description: null, phase_id: 'prepare', categories: ['logistics'],
      status: 'not_started', assignees: [], start_date: null, due_date: null, priority: 'medium',
      dependency_task_ids: [], blocked: false,
    },
  ],
  milestones: [{
    id: 'selling', title: 'Start selling our home', description: null,
    target_earliest_date: null, target_latest_date: null, status: 'pending', achieved_at: null,
  }],
  decisions: [{
    id: 'route', title: 'Choose sale route', description: null, milestone_id: 'selling',
    options: [{ id: 'public', title: 'Public', description: null }, { id: 'private', title: 'Private', description: null }],
    status: 'unresolved', selected_option_id: null,
  }],
}

function response(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response
}

function recommendation() {
  return {
    status: 'recommended', task_id: 'pack', task_title: 'Pack boxes', phase_id: 'prepare', phase_title: 'Prepare',
    why: ['Ready'], why_now: 'Ready', directly_unblocks_task_ids: [], ranking_factors: null,
  }
}

function planRequests(write?: (path: string, init: RequestInit) => Promise<Response>) {
  return vi.fn((path: string, init?: RequestInit) => {
    if (path === '/api/relocation-plan/recommendation') return Promise.resolve(response(recommendation()))
    if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(plan))
    return write?.(path, init!) ?? Promise.resolve(response(plan))
  })
}

async function openCreation(type: 'Task' | 'Milestone' | 'Decision') {
  const add = await screen.findByRole('button', { name: 'Add' })
  fireEvent.click(add)
  fireEvent.click(within(screen.getByRole('menu', { name: 'Add' })).getByRole('menuitem', { name: new RegExp(type) }))
}

beforeEach(() => {
  sessionStorage.setItem('gotime:plan:title-plan:expansion', JSON.stringify({
    version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [],
  }))
  sessionStorage.setItem('gotime:plan:title-plan:scroll', JSON.stringify({ version: 1, y: 275 }))
})

afterEach(() => {
  sessionStorage.clear()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView
})

describe('plan item title uniqueness', () => {
  it('canonicalizes capitalization and surrounding or repeated whitespace', () => {
    expect(canonicalizePlanItemTitle('  WASH\t  Windows  ')).toBe('wash windows')
    expect(canonicalizePlanItemTitle('ÉCOLE')).toBe(canonicalizePlanItemTitle('école'))
  })

  it('detects duplicate Task creation across phases and completed status without side effects', async () => {
    const fetchMock = planRequests()
    vi.stubGlobal('fetch', fetchMock)
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    await openCreation('Task')
    const title = screen.getByLabelText('Title')
    fireEvent.change(title, { target: { value: '  wash   WINDOWS  ' } })
    fireEvent.change(screen.getByLabelText('Description (optional)'), { target: { value: 'Keep this draft' } })

    expect(title).toBeInvalid()
    expect(screen.getByText('A task with this title already exists in this plan.')).toHaveClass('invalid-feedback')
    fireEvent.click(screen.getByRole('button', { name: 'Create task' }))
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(screen.getByLabelText('Description (optional)')).toHaveValue('Keep this draft')
    expect(screen.getByRole('heading', { name: 'Add task' })).toBeVisible()
    expect(screen.getByRole('button', { name: /Move 0 remaining · 1 completed/ })).toHaveAttribute('aria-expanded', 'false')
    expect(document.querySelector('.is-found')).toBeNull()
    expect(sessionStorage.getItem('gotime:plan:title-plan:scroll')).toContain('275')

    fireEvent.change(title, { target: { value: 'Wash mirrors' } })
    expect(title).not.toBeInvalid()
    expect(screen.queryByText('A task with this title already exists in this plan.')).not.toBeInTheDocument()
  })

  it('excludes the current Task during editing but rejects a rename to another Task', async () => {
    vi.stubGlobal('fetch', planRequests())
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    const pack = await screen.findByRole('article', { name: 'Pack boxes' })
    fireEvent.click(within(pack).getByRole('button', { name: 'Edit' }))
    const title = screen.getByLabelText('Title')
    fireEvent.change(title, { target: { value: '  PACK   BOXES ' } })
    expect(title).not.toBeInvalid()
    fireEvent.change(title, { target: { value: 'wash windows' } })
    expect(title).toBeInvalid()
  })

  it('detects Milestone and Decision duplicates inline while allowing cross-type titles', async () => {
    let latest = plan
    const fetchMock = planRequests(async (path, init) => {
      const body = JSON.parse(String(init.body))
      if (path === '/api/relocation-plan/milestones') {
        latest = { ...latest, milestones: [...latest.milestones, { ...body, status: 'pending', achieved_at: null }] }
      }
      return response(latest)
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)

    await openCreation('Milestone')
    const milestoneTitle = screen.getByLabelText('Name')
    fireEvent.change(milestoneTitle, { target: { value: ' start  SELLING our HOME ' } })
    expect(milestoneTitle).toBeInvalid()
    expect(screen.getByText('A milestone with this title already exists in this plan.')).toHaveClass('invalid-feedback')
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    await openCreation('Decision')
    const decisionTitle = screen.getByLabelText('Decision')
    fireEvent.change(decisionTitle, { target: { value: ' CHOOSE  sale ROUTE ' } })
    expect(decisionTitle).toBeInvalid()
    expect(screen.getByText('A decision with this title already exists in this plan.')).toHaveClass('invalid-feedback')
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    await openCreation('Milestone')
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Wash windows' } })
    expect(screen.getByLabelText('Name')).not.toBeInvalid()
    fireEvent.click(screen.getByRole('button', { name: 'Save milestone' }))
    expect(await screen.findByRole('article', { name: 'Wash windows' })).toHaveClass('is-found')
  })

  it('maps a stale backend 409 to the Task title and recovers without reveal or workspace changes', async () => {
    let attempts = 0
    let latest = plan
    const fetchMock = planRequests(async (path, init) => {
      if (path !== '/api/relocation-plan/tasks') return response(latest)
      attempts += 1
      if (attempts === 1) return response({ detail: {
        code: 'duplicate_task_title', message: 'A task with this title already exists in this plan.',
      } }, 409)
      const body = JSON.parse(String(init.body))
      latest = { ...latest, tasks: [...latest.tasks, { ...body, blocked: false }] }
      return response(latest, 201)
    })
    vi.stubGlobal('fetch', fetchMock)
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)
    await openCreation('Task')
    const title = screen.getByLabelText('Title')
    fireEvent.change(title, { target: { value: 'Apparently unique' } })
    fireEvent.change(screen.getByLabelText('Description (optional)'), { target: { value: 'Preserved' } })
    const scrollBeforeRejection = sessionStorage.getItem('gotime:plan:title-plan:scroll')
    fireEvent.click(screen.getByRole('button', { name: 'Create task' }))

    expect(await screen.findByText('A task with this title already exists in this plan.')).toHaveClass('invalid-feedback')
    expect(title).toHaveFocus()
    expect(title).toBeInvalid()
    expect(screen.getByLabelText('Description (optional)')).toHaveValue('Preserved')
    expect(screen.getByRole('button', { name: 'Create task' })).toBeEnabled()
    expect(document.querySelector('.is-found')).toBeNull()
    expect(sessionStorage.getItem('gotime:plan:title-plan:scroll')).toBe(scrollBeforeRejection)

    fireEvent.change(title, { target: { value: 'Actually unique' } })
    expect(title).not.toBeInvalid()
    fireEvent.click(screen.getByRole('button', { name: 'Create task' }))
    const created = await screen.findByRole('article', { name: 'Actually unique' })
    expect(created).toHaveFocus()
    expect(created).toHaveClass('is-found')
  })
})
