import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MilestoneDecisionFoundation } from './MilestoneDecisionFoundation'
import { RelocationPlan } from './RelocationPlan'
import type { RelocationPlan as Plan, RelocationTask } from './api/relocationPlan'


const fixedPlan: Plan = {
  id: 'family-relocation-plan', title: 'Family plan',
  phases: [{ id: 'prepare', title: 'Prepare for the move', position: 10 }],
  tasks: [{
    id: 'pack', title: 'Pack', description: null, phase_id: 'prepare', categories: [],
    status: 'not_started', assignees: [], start_date: null, due_date: null,
    priority: 'medium', dependency_task_ids: [], blocked: false,
    expected_elapsed_min_days: null, expected_elapsed_max_days: null,
  }],
  decisions: [],
  milestones: [{
    id: 'move', title: 'Move out', description: null,
    target_earliest_date: '2027-03-12', target_latest_date: '2027-03-12',
    timing_mode: 'fixed_date', governed_phase_id: 'prepare', status: 'pending',
    achieved_at: null, timing: {
      status: 'timing_incomplete', summary: 'Add expected elapsed time to the related work before GoTime can calculate when this phase should begin.',
      governed_task_ids: ['pack'], critical_path_task_ids: [], actionable_task_ids: ['pack'],
      missing_duration_task_ids: ['pack'], duration_min_days: null, duration_max_days: null,
      start_window_opening: null, conservative_latest_start: null,
      last_plausible_start: null, conflicts: [],
    },
  }],
}

const response = (body: unknown): Response => ({ ok: true, status: 200, json: async () => body }) as Response

beforeEach(() => sessionStorage.clear())
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); sessionStorage.clear() })

