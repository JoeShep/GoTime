import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { generateTaskId, RelocationPlan } from './RelocationPlan'
import type { RelocationPlan as RelocationPlanData } from './api/relocationPlan'

const phases = [
  { id: 'decide', title: 'Decide where and how to move', position: 10 },
  { id: 'prepare', title: 'Prepare for the move', position: 20 },
  { id: 'move', title: 'Complete the move', position: 30 },
  { id: 'settle', title: 'Settle in', position: 40 },
]

const plan: RelocationPlanData = {
  id: 'family-relocation-plan',
  title: 'Relocate the family to Northern California',
  phases,
  tasks: [
    {
      id: 'choose-mover',
      title: 'Choose a mover',
      description: 'Compare the final quotes.',
      phase_id: 'prepare',
      category: 'logistics',
      status: 'not_started',
      assignees: ['Joe', 'Sarah'],
      start_date: '2026-09-01',
      due_date: '2026-09-10',
      priority: 'high',
      dependency_task_ids: [],
      blocked: false,
    },
    {
      id: 'pay-deposit',
      title: 'Pay the mover deposit',
      description: null,
      phase_id: 'prepare',
      category: 'financial',
      status: 'not_started',
      assignees: ['Sarah'],
      start_date: null,
      due_date: null,
      priority: 'critical',
      dependency_task_ids: ['choose-mover'],
      blocked: true,
    },
  ],
}

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

