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
    expect(await screen.findByText('1 of 2 subtasks completed')).toBeVisible()
    expect(screen.getByRole('button', { name: /Prepare 1 remaining · 1 completed/ })).toBeVisible()
    expect(screen.queryByRole('article', { name: 'Meet realtor' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show subtasks' }))
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
    await screen.findByText('1 of 2 subtasks completed')
    fireEvent.click(screen.getByRole('button', { name: 'Filter by categories' }))
    fireEvent.click(screen.getByLabelText('Financial'))
    expect(screen.getByRole('article', { name: 'Reengage realtor' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Add subtask' }))
    expect(screen.getByLabelText(/Part of/)).toHaveValue('parent')
    expect(screen.getByLabelText('Phase')).toBeDisabled()
    expect(screen.getByLabelText('Subtask order')).toBeVisible()
  })

  it('warns before a conflicting parent status and shows the manual override control', async () => {
    sessionStorage.setItem('gotime:plan:hierarchy-plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [] }))
    const overridden: Plan = { ...plan, tasks: plan.tasks.map((task) => task.id === 'parent' ? { ...task, status: 'completed', manual_status_override: 'completed' } : task) }
    let statusRequests = 0
    vi.stubGlobal('confirm', vi.fn(() => true))
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
    expect(await within(parent).findByText('Manual status')).toBeVisible()
    expect(within(parent).getByRole('button', { name: 'Return to automatic status' })).toBeVisible()
    expect(statusRequests).toBe(2)
  })
})
