import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  formatMilestoneTiming,
  MilestoneDecisionFoundation,
} from './MilestoneDecisionFoundation'
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

    expect(screen.getByText('Target: on or after Jan 2, 2027')).toBeVisible()
    expect(screen.getByText('Pending')).toHaveClass('align-self-start', 'flex-shrink-0')
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

  it('formats every target-window form as date-only calendar values', () => {
    expect(formatMilestoneTiming({ target_earliest_date: null, target_latest_date: null }))
      .toBe('Target timing not set')
    expect(formatMilestoneTiming({ target_earliest_date: '2027-01-01', target_latest_date: null }))
      .toBe('Target: on or after Jan 1, 2027')
    expect(formatMilestoneTiming({ target_earliest_date: null, target_latest_date: '2027-02-28' }))
      .toBe('Target: on or before Feb 28, 2027')
    expect(formatMilestoneTiming({ target_earliest_date: '2027-01-01', target_latest_date: '2027-01-01' }))
      .toBe('Target: Jan 1, 2027')
    expect(formatMilestoneTiming({ target_earliest_date: '2027-01-01', target_latest_date: '2027-02-28' }))
      .toBe('Target: Jan 1 – Feb 28, 2027')
    expect(formatMilestoneTiming({ target_earliest_date: '2026-12-15', target_latest_date: '2027-01-10' }))
      .toBe('Target: Dec 15, 2026 – Jan 10, 2027')
  })

  it('constrains the latest picker and shows invalid ranges inline', () => {
    vi.stubGlobal('fetch', vi.fn())
    render(<MilestoneDecisionFoundation plan={plan} onPlanUpdated={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }))

    const latest = screen.getByLabelText(/Latest target date/) as HTMLInputElement
    expect(latest).toHaveAttribute('min', '2027-01-02')
    fireEvent.change(latest, { target: { value: '2027-01-01' } })
    expect(screen.getByText('Latest target must be on or after the earliest target.'))
      .toBeVisible()
    expect(screen.getByRole('button', { name: 'Save milestone' })).toBeDisabled()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(latest).toHaveValue('2027-01-01')
  })

  it('keeps unrelated cards stable during narrow mutations', async () => {
    let resolveRequest: ((value: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((resolve) => {
      resolveRequest = resolve
    })))
    render(<MilestoneDecisionFoundation plan={withDecision} onPlanUpdated={vi.fn()} />)

    const achievement = screen.getByRole('button', { name: 'Mark achieved' })
    const selection = screen.getByRole('combobox', { name: 'Selection for Select the initial home-sale strategy' })
    fireEvent.change(selection, { target: { value: 'builder' } })
    expect(selection).toBeDisabled()
    expect(achievement).not.toBeDisabled()
    expect(screen.getByRole('heading', { name: 'Start selling our home' })).toBeVisible()
    expect(screen.queryByText(/Loading/)).not.toBeInTheDocument()

    resolveRequest?.(response(withDecision))
    await waitFor(() => expect(selection).not.toBeDisabled())
  })

  it('exposes mobile typography and wrapping hooks without changing controls', () => {
    vi.stubGlobal('fetch', vi.fn())
    const { container } = render(
      <MilestoneDecisionFoundation plan={withDecision} onPlanUpdated={vi.fn()} />,
    )
    expect(container.querySelector('.plan-foundation-title')).toBeInTheDocument()
    expect(container.querySelector('.plan-foundation-heading')).toHaveClass('px-2', 'px-sm-0')
    expect(container.querySelector('.decision-title')).toBeInTheDocument()
    expect(container.querySelector('.plan-foundation-metadata')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Edit decision' }))
    expect(container.querySelector('.decision-option-row')).toHaveClass('flex-wrap', 'flex-sm-nowrap')
    expect(container.querySelector('.decision-option-input')).toBeInTheDocument()
  })
})
