import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RelocationPlan } from './RelocationPlan'
import type { RelocationPlan as Plan } from './api/relocationPlan'

const plan: Plan = {
  id: 'hierarchy-plan', title: 'Move', milestones: [], decisions: [],
  phases: [{ id: 'prepare', title: 'Prepare', position: 10 }],
  tasks: [
    { id: 'parent', title: 'Reengage realtor', description: null, phase_id: 'prepare', categories: ['housing'], status: 'in_progress', stored_status: 'not_started', automatic_status: 'in_progress', manual_status_override: null, is_parent: true, subtask_count: 2, completed_subtask_count: 1, parent_task_id: null, subtask_position: null, assignees: [], start_date: null, due_date: null, priority: 'medium', dependency_task_ids: [], blocked: false },
    { id: 'contact', title: 'Contact realtor', description: null, phase_id: 'prepare', categories: ['housing'], status: 'completed', parent_task_id: 'parent', subtask_position: 1, assignees: [], start_date: null, due_date: null, priority: 'medium', dependency_task_ids: [], blocked: false },
    { id: 'meet', title: 'Meet realtor', description: null, phase_id: 'prepare', categories: ['financial'], status: 'not_started', parent_task_id: 'parent', subtask_position: 2, assignees: [], start_date: null, due_date: null, priority: 'medium', dependency_task_ids: [], blocked: false },
  ],
}

function response(body: unknown, status = 200): Response {
  return { ok: status < 400, status, json: async () => body } as Response
}

