import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RelocationPlan } from './RelocationPlan'
import type { RelocationPlan as Plan, RelocationTask } from './api/relocationPlan'

const phases = [
  { id: 'prepare', title: 'Prepare', position: 10 },
  { id: 'move', title: 'Move', position: 20 },
]

const parent: RelocationTask = {
  id: 'parent', title: 'Parent task', description: null, phase_id: 'prepare', categories: ['housing'],
  status: 'in_progress', assignees: [], start_date: null, due_date: null, priority: 'medium',
  dependency_task_ids: [], blocked: false, is_parent: true, subtask_count: 1, completed_subtask_count: 0,
  stored_status: 'not_started', automatic_status: 'in_progress', manual_status_override: null,
}
const child: RelocationTask = {
  id: 'child', title: 'Child task', description: 'Original child draft', phase_id: 'prepare', categories: ['housing'],
  status: 'not_started', assignees: [], start_date: null, due_date: null, priority: 'medium',
  dependency_task_ids: [], blocked: false, parent_task_id: 'parent', subtask_position: 0,
}
const ordinary: RelocationTask = {
  id: 'ordinary', title: 'Ordinary task', description: 'Original draft', phase_id: 'prepare', categories: ['housing'],
  status: 'not_started', assignees: [], start_date: null, due_date: null, priority: 'medium',
  dependency_task_ids: [], blocked: false,
}
const initialPlan: Plan = { id: 'plan', title: 'Plan', phases, tasks: [parent, child, ordinary], milestones: [], decisions: [] }

const response = (body: unknown, status = 200): Response => ({
  ok: status >= 200 && status < 300, status, json: async () => body,
}) as Response

