import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { viewerLocalEvaluationDate } from './api/relocationPlan'
import { NextTaskRecommendation } from './NextTaskRecommendation'
import { RelocationPlan } from './RelocationPlan'

describe('Recommendation date calibration', () => {
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

  it('formats an explicit viewer-local calendar date without UTC conversion', () => {
    expect(viewerLocalEvaluationDate(new Date(2026, 7, 28, 23, 59))).toBe('2026-08-28')
  })

  it('uses accessible date language and responsive date-field columns', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({
      id: 'plan', title: 'Plan', phases: [{ id: 'prepare', title: 'Prepare', position: 1 }],
      tasks: [], milestones: [], decisions: [],
    }) }))
    render(<RelocationPlan />)
    await screen.findByText('Prepare')
    fireEvent.click(screen.getByRole('button', { name: /add/i }))
    fireEvent.click(await screen.findByRole('menuitem', { name: /task/i }))
    const hold = screen.getByLabelText('Do not recommend before (optional)')
    expect(hold).toHaveAccessibleDescription('You can still start or complete it earlier.')
    expect(hold.closest('.task-date-field')).toHaveClass('col-md-6', 'col-lg-3')
    expect(screen.getByLabelText('Due by (optional)').closest('.task-date-field')).toHaveClass('col-md-6', 'col-lg-3')
  })

  it('refetches after the viewer local calendar crosses midnight', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 7, 28, 23, 59, 59, 500))
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({
      status: 'no_actionable_task', candidate_type: null, task_id: null, task_title: null,
      phase_id: null, phase_title: null, why: ['None'], why_now: 'None',
      directly_unblocks_task_ids: [], signals: [], ranking_factors: null, upcoming: [],
    }) })
    vi.stubGlobal('fetch', fetchMock)
    render(<NextTaskRecommendation refreshKey={0} />)
    await act(async () => {})
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/relocation-plan/recommendation?evaluation_date=2026-08-28', expect.anything(),
    )
    await act(async () => { await vi.advanceTimersByTimeAsync(600) })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/relocation-plan/recommendation?evaluation_date=2026-08-29', expect.anything(),
    )
  })
})