describe('lean Milestone timing', () => {
  it('edits a fixed date and one selected phase with the future-work explanation', () => {
    render(<MilestoneDecisionFoundation plan={fixedPlan} onPlanUpdated={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /Move out/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }))
    expect(screen.getByRole('radio', { name: 'Fixed date' })).toBeChecked()
    expect(document.getElementById('milestone-fixed-date')).toHaveValue('2027-03-12')
    expect(screen.getByRole('combobox', { name: 'Apply this date to Tasks in' })).toHaveValue('prepare')
    expect(screen.getByText('Every active Task in the selected phase—including Tasks added later—will be planned backward from this date.')).toBeVisible()
  })

  it('distinguishes Timing incomplete, expands details accessibly, and requests a time estimate', () => {
    const target = vi.fn()
    render(<MilestoneDecisionFoundation plan={fixedPlan} onPlanUpdated={vi.fn()} onTaskEstimateRequested={target} />)
    expect(screen.getByText('Fixed date: Mar 12, 2027')).toBeVisible()
    expect(screen.getByText('Timing incomplete', { selector: '.badge' })).toBeVisible()
    const view = screen.getByRole('button', { name: 'View timing' })
    expect(view).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(view)
    expect(view).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('This date applies to Tasks in:')).toBeVisible()
    expect(screen.queryByText(/governed phase/i)).not.toBeInTheDocument()
    expect(screen.getByText('Missing time estimates')).toBeVisible()
    const estimate = screen.getByRole('button', { name: 'Add time estimate for Pack' })
    expect(estimate).toHaveTextContent('Estimate time')
    fireEvent.click(estimate)
    expect(target).toHaveBeenCalledWith(expect.objectContaining({ id: 'pack' }), 'move')
    expect(JSON.parse(sessionStorage.getItem('gotime:milestone-timing:family-relocation-plan:v1') ?? '[]')).toContain('move')
  })

  it('does not render timing disclosure for a target window or reserve its details region', () => {
    const plan = structuredClone(fixedPlan)
    plan.milestones[0] = {
      ...plan.milestones[0], timing_mode: 'target_window', governed_phase_id: null,
      target_earliest_date: '2027-03-10', timing: { ...plan.milestones[0].timing!, status: 'no_work_linked', summary: 'No work linked yet', governed_task_ids: [], actionable_task_ids: [], missing_duration_task_ids: [] },
    }
    render(<MilestoneDecisionFoundation plan={plan} onPlanUpdated={vi.fn()} />)
    expect(screen.getByText('Target: Mar 10 – Mar 12, 2027')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'View timing' })).not.toBeInTheDocument()
    expect(document.getElementById('milestone-timing-move')).not.toBeInTheDocument()
  })

  it('shows No work linked yet without a disclosure for a fixed date without a selected phase', () => {
    const plan = structuredClone(fixedPlan)
    plan.milestones[0] = {
      ...plan.milestones[0], governed_phase_id: null,
      timing: { ...plan.milestones[0].timing!, status: 'no_work_linked', summary: 'No work linked yet', governed_task_ids: [], actionable_task_ids: [], missing_duration_task_ids: [] },
    }
    render(<MilestoneDecisionFoundation plan={plan} onPlanUpdated={vi.fn()} />)
    expect(screen.getByText('No work linked yet')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'View timing' })).not.toBeInTheDocument()
    expect(document.getElementById('milestone-timing-move')).not.toBeInTheDocument()
  })

  it('renders calculated content for a complete fixed-date timing analysis', () => {
    const plan = structuredClone(fixedPlan)
    plan.milestones[0].timing = {
      ...plan.milestones[0].timing!, status: 'at_risk', summary: 'This phase needs attention now.',
      critical_path_task_ids: ['pack'], actionable_task_ids: ['pack'], missing_duration_task_ids: [],
      duration_min_days: 2, duration_max_days: 4, conservative_latest_start: '2027-03-08', last_plausible_start: '2027-03-10',
    }
    render(<MilestoneDecisionFoundation plan={plan} onPlanUpdated={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'View timing' }))
    expect(screen.getByText(/2–4 elapsed days/)).toBeVisible()
    expect(screen.getByText('Safe start:')).toBeVisible()
    expect(screen.getByText('Last plausible start:')).toBeVisible()
    expect(screen.getByText('Current actionable work')).toBeVisible()
  })

  it('removes expanded timing and stale session state when phase or fixed-date eligibility is cleared', async () => {
    const { rerender } = render(<MilestoneDecisionFoundation plan={fixedPlan} onPlanUpdated={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'View timing' }))
    expect(document.getElementById('milestone-timing-move')).toBeVisible()

    const noPhase = structuredClone(fixedPlan)
    noPhase.milestones[0] = { ...noPhase.milestones[0], governed_phase_id: null, timing: { ...noPhase.milestones[0].timing!, status: 'no_work_linked', summary: 'No work linked yet' } }
    rerender(<MilestoneDecisionFoundation plan={noPhase} onPlanUpdated={vi.fn()} />)
    expect(screen.queryByRole('button', { name: 'View timing' })).not.toBeInTheDocument()
    expect(document.getElementById('milestone-timing-move')).not.toBeInTheDocument()
    await waitFor(() => expect(JSON.parse(sessionStorage.getItem('gotime:milestone-timing:family-relocation-plan:v1') ?? '[]')).not.toContain('move'))

    const targetWindow = structuredClone(fixedPlan)
    targetWindow.milestones[0] = { ...targetWindow.milestones[0], timing_mode: 'target_window', governed_phase_id: null, timing: { ...targetWindow.milestones[0].timing!, status: 'no_work_linked', summary: 'No work linked yet' } }
    rerender(<MilestoneDecisionFoundation plan={targetWindow} onPlanUpdated={vi.fn()} />)
    expect(screen.queryByRole('button', { name: 'View timing' })).not.toBeInTheDocument()
    expect(document.getElementById('milestone-timing-move')).not.toBeInTheDocument()
  })

  it('keeps multiple actionable Tasks plural and pairs long titles with independent responsive estimate actions', () => {
    const plan = structuredClone(fixedPlan)
    const longTitle = 'Stop Tennessee utilities: gas, electric, water, internet, garbage/recycling/compost, etc'
    plan.tasks.push({ ...plan.tasks[0], id: 'utilities', title: longTitle })
    plan.milestones[0].timing = {
      ...plan.milestones[0].timing!, actionable_task_ids: ['pack', 'utilities'],
      governed_task_ids: ['pack', 'utilities'], missing_duration_task_ids: ['pack', 'utilities'],
    }
    render(<MilestoneDecisionFoundation plan={plan} onPlanUpdated={vi.fn()} onTaskEstimateRequested={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'View timing' }))
    expect(screen.getByText('Current actionable work')).toBeVisible()
    const list = screen.getByRole('list')
    const items = within(list).getAllByRole('listitem')
    expect(items).toHaveLength(2)
    expect(items[1]).toHaveTextContent(longTitle)
    expect(within(items[1]).getByRole('button', { name: `Add time estimate for ${longTitle}` })).toHaveTextContent('Estimate time')
    expect(items[0]).toHaveClass('milestone-missing-estimate-item')
    expect(within(items[0]).getByRole('button')).toHaveClass('milestone-estimate-action')
  })

  it('opens elapsed-time editing directly and returns Cancel to the same estimate action without changing filters', async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(fixedPlan))
      return Promise.resolve(response(fixedPlan))
    })
    vi.stubGlobal('fetch', fetchMock)
    sessionStorage.setItem('gotime:plan:family-relocation-plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: [], expandedCompletedPhaseIds: [] }))
    sessionStorage.setItem('gotime:plan:family-relocation-plan:filters', JSON.stringify({ version: 1, categories: ['housing'] }))
    render(<RelocationPlan />)
    fireEvent.click(await screen.findByRole('button', { name: 'View timing' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add time estimate for Pack' }))
    expect(await screen.findByRole('heading', { name: 'Edit task' })).toBeVisible()
    await waitFor(() => expect(screen.getByLabelText('From')).toHaveFocus())
    expect(screen.getByLabelText('Do not recommend before')).not.toHaveFocus()
    expect(screen.getByLabelText('Due by')).not.toHaveFocus()
    fireEvent.change(screen.getByLabelText('From'), { target: { value: '4' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    const returned = await screen.findByRole('button', { name: 'Add time estimate for Pack' })
    await waitFor(() => expect(returned).toHaveFocus())
    expect(screen.getByRole('button', { name: 'Filter by categories' })).toHaveTextContent('Categories (1)')
  })

  it('prepares hidden completed subtask, parent, and phase reveal state without clearing the category filter', async () => {
    const plan = structuredClone(fixedPlan)
    const parent: RelocationTask = { ...plan.tasks[0], id: 'parent', title: 'Parent', categories: ['housing'], is_parent: true, subtask_count: 1, completed_subtask_count: 1 }
    const child: RelocationTask = { ...plan.tasks[0], id: 'child', title: 'Hidden completed child', categories: ['housing'], status: 'completed', parent_task_id: 'parent', subtask_position: 0 }
    plan.tasks = [parent, child]
    plan.milestones[0].timing = { ...plan.milestones[0].timing!, governed_task_ids: ['parent', 'child'], actionable_task_ids: [], missing_duration_task_ids: ['child'] }
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response(plan))))
    sessionStorage.setItem('gotime:plan:family-relocation-plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: [], expandedCompletedPhaseIds: [] }))
    sessionStorage.setItem('gotime:plan:family-relocation-plan:filters', JSON.stringify({ version: 1, categories: ['financial'] }))
    render(<RelocationPlan />)
    fireEvent.click(await screen.findByRole('button', { name: 'View timing' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add time estimate for Hidden completed child' }))
    await waitFor(() => expect(screen.getByLabelText('From')).toHaveFocus())
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add time estimate for Hidden completed child' })).toHaveFocus())
    expect(JSON.parse(sessionStorage.getItem('gotime:plan:family-relocation-plan:expansion') ?? '{}')).toEqual(expect.objectContaining({ expandedCompletedPhaseIds: ['prepare'] }))
    expect(JSON.parse(sessionStorage.getItem('gotime:plan:family-relocation-plan:subtasks') ?? '[]')).toContain('parent')
    expect(screen.getByRole('button', { name: 'Filter by categories' })).toHaveTextContent('Categories (1)')
  })

  it('returns a successful estimate save to the next missing Task and keeps failures in the editor', async () => {
    const nextPlan = structuredClone(fixedPlan)
    nextPlan.tasks.push({ ...nextPlan.tasks[0], id: 'utilities', title: 'Stop Tennessee utilities' })
    nextPlan.milestones[0].timing = {
      ...nextPlan.milestones[0].timing!, governed_task_ids: ['pack', 'utilities'], actionable_task_ids: ['pack', 'utilities'], missing_duration_task_ids: ['pack', 'utilities'],
    }
    const savedPlan = structuredClone(nextPlan)
    savedPlan.tasks[0].expected_elapsed_min_days = 2
    savedPlan.tasks[0].expected_elapsed_max_days = 3
    savedPlan.milestones[0].timing = { ...savedPlan.milestones[0].timing!, missing_duration_task_ids: ['utilities'] }
    let fail = false
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(nextPlan))
      if (fail) return Promise.resolve({ ok: false, status: 500, json: async () => ({ detail: 'Save failed.' }) } as Response)
      return Promise.resolve(response(savedPlan))
    })
    vi.stubGlobal('fetch', fetchMock)
    sessionStorage.setItem('gotime:plan:family-relocation-plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [] }))
    render(<RelocationPlan />)
    fireEvent.click(await screen.findByRole('button', { name: 'View timing' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add time estimate for Pack' }))
    fireEvent.change(await screen.findByLabelText('From'), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText('to'), { target: { value: '3' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    const next = await screen.findByRole('button', { name: 'Add time estimate for Stop Tennessee utilities' })
    await waitFor(() => expect(next).toHaveFocus())
    expect(screen.queryByRole('button', { name: 'Add time estimate for Pack' })).not.toBeInTheDocument()

    fireEvent.click(next)
    fail = true
    fireEvent.change(await screen.findByLabelText('From'), { target: { value: '5' } })
    fireEvent.change(screen.getByLabelText('to'), { target: { value: '6' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    expect(await screen.findByText('Save failed.')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Edit task' })).toBeVisible()
    expect(screen.getByLabelText('From')).toHaveValue(5)
  })

  it('returns a final successful estimate to the expanded timing summary', async () => {
    const savedPlan = structuredClone(fixedPlan)
    savedPlan.tasks[0].expected_elapsed_min_days = 1
    savedPlan.tasks[0].expected_elapsed_max_days = 1
    savedPlan.milestones[0].timing = {
      ...savedPlan.milestones[0].timing!, status: 'time_to_begin', summary: 'Starting now keeps this Milestone on track.',
      missing_duration_task_ids: [], duration_min_days: 1, duration_max_days: 1,
      conservative_latest_start: '2027-03-11', last_plausible_start: '2027-03-11', critical_path_task_ids: ['pack'],
    }
    const fetchMock = vi.fn((path: string, init?: RequestInit) => Promise.resolve(response(path === '/api/relocation-plan' && !init?.method ? fixedPlan : savedPlan)))
    vi.stubGlobal('fetch', fetchMock)
    sessionStorage.setItem('gotime:plan:family-relocation-plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [] }))
    render(<RelocationPlan />)
    fireEvent.click(await screen.findByRole('button', { name: 'View timing' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add time estimate for Pack' }))
    fireEvent.change(await screen.findByLabelText('From'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('to'), { target: { value: '1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(document.querySelector('[data-milestone-timing-summary="move"]')).toHaveFocus())
    expect(screen.getByRole('button', { name: 'View timing' })).toHaveAttribute('aria-expanded', 'true')
  })

  it('enters, normalizes, clears, and sets Same day elapsed ranges', async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(fixedPlan))
      return Promise.resolve(response(fixedPlan))
    })
    vi.stubGlobal('fetch', fetchMock)
    sessionStorage.setItem('gotime:plan:family-relocation-plan:expansion', JSON.stringify({ version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [] }))
    render(<RelocationPlan />)
    const packCard = await screen.findByRole('article', { name: 'Pack' })
    fireEvent.click(packCard.querySelector('[data-task-edit-control="true"]') as HTMLButtonElement)
    expect(screen.getByRole('group', { name: 'Expected elapsed time (optional)' })).toBeVisible()
    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText('to'), { target: { value: '3' } })
    fireEvent.change(screen.getByLabelText('Unit'), { target: { value: 'weeks' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      '/api/relocation-plan/tasks/pack',
      expect.objectContaining({ body: expect.stringContaining('"expected_elapsed_min_days":14') }),
    ))
  })
})