function mockSave(updated: Plan, failure = false) {
  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(initialPlan))
    if (failure) return Promise.resolve(response({ detail: 'Save failed.' }, 500))
    return Promise.resolve(response(updated))
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function storeView(filters: string[] = []) {
  sessionStorage.setItem('gotime:plan:plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [] }))
  sessionStorage.setItem('gotime:plan:plan:filters', JSON.stringify({ version: 1, categories: filters }))
  sessionStorage.setItem('gotime:plan:plan:subtasks', JSON.stringify(['parent']))
}

async function editTask(title: string) {
  const card = await screen.findByRole('article', { name: title })
  fireEvent.click(within(card).getByRole('button', { name: 'Edit' }))
  return screen.findByRole('heading', { name: 'Edit task' })
}

beforeEach(() => {
  storeView()
  Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
  vi.stubGlobal('scrollTo', vi.fn())
})

afterEach(() => {
  sessionStorage.clear()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView
})

describe('existing Task edit return', () => {
  it('returns an ordinary same-location save to its Edit control without unnecessary scrolling', async () => {
    mockSave({ ...initialPlan, tasks: initialPlan.tasks.map((task) => task.id === 'ordinary' ? { ...task, description: 'Saved' } : task) })
    const bounds = vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({ top: 100, bottom: 300 } as DOMRect)
    render(<RelocationPlan />)
    await editTask('Ordinary task')
    fireEvent.change(screen.getByLabelText('Description (optional)'), { target: { value: 'Saved' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    const card = await screen.findByRole('article', { name: 'Ordinary task' })
    await waitFor(() => expect(within(card).getByRole('button', { name: 'Edit' })).toHaveFocus())
    expect(card).toHaveClass('is-found')
    expect((Element.prototype.scrollIntoView as ReturnType<typeof vi.fn>)).not.toHaveBeenCalledWith(expect.objectContaining({ block: 'center' }))
    bounds.mockRestore()
  })

  it('reveals a saved subtask in its current parent and handles attachment and detachment from the returned Plan', async () => {
    const attached: Plan = { ...initialPlan, tasks: initialPlan.tasks.map((task) => task.id === 'ordinary' ? { ...task, parent_task_id: 'parent', subtask_position: 1 } : task) }
    mockSave(attached)
    const first = render(<RelocationPlan />)
    await editTask('Ordinary task')
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await screen.findByRole('article', { name: 'Ordinary task' })
    await waitFor(() => {
      expect(document.activeElement).toHaveAttribute('data-task-edit-control')
      expect(document.activeElement?.closest('article')).toHaveAttribute('id', 'task-ordinary')
    })
    expect(screen.getByRole('button', { name: /1 of 1 required subtask completed|0 of 1 required subtask completed/ })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('article', { name: 'Ordinary task' })).toHaveClass('is-subtask', 'is-found')
    first.unmount()

    storeView()
    const detached: Plan = { ...initialPlan, tasks: initialPlan.tasks.map((task) => task.id === 'child' ? { ...task, parent_task_id: null, subtask_position: null } : task) }
    mockSave(detached)
    render(<RelocationPlan />)
    await editTask('Child task')
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await screen.findByRole('article', { name: 'Child task' })
    await waitFor(() => {
      expect(document.activeElement).toHaveAttribute('data-task-edit-control')
      expect(document.activeElement?.closest('article')).toHaveAttribute('id', 'task-child')
    })
    expect(screen.getByRole('article', { name: 'Child task' })).not.toHaveClass('is-subtask')
    expect(screen.getByRole('article', { name: 'Child task' })).toHaveClass('is-found')
  })

  it('resolves phase and Completed movement and respects reduced motion', async () => {
    const moved: Plan = { ...initialPlan, tasks: initialPlan.tasks.map((task) => task.id === 'ordinary' ? { ...task, phase_id: 'move', status: 'completed' } : task) }
    mockSave(moved)
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true }))
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({ top: 1200, bottom: 1400 } as DOMRect)
    render(<RelocationPlan />)
    await editTask('Ordinary task')
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    const card = await screen.findByRole('article', { name: 'Ordinary task' })
    await waitFor(() => {
      expect(document.activeElement).toHaveAttribute('data-task-edit-control')
      expect(document.activeElement?.closest('article')).toHaveAttribute('id', 'task-ordinary')
    })
    expect(screen.getByRole('button', { name: /Move 0 remaining · 1 completed/ })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: 'Completed (1)' })).toHaveAttribute('aria-expanded', 'true')
    expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({ behavior: 'auto', block: 'center' })
  })

  it('returns Cancel to the original control and scroll position without a save highlight', async () => {
    mockSave(initialPlan)
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 640 })
    render(<RelocationPlan />)
    await editTask('Ordinary task')
    fireEvent.change(screen.getByLabelText('Description (optional)'), { target: { value: 'Unsaved' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    const card = await screen.findByRole('article', { name: 'Ordinary task' })
    await waitFor(() => expect(within(card).getByRole('button', { name: 'Edit' })).toHaveFocus())
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 640, left: 0, behavior: 'auto' })
    expect(card).not.toHaveClass('is-found')
    expect(screen.queryByDisplayValue('Unsaved')).not.toBeInTheDocument()
  })

  it('preserves a compatible filter and offers explicit established reveal when a save becomes hidden', async () => {
    storeView(['housing'])
    const hidden: Plan = { ...initialPlan, tasks: initialPlan.tasks.map((task) => task.id === 'ordinary' ? { ...task, categories: ['financial'] } : task) }
    mockSave(hidden)
    render(<RelocationPlan />)
    await editTask('Ordinary task')
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    const show = await screen.findByRole('button', { name: 'Show task' })
    await waitFor(() => expect(show).toHaveFocus())
    expect(screen.getByText('Task saved but hidden by the current filter.')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Filter by categories' })).toHaveTextContent('Categories (1)')
    expect(screen.queryByRole('article', { name: 'Ordinary task' })).not.toBeInTheDocument()
    fireEvent.click(show)
    const card = await screen.findByRole('article', { name: 'Ordinary task' })
    await waitFor(() => expect(card).toHaveFocus())
    expect(card).toHaveClass('is-found')
    expect(screen.getByRole('button', { name: 'Filter by categories' })).toHaveTextContent('Categories')
  })

  it('keeps the editor and draft open after persistence failure', async () => {
    mockSave(initialPlan, true)
    render(<RelocationPlan />)
    await editTask('Ordinary task')
    fireEvent.change(screen.getByLabelText('Description (optional)'), { target: { value: 'Keep this draft' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    expect(await screen.findByText('Save failed.')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Edit task' })).toBeVisible()
    expect(screen.getByLabelText('Description (optional)')).toHaveValue('Keep this draft')
    expect(screen.queryByText('Task saved but hidden by the current filter.')).not.toBeInTheDocument()
  })
})
