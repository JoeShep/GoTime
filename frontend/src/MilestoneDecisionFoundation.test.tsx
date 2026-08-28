import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
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

const withPreparation: RelocationPlan = {
  ...withDecision,
  phases: [{ id: 'decide', title: 'Decide', position: 10 }],
  tasks: [{
    id: 'research', title: 'Research sale options', description: null, phase_id: 'decide',
    categories: ['housing'], status: 'not_started', assignees: [], start_date: null,
    due_date: null, priority: 'high', dependency_task_ids: [], blocked: false,
  }],
  decisions: [{
    ...withDecision.decisions[0], preparation_task_ids: ['research'],
    preparation_readiness: 'preparation_incomplete', completed_preparation_task_count: 0,
  }],
}

function response(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body } as Response
}

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })
beforeEach(() => sessionStorage.clear())

function expandMilestone() {
  fireEvent.click(screen.getByRole('button', { name: /Start selling our home/ }))
}

function expandDecision() {
  expandMilestone()
  fireEvent.click(screen.getByRole('button', { name: /Select the initial home-sale strategy/ }))
}

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
    expandMilestone()
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
    expandDecision()

    const selection = screen.getByRole('combobox', { name: 'Selection for Select the initial home-sale strategy' })
    expect(Array.from((selection as HTMLSelectElement).options).map((option) => option.text)).toEqual([
      'Unresolved', 'Public listing as-is', 'Builder outreach',
    ])
    fireEvent.change(selection, { target: { value: 'builder' } })
    fireEvent.click(screen.getByRole('button', { name: 'Select option anyway' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      '/api/relocation-plan/decisions/sale-strategy/selection',
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ selected_option_id: 'builder', confirm_not_ready: true }) }),
    ))
  })

  it('labels milestone timing as guidance rather than task timing', () => {
    vi.stubGlobal('fetch', vi.fn())
    render(<MilestoneDecisionFoundation plan={plan} onPlanUpdated={vi.fn()} />)
    expandMilestone()
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
    expandMilestone()
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
    expandDecision()

    const achievement = screen.getByRole('button', { name: 'Mark achieved' })
    const selection = screen.getByRole('combobox', { name: 'Selection for Select the initial home-sale strategy' })
    fireEvent.change(selection, { target: { value: 'builder' } })
    fireEvent.click(screen.getByRole('button', { name: 'Select option anyway' }))
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
    expandMilestone()
    expect(container.querySelector('.decision-title')).toBeInTheDocument()
    expect(container.querySelector('.plan-foundation-metadata')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Select the initial home-sale strategy/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Edit decision' }))
    expect(container.querySelector('.decision-option-row')).toHaveClass('flex-wrap', 'flex-sm-nowrap')
    expect(container.querySelector('.decision-option-input')).toBeInTheDocument()
  })

  it('starts Milestones and Decisions collapsed with independent accessible expansion', () => {
    render(<MilestoneDecisionFoundation plan={withDecision} onPlanUpdated={vi.fn()} />)
    const milestoneToggle = screen.getByRole('button', { name: /Start selling our home/ })
    expect(milestoneToggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByText('1 Decision · 0 resolved')).toBeVisible()
    expect(screen.queryByRole('button', { name: /Select the initial home-sale strategy/ })).not.toBeInTheDocument()
    fireEvent.click(milestoneToggle)
    const decisionToggle = screen.getByRole('button', { name: /Select the initial home-sale strategy/ })
    expect(decisionToggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByLabelText('Selection for Select the initial home-sale strategy')).not.toBeInTheDocument()
    fireEvent.click(decisionToggle)
    expect(screen.getByLabelText('Selection for Select the initial home-sale strategy')).toBeVisible()
    expect(screen.getByText('Add tasks that should be completed before making this decision.')).toBeVisible()
    expect(JSON.parse(sessionStorage.getItem('gotime:milestone-expansion:family-relocation-plan:v1') ?? '[]')).toContain('start-selling-home')
    expect(JSON.parse(sessionStorage.getItem('gotime:decision-expansion:family-relocation-plan:v1') ?? '[]')).toContain('sale-strategy')
  })

  it('uses equal-height desktop pairs, a full-row final Decision, and natural narrow-width hooks', () => {
    const layoutPlan: RelocationPlan = {
      ...withDecision,
      milestones: [
        ...withDecision.milestones,
        { ...withDecision.milestones[0], id: 'complete-move', title: 'Complete the move' },
      ],
      decisions: [
        ...withDecision.decisions,
        { ...withDecision.decisions[0], id: 'sale-timing', title: 'Choose sale timing' },
        { ...withDecision.decisions[0], id: 'sale-channel', title: 'Choose sale channel' },
        { ...withDecision.decisions[0], id: 'moving-method', title: 'Choose moving method', milestone_id: 'complete-move' },
      ],
    }
    const { container } = render(<MilestoneDecisionFoundation plan={layoutPlan} onPlanUpdated={vi.fn()} />)

    const milestoneColumns = container.querySelectorAll('.milestone-stack > .milestone-column')
    expect(milestoneColumns).toHaveLength(2)
    milestoneColumns.forEach((column) => expect(column).toHaveClass('col-12'))
    expect(milestoneColumns[0].querySelector('.plan-foundation-card')).not.toHaveClass('h-100')

    fireEvent.click(screen.getByRole('button', { name: /Start selling our home/ }))
    const firstMilestoneColumns = milestoneColumns[0].querySelectorAll('.decision-grid > .decision-column')
    expect(firstMilestoneColumns).toHaveLength(3)
    Array.from(firstMilestoneColumns).slice(0, 2).forEach((column) => {
      expect(column).toHaveClass('col-12', 'col-lg-6', 'decision-column-paired')
      expect(column.querySelector('.decision-card')).not.toHaveClass('h-100')
    })
    expect(firstMilestoneColumns[2]).toHaveClass('col-12', 'col-lg-12', 'decision-column-full')
    fireEvent.click(screen.getByRole('button', { name: /Choose sale channel/ }))
    expect(firstMilestoneColumns[2].querySelector('.decision-controls')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Complete the move/ }))
    const singleColumn = milestoneColumns[1].querySelector('.decision-grid > .decision-column')
    expect(singleColumn).toHaveClass('col-12', 'col-lg-12', 'decision-column-full')
    expect(singleColumn?.querySelector('.decision-card')).not.toHaveClass('h-100')
  })

  it('explains readiness through focus and dismisses with Escape or outside click', async () => {
    render(<MilestoneDecisionFoundation plan={withDecision} onPlanUpdated={vi.fn()} />)
    expandMilestone()
    expect(screen.getByText('No preparation tasks')).toBeVisible()
    const help = screen.getByRole('button', { name: 'About No preparation tasks' })
    fireEvent.focus(help)
    expect(screen.getByText('Preparation tasks are work you want completed before making this decision. GoTime uses their current status to estimate whether the decision is ready.')).toBeVisible()
    fireEvent.keyDown(document, { key: 'Escape' })
    await waitFor(() => expect(screen.queryByRole('tooltip')).not.toBeInTheDocument())
    expect(help).toHaveFocus()
    fireEvent.click(help)
    expect(help).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(document.body)
    await waitFor(() => expect(help).toHaveAttribute('aria-expanded', 'false'))
    expect(help).toHaveFocus()
  })

  it('uses the shared fixed-box SVG for preparation and keeps picker results query-driven', () => {
    render(<MilestoneDecisionFoundation plan={withPreparation} onPlanUpdated={vi.fn()} />)
    expandMilestone()
    const progress = screen.getByRole('button', { name: /0 of 1 preparation task completed/ })
    expect(progress).toHaveAttribute('aria-expanded', 'false')
    expect(progress.querySelector('svg.expansion-chevron')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: /Select the initial home-sale strategy/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Edit decision' }))
    expect(screen.getByLabelText('Selected preparation tasks')).toHaveTextContent('Research sale options')
    expect(screen.queryByRole('group', { name: 'Preparation task search results' })).not.toBeInTheDocument()
    const search = screen.getByRole('searchbox', { name: 'Work needed before deciding' })
    fireEvent.change(search, { target: { value: 'Research' } })
    expect(screen.getByRole('group', { name: 'Preparation task search results' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Remove Research sale options' }))
    expect(screen.queryByLabelText('Selected preparation tasks')).not.toBeInTheDocument()
  })
})
