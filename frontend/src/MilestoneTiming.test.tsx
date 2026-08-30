import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MilestoneDecisionFoundation } from './MilestoneDecisionFoundation'
import { RelocationPlan } from './RelocationPlan'
import type { RelocationPlan as Plan } from './api/relocationPlan'


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
  it('edits a fixed date and one governed phase with the future-work explanation', () => {
    render(<MilestoneDecisionFoundation plan={fixedPlan} onPlanUpdated={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /Move out/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }))
    expect(screen.getByRole('radio', { name: 'Fixed date' })).toBeChecked()
    expect(document.getElementById('milestone-fixed-date')).toHaveValue('2027-03-12')
    expect(screen.getByLabelText('Work to finish before this date')).toHaveValue('prepare')
    expect(screen.getByText(/including work added later/)).toBeVisible()
  })

  it('distinguishes Timing incomplete, expands details accessibly, and targets Add estimate', () => {
    const target = vi.fn()
    render(<MilestoneDecisionFoundation plan={fixedPlan} onPlanUpdated={vi.fn()} onTaskTargeted={target} />)
    expect(screen.getByText('Fixed date: Mar 12, 2027')).toBeVisible()
    expect(screen.getByText('Timing incomplete', { selector: '.badge' })).toBeVisible()
    const view = screen.getByRole('button', { name: 'View timing' })
    expect(view).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(view)
    expect(view).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Governed phase:')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Add estimate' }))
    expect(target).toHaveBeenCalledWith(expect.objectContaining({ id: 'pack' }))
    expect(JSON.parse(sessionStorage.getItem('gotime:milestone-timing:family-relocation-plan:v1') ?? '[]')).toContain('move')
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