afterEach(() => {
  sessionStorage.clear()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('required subtasks', () => {
  it('renders a summary parent with collapsed independently persisted subtasks and leaf-only counts', async () => {
    sessionStorage.setItem('gotime:plan:hierarchy-plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [] }))
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response(plan))))
    const first = render(<RelocationPlan />)
    const progress = await screen.findByRole('button', { name: '1 of 2 required subtasks completed' })
    expect(progress).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('button', { name: /Prepare 1 remaining · 1 completed/ })).toBeVisible()
    expect(screen.queryByRole('article', { name: 'Meet realtor' })).not.toBeInTheDocument()
    fireEvent.click(progress)
    expect(progress).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('article', { name: 'Meet realtor' })).toBeVisible()
    await waitFor(() => expect(sessionStorage.getItem('gotime:plan:hierarchy-plan:subtasks')).toContain('parent'))
    first.unmount()
    render(<RelocationPlan />)
    expect(await screen.findByRole('article', { name: 'Meet realtor' })).toBeVisible()
  })

  it('keeps a matching parent for filter context and offers Add subtask with Part of preselected', async () => {
    sessionStorage.setItem('gotime:plan:hierarchy-plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [] }))
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response(plan))))
    render(<RelocationPlan />)
    await screen.findByText('1 of 2 required subtasks completed')
    fireEvent.click(screen.getByRole('button', { name: 'Filter by categories' }))
    fireEvent.click(screen.getByLabelText('Financial'))
    expect(screen.getByRole('article', { name: 'Reengage realtor' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Add subtask' }))
    expect(screen.getByLabelText('This task is a subtask')).toBeChecked()
    expect(screen.getByText('Part of Reengage realtor')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Change' })).toBeVisible()
    expect(screen.getByLabelText('Phase')).toBeDisabled()
  })

  it('warns before a conflicting parent status and shows the manual override control', async () => {
    sessionStorage.setItem('gotime:plan:hierarchy-plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [] }))
    const overridden: Plan = { ...plan, tasks: plan.tasks.map((task) => task.id === 'parent' ? { ...task, status: 'completed', manual_status_override: 'completed' } : task) }
    let statusRequests = 0
    vi.stubGlobal('fetch', vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith('/status')) {
        statusRequests += 1
        return statusRequests === 1
          ? Promise.resolve(response({ detail: { code: 'parent_status_override_confirmation_required', message: 'Confirm override.' } }, 409))
          : Promise.resolve(response(overridden))
      }
      return Promise.resolve(response(plan))
    }))
    render(<RelocationPlan />)
    const parent = await screen.findByRole('article', { name: 'Reengage realtor' })
    fireEvent.change(within(parent).getByLabelText('Status for Reengage realtor'), { target: { value: 'completed' } })
    const dialog = await screen.findByRole('dialog', { name: 'Complete this parent manually?' })
    expect(within(dialog).getByText(/may unblock downstream work/)).toBeVisible()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Complete parent manually' }))
    expect(await within(parent).findByText('Manual status')).toBeVisible()
    expect(within(parent).getByRole('button', { name: 'Return to automatic status' })).toBeVisible()
    expect(statusRequests).toBe(2)
  })

  it('reorders the complete sibling list immediately and retains focus on the moved subtask', async () => {
    sessionStorage.setItem('gotime:plan:hierarchy-plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [] }))
    sessionStorage.setItem('gotime:plan:hierarchy-plan:subtasks', JSON.stringify(['parent']))
    const reordered: Plan = { ...plan, tasks: plan.tasks.map((task) => task.id === 'contact' ? { ...task, subtask_position: 2 } : task.id === 'meet' ? { ...task, subtask_position: 1 } : task) }
    const fetchMock = vi.fn((path: string, init?: RequestInit) => path.endsWith('/subtasks/order') ? Promise.resolve(response(reordered)) : Promise.resolve(response(plan)))
    vi.stubGlobal('fetch', fetchMock)
    render(<RelocationPlan />)
    const contact = await screen.findByRole('article', { name: 'Contact realtor' })
    expect(within(contact).getByRole('button', { name: 'Move up' })).toBeDisabled()
    fireEvent.click(within(contact).getByRole('button', { name: 'Move down' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({ child_task_ids: ['meet', 'contact'] })
    await waitFor(() => expect(within(contact).getByRole('button', { name: 'Move up' })).toHaveFocus())
    expect(sessionStorage.getItem('gotime:plan:hierarchy-plan:subtasks')).toContain('parent')
  })

  it('uses a searchable eligible-parent picker and validates a missing selection inline', async () => {
    sessionStorage.setItem('gotime:plan:hierarchy-plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [] }))
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response(plan))))
    render(<RelocationPlan />)
    await screen.findByRole('button', { name: 'Add' })
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))
    fireEvent.click(screen.getByRole('menuitem', { name: /Task/ }))
    fireEvent.click(screen.getByLabelText('This task is a subtask'))
    expect(screen.getByRole('searchbox', { name: 'Parent Task' })).toBeVisible()
    expect(screen.getByRole('option', { name: /Reengage realtor.*Housing.*In progress/ })).toBeVisible()
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'New required work' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create task' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Select the parent Task')
    fireEvent.click(screen.getByRole('option', { name: /Reengage realtor/ }))
    expect(screen.getByText('Part of Reengage realtor')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Change' }))
    expect(screen.getByRole('searchbox', { name: 'Parent Task' })).toHaveFocus()
  })

  it('detaches an existing subtask by unchecking the hierarchy choice', async () => {
    sessionStorage.setItem('gotime:plan:hierarchy-plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [] }))
    sessionStorage.setItem('gotime:plan:hierarchy-plan:subtasks', JSON.stringify(['parent']))
    const detached: Plan = { ...plan, tasks: plan.tasks.map((task) => task.id === 'meet' ? { ...task, parent_task_id: null, subtask_position: null } : task) }
    const fetchMock = vi.fn((path: string, init?: RequestInit) => init?.method === 'PUT' ? Promise.resolve(response(detached)) : Promise.resolve(response(plan)))
    vi.stubGlobal('fetch', fetchMock)
    render(<RelocationPlan />)
    const child = await screen.findByRole('article', { name: 'Meet realtor' })
    fireEvent.click(within(child).getByRole('button', { name: 'Edit' }))
    fireEvent.click(screen.getByLabelText('This task is a subtask'))
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toMatchObject({ parent_task_id: null, subtask_position: null })
  })

  it('confirms a first required-subtask attachment in the application and restores focus on cancel', async () => {
    const ordinaryParent = { ...plan.tasks[0], id: 'ordinary', title: 'Ordinary outcome', status: 'in_progress' as const, automatic_status: null, is_parent: false, subtask_count: 0, completed_subtask_count: 0 }
    const initial = { ...plan, tasks: [...plan.tasks, ordinaryParent] }
    const fetchMock = vi.fn((path: string) => path === '/api/relocation-plan' ? Promise.resolve(response(initial)) : Promise.resolve(response(initial)))
    vi.stubGlobal('fetch', fetchMock)
    render(<RelocationPlan />)
    await screen.findByRole('button', { name: 'Add' })
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))
    fireEvent.click(screen.getByRole('menuitem', { name: /Task/ }))
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'First required work' } })
    fireEvent.click(screen.getByLabelText('This task is a subtask'))
    fireEvent.click(screen.getByRole('option', { name: /Ordinary outcome/ }))
    const create = screen.getByRole('button', { name: 'Create task' })
    fireEvent.click(create)
    const dialog = await screen.findByRole('dialog', { name: 'Attach the first required subtask?' })
    expect(within(dialog).getByText(/will become not started/)).toBeVisible()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(create).toHaveFocus())
    expect(fetchMock).toHaveBeenCalledTimes(1)
    fireEvent.click(create)
    fireEvent.click(await screen.findByRole('button', { name: 'Attach required subtask' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  })

  it('uses the application modal before moving a parent and all required subtasks', async () => {
    sessionStorage.setItem('gotime:plan:hierarchy-plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [] }))
    const phasePlan: Plan = { ...plan, phases: [...plan.phases, { id: 'move', title: 'Move', position: 20 }] }
    const moved: Plan = { ...phasePlan, tasks: phasePlan.tasks.map((task) => ({ ...task, phase_id: 'move' })) }
    let updateRequests = 0
    vi.stubGlobal('fetch', vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith('/tasks/parent') && init?.method === 'PUT') {
        updateRequests += 1
        return JSON.parse(String(init.body)).confirm_parent_phase_move
          ? Promise.resolve(response(moved))
          : Promise.resolve(response({ detail: { code: 'parent_phase_move_confirmation_required', message: 'Confirm move.' } }, 409))
      }
      return Promise.resolve(response(phasePlan))
    }))
    render(<RelocationPlan />)
    const parent = await screen.findByRole('article', { name: 'Reengage realtor' })
    fireEvent.click(within(parent).getByRole('button', { name: 'Edit' }))
    fireEvent.change(screen.getByLabelText('Phase'), { target: { value: 'move' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    const dialog = await screen.findByRole('dialog', { name: 'Move parent and 2 required subtasks?' })
    expect(within(dialog).getByText(/Every required subtask will move/)).toBeVisible()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Move parent and subtasks' }))
    await waitFor(() => expect(updateRequests).toBe(2))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })
})
