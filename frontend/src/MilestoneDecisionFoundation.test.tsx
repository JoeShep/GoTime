import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MilestoneDecisionFoundation } from './MilestoneDecisionFoundation'
import type { RelocationPlan } from './api/relocationPlan'

const plan: RelocationPlan = {
  id: 'family-relocation-plan', title: 'Family plan', phases: [], tasks: [], decisions: [],
  milestones: [{
    id: 'start-selling-home', title: 'Start selling our home', description: null,
    target_earliest_date: '2027-01-02', target_latest_date: null,
    status: 'pending', achieved_at: null,
  }],
}

const withDecision: RelocationPlan = {
  ...plan,
  decisions: [{
    id: 'sale-strategy', title: 'Select the initial home-sale strategy',
    description: null, milestone_id: 'start-selling-home', status: 'unresolved',
    selected_option_id: null,
    options: [
      { id: 'as-is', title: 'Public listing as-is', description: null },
      { id: 'builder', title: 'Builder outreach', description: null },
    ],
  }],
}

function response(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body } as Response
}

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('Milestone and Decision foundation', () => {
  it('explains an open-ended target and changes achievement explicitly', async () => {
    const fetchMock = vi.fn(() => Promise.resolve(response({
      ...plan, milestones: [{ ...plan.milestones[0], status: 'achieved', achieved_at: '2026-08-19T00:00:00Z' }],
    })))
    vi.stubGlobal('fetch', fetchMock)
    const updated = vi.fn()
    render(<MilestoneDecisionFoundation plan={plan} onPlanUpdated={updated} />)

    expect(screen.getByText('Target: on or after 2027-01-02')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Mark achieved' }))
    await waitFor(() => expect(updated).toHaveBeenCalled())
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/relocation-plan/milestones/start-selling-home/achievement',
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ achieved: true }) }),
    )
  })

  it('keeps option order and selection under user control', async () => {
    const fetchMock = vi.fn(() => Promise.resolve(response({
      ...withDecision,
      decisions: [{ ...withDecision.decisions[0], status: 'resolved', selected_option_id: 'builder' }],
    })))
    vi.stubGlobal('fetch', fetchMock)
    render(<MilestoneDecisionFoundation plan={withDecision} onPlanUpdated={vi.fn()} />)

    const selection = screen.getByRole('combobox', { name: 'Selection for Select the initial home-sale strategy' })
    expect(Array.from((selection as HTMLSelectElement).options).map((option) => option.text)).toEqual([
      'Unresolved', 'Public listing as-is', 'Builder outreach',
    ])
    fireEvent.change(selection, { target: { value: 'builder' } })
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      '/api/relocation-plan/decisions/sale-strategy/selection',
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ selected_option_id: 'builder' }) }),
    ))
  })

  it('labels milestone timing as guidance rather than task timing', () => {
    vi.stubGlobal('fetch', vi.fn())
    render(<MilestoneDecisionFoundation plan={plan} onPlanUpdated={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }))
    expect(screen.getByText('Planning guidance; not a task start date.')).toBeVisible()
    expect(screen.getByText('Leave blank for an open-ended “on or after” target.')).toBeVisible()
  })
})