function mockPlanRequests(mutationPlan = plan) {
  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(plan))
    return Promise.resolve(response(mutationPlan))
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('persistent relocation plan', () => {
  it('shows a loading state while retrieving the plan', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => undefined)))
    render(<RelocationPlan />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading relocation plan')
  })

  it('renders ordered phases, tasks, blocked state, and dependency context', async () => {
    mockPlanRequests()
    render(<RelocationPlan />)

    expect(await screen.findByRole('heading', { name: 'Choose a mover' })).toBeVisible()
    const phaseHeadings = screen.getAllByRole('heading', { level: 3 })
    expect(phaseHeadings.map((heading) => heading.textContent)).toEqual(phases.map((phase) => phase.title))
    expect(screen.getByText('Blocked')).toBeVisible()
    expect(screen.getByText(/Depends on:/).closest('p')).toHaveTextContent('Choose a mover')
    expect(screen.getAllByText('No tasks in this phase yet.')).toHaveLength(3)
  })

  it('adds a task with selected dependencies', async () => {
    const fetchMock = mockPlanRequests()
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })

    fireEvent.click(screen.getByRole('button', { name: 'Add task' }))
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Pack the kitchen' } })
    fireEvent.change(screen.getByLabelText('Assignees'), { target: { value: 'Joe, Sarah' } })
    fireEvent.click(screen.getByLabelText('Choose a mover (Not started)'))
    fireEvent.click(screen.getByRole('button', { name: 'Save task' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(screen.getByText('Task added.')).toBeVisible()
    const [, init] = fetchMock.mock.calls[1]
    expect(fetchMock.mock.calls[1][0]).toBe('/api/relocation-plan/tasks')
    expect(JSON.parse(String(init?.body))).toEqual(expect.objectContaining({
      title: 'Pack the kitchen',
      assignees: ['Joe', 'Sarah'],
      dependency_task_ids: ['choose-mover'],
      description: null,
      start_date: null,
      due_date: null,
    }))
  })

  it('creates a valid bounded ID without changing a 200-character title', async () => {
    const longTitle = 'A'.repeat(200)
    const fetchMock = mockPlanRequests()
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })

    fireEvent.click(screen.getByRole('button', { name: 'Add task' }))
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: longTitle } })
    fireEvent.change(screen.getByLabelText('Assignees'), { target: { value: 'Joe' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save task' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    const body = JSON.parse(String(fetchMock.mock.calls[1][1]?.body)) as {
      id: string
      title: string
    }
    expect(body.title).toBe(longTitle)
    expect(body.id).toMatch(/^[a-z0-9][a-z0-9-]*$/)
    expect(body.id.length).toBeLessThanOrEqual(64)
  })

  it('generates distinct valid IDs for repeated identical titles', () => {
    const first = generateTaskId('Pack the kitchen')
    const second = generateTaskId('Pack the kitchen')

    expect(first).not.toBe(second)
    for (const id of [first, second]) {
      expect(id).toMatch(/^[a-z0-9][a-z0-9-]*$/)
      expect(id.length).toBeLessThanOrEqual(64)
      expect(id).toMatch(/^pack-the-kitchen-/)
    }
  })

  it('edits with a complete replacement without losing untouched fields', async () => {
    const fetchMock = mockPlanRequests()
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })

    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0])
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Choose the mover' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save task' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    const [path, init] = fetchMock.mock.calls[1]
    expect(path).toBe('/api/relocation-plan/tasks/choose-mover')
    expect(JSON.parse(String(init?.body))).toEqual({
      title: 'Choose the mover',
      description: 'Compare the final quotes.',
      phase_id: 'prepare',
      category: 'logistics',
      status: 'not_started',
      assignees: ['Joe', 'Sarah'],
      start_date: '2026-09-01',
      due_date: '2026-09-10',
      priority: 'high',
      dependency_task_ids: [],
    })
  })

  it('intentionally clears nullable fields with explicit null values', async () => {
    const fetchMock = mockPlanRequests()
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })

    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0])
    fireEvent.change(screen.getByLabelText('Description (optional)'), { target: { value: '' } })
    fireEvent.change(screen.getByLabelText('Start date (optional)'), { target: { value: '' } })
    fireEvent.change(screen.getByLabelText('Due date (optional)'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save task' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual(
      expect.objectContaining({
        description: null,
        start_date: null,
        due_date: null,
      }),
    )
  })

  it('changes task status through the narrow status endpoint', async () => {
    const fetchMock = mockPlanRequests()
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })

    fireEvent.change(screen.getByLabelText('Status for Choose a mover'), { target: { value: 'completed' } })

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(fetchMock.mock.calls[1][0]).toBe('/api/relocation-plan/tasks/choose-mover/status')
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({ status: 'completed' })
  })

  it('visibly unblocks a dependent from the returned status-update plan', async () => {
    const completedPlan: RelocationPlanData = {
      ...plan,
      tasks: plan.tasks.map((task) =>
        task.id === 'choose-mover'
          ? { ...task, status: 'completed' }
          : { ...task, blocked: false },
      ),
    }
    mockPlanRequests(completedPlan)
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })
    expect(screen.getByText('Blocked')).toBeVisible()

    fireEvent.change(screen.getByLabelText('Status for Choose a mover'), {
      target: { value: 'completed' },
    })

    expect(await screen.findByText('Status updated for Choose a mover.')).toBeVisible()
    expect(screen.queryByText('Blocked')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Status for Choose a mover')).toHaveValue('completed')
  })

  it('does not offer the edited task as its own dependency', async () => {
    mockPlanRequests()
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })
    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0])

    expect(screen.queryByLabelText('Choose a mover (Not started)')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Pay the mover deposit (Not started)')).toBeVisible()
  })

  it('shows backend validation details without discarding the editor', async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(plan))
      return Promise.resolve(response({ detail: 'Task dependencies cannot contain a cycle.' }, 422))
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })

    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0])
    fireEvent.click(screen.getByLabelText('Pay the mover deposit (Not started)'))
    fireEvent.click(screen.getByRole('button', { name: 'Save task' }))

    expect(await screen.findByText('Task dependencies cannot contain a cycle.')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Edit task' })).toBeVisible()
  })

  it('shows a network error when the plan cannot be loaded', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('The server is unavailable.')))
    render(<RelocationPlan />)

    expect(await screen.findByText('The server is unavailable.')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Add task' })).not.toBeInTheDocument()
  })
})
