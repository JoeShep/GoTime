import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, useLocation } from 'react-router'
import App from './App'
import { NextTaskRecommendation } from './NextTaskRecommendation'
import { RelocationPlanExperience } from './RelocationPlanExperience'
import type { RecommendationItem, RelocationPlan, RelocationTask, RelocationTaskRecommendation } from './api/relocationPlan'


const taskItem = (overrides: Partial<RecommendationItem> = {}): RecommendationItem => ({
  candidate_type: 'task', task_id: 'research', task_title: 'Research neighborhoods',
  decision_id: null, decision_title: null, phase_id: 'prepare', phase_title: 'Prepare',
  why: ['Its user priority is medium.'], why_now: 'It advances preparation for an unresolved decision.',
  directly_unblocks_task_ids: [], signals: [{
    kind: 'direct_decision_preparation', decision_id: 'choose-area', decision_title: 'Choose an area',
    preparation_task_id: 'research', preparation_task_title: 'Research neighborhoods',
    parent_task_id: null, parent_task_title: null, blocked_task_id: null, blocked_task_title: null,
    dependency_path_task_ids: ['research'],
  }],
  task_metadata: { status: 'not_started', assignees: ['Joe'], categories: ['housing'], start_date: null, due_date: '2026-09-01', priority: 'medium' },
  ranking_factors: null, ...overrides,
})

const decisionItem = (overrides: Partial<RecommendationItem> = {}): RecommendationItem => ({
  candidate_type: 'decision', task_id: null, task_title: null, decision_id: 'choose-area',
  decision_title: 'Choose an area', phase_id: null, phase_title: null,
  why: ['All currently tracked preparation work is complete.'],
  why_now: 'This unresolved decision is ready for your review.', directly_unblocks_task_ids: [],
  signals: [{ kind: 'ready_to_decide', decision_id: 'choose-area', decision_title: 'Choose an area', preparation_task_id: null, preparation_task_title: null, parent_task_id: null, parent_task_title: null, blocked_task_id: null, blocked_task_title: null, dependency_path_task_ids: [] }],
  task_metadata: null, ranking_factors: null, ...overrides,
})

const response = (body: unknown): Response => ({ ok: true, status: 200, json: async () => body }) as Response

function recommendation(primary: RecommendationItem, upcoming: RecommendationItem[] = []): RelocationTaskRecommendation {
  return { status: 'recommended', ...primary, upcoming }
}

afterEach(() => {
  sessionStorage.clear()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView
})

describe('contextual Recommendations', () => {
  it('renders Task and Decision candidates consistently in primary and upcoming positions', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(recommendation(taskItem(), [decisionItem()]))))
    render(<NextTaskRecommendation refreshKey={0} />)

    expect(await screen.findByText('Primary recommendation')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Research neighborhoods' })).toBeVisible()
    expect(screen.getByText('Not started · Medium priority · Joe · Housing · Due 2026-09-01')).toBeVisible()
    expect(screen.getByText('Helps prepare:').closest('p')).toHaveTextContent('Choose an area')
    expect(screen.getByLabelText('Upcoming recommendations')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Make a decision' })).toBeVisible()
    expect(screen.getByText('All currently tracked preparation work is complete.')).toBeVisible()
  })

  it('explains inherited and dependency contexts and discloses every Decision accessibly', async () => {
    const inherited = taskItem({ signals: [{ ...taskItem().signals![0], kind: 'inherited_decision_preparation', parent_task_id: 'compare', parent_task_title: 'Compare areas' }] })
    const dependency = taskItem({ task_id: 'collect', task_title: 'Collect school data', signals: [{ ...taskItem().signals![0], kind: 'unblocks_decision_preparation', blocked_task_id: 'compare-costs', blocked_task_title: 'Compare costs' }] })
    const multiple = taskItem({ task_id: 'shared', task_title: 'Shared research', signals: [taskItem().signals![0], { ...taskItem().signals![0], decision_id: 'choose-school', decision_title: 'Choose a school' }] })
    const requests = [recommendation(inherited), recommendation(dependency), recommendation(multiple)]
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => Promise.resolve(response(requests.shift()))))

    const view = render(<NextTaskRecommendation refreshKey={0} />)
    expect((await screen.findByText('Part of:')).closest('div')).toHaveTextContent('Compare areas')
    expect(screen.getByText('Helps prepare:').closest('div')).toHaveTextContent('Choose an area')
    view.rerender(<NextTaskRecommendation refreshKey={1} />)
    expect((await screen.findByText(/Unblocks Compare costs/)).closest('p')).toHaveTextContent('which helps prepare Choose an area')
    view.rerender(<NextTaskRecommendation refreshKey={2} />)
    const disclosure = await screen.findByText('Helps prepare 2 decisions')
    fireEvent.click(disclosure)
    expect(screen.getByText('Choose an area')).toBeVisible()
    expect(screen.getByText('Choose a school')).toBeVisible()
  })

  it('renders a ready Decision as primary and a Task as upcoming', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(recommendation(decisionItem(), [taskItem()]))))
    render(<NextTaskRecommendation refreshKey={0} />)
    expect(await screen.findByText('Primary recommendation')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Make a decision' })).toBeVisible()
    expect(screen.getByLabelText('Upcoming recommendations')).toHaveTextContent('Research neighborhoods')
  })

  it('rerenders Task to ready Decision to ordinary work after recalculation', async () => {
    const ordinary = taskItem({ task_id: 'pack', task_title: 'Pack boxes', signals: [], why_now: 'It is available to work on now.' })
    const requests = [recommendation(taskItem()), recommendation(decisionItem()), recommendation(ordinary)]
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => Promise.resolve(response(requests.shift()))))
    const view = render(<NextTaskRecommendation refreshKey={0} />)

    expect(await screen.findByRole('heading', { name: 'Research neighborhoods' })).toBeVisible()
    view.rerender(<NextTaskRecommendation refreshKey={1} />)
    expect(await screen.findByRole('heading', { name: 'Make a decision' })).toBeVisible()
    view.rerender(<NextTaskRecommendation refreshKey={2} />)
    expect(await screen.findByRole('heading', { name: 'Pack boxes' })).toBeVisible()
    expect(screen.queryByText('Choose an area')).not.toBeInTheDocument()
  })

  it('recalculates immediately from preparation Task to Decision to next Task after mutations', async () => {
    const preparationTask: RelocationTask = { id: 'research', title: 'Research neighborhoods', description: null, phase_id: 'prepare', categories: ['housing'], status: 'not_started', assignees: [], start_date: null, due_date: null, priority: 'medium', dependency_task_ids: [], blocked: false }
    const ordinaryTask: RelocationTask = { ...preparationTask, id: 'pack', title: 'Pack boxes', categories: ['logistics'] }
    const milestone = { id: 'move', title: 'Move', description: null, target_earliest_date: null, target_latest_date: null, status: 'pending' as const, achieved_at: null }
    const unresolved = { id: 'choose-area', title: 'Choose an area', description: null, milestone_id: 'move', options: [{ id: 'a', title: 'A', description: null }, { id: 'b', title: 'B', description: null }], status: 'unresolved' as const, selected_option_id: null, preparation_task_ids: ['research'], preparation_readiness: 'preparation_incomplete' as const, completed_preparation_task_count: 0 }
    const initial: RelocationPlan = { id: 'plan', title: 'Move', phases: [{ id: 'prepare', title: 'Prepare', position: 10 }], tasks: [preparationTask, ordinaryTask], milestones: [milestone], decisions: [unresolved] }
    const ready: RelocationPlan = { ...initial, tasks: [{ ...preparationTask, status: 'completed' }, ordinaryTask], decisions: [{ ...unresolved, preparation_readiness: 'ready_to_decide', completed_preparation_task_count: 1 }] }
    const resolved: RelocationPlan = { ...ready, decisions: [{ ...ready.decisions[0], status: 'resolved', selected_option_id: 'a' }] }
    let stage = 0
    vi.stubGlobal('fetch', vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan/recommendation') {
        return Promise.resolve(response(stage === 0 ? recommendation(taskItem()) : stage === 1 ? recommendation(decisionItem()) : recommendation(taskItem({ task_id: 'pack', task_title: 'Pack boxes', signals: [] }))))
      }
      if (path.endsWith('/status') && init?.method === 'PATCH') { stage = 1; return Promise.resolve(response(ready)) }
      if (path.endsWith('/selection') && init?.method === 'PATCH') { stage = 2; return Promise.resolve(response(resolved)) }
      return Promise.resolve(response(stage === 0 ? initial : stage === 1 ? ready : resolved))
    }))
    render(<RelocationPlanExperience />)

    await screen.findByText('Helps prepare:')
    fireEvent.click(screen.getByRole('button', { name: /Prepare 2 remaining/ }))
    fireEvent.change(screen.getByLabelText('Status for Research neighborhoods'), { target: { value: 'completed' } })
    expect(await screen.findByRole('heading', { name: 'Make a decision' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Move' }))
    fireEvent.click(screen.getByRole('button', { name: /Choose an area/ }))
    fireEvent.change(screen.getByLabelText('Selection for Choose an area'), { target: { value: 'a' } })
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Make a decision' })).not.toBeInTheDocument())
    expect(screen.getAllByRole('heading', { name: 'Pack boxes' })).toHaveLength(2)
  })

  it('Review decision reveals, focuses, and highlights the existing Decision card', async () => {
    const plan: RelocationPlan = {
      id: 'plan', title: 'Move', phases: [{ id: 'prepare', title: 'Prepare', position: 10 }], tasks: [],
      milestones: [{ id: 'move', title: 'Move', description: null, target_earliest_date: null, target_latest_date: null, status: 'pending', achieved_at: null }],
      decisions: [{ id: 'choose-area', title: 'Choose an area', description: null, milestone_id: 'move', options: [{ id: 'a', title: 'A', description: null }, { id: 'b', title: 'B', description: null }], status: 'unresolved', selected_option_id: null, preparation_task_ids: [], preparation_readiness: 'ready_to_decide', completed_preparation_task_count: 0 }],
    }
    vi.stubGlobal('fetch', vi.fn((path: string) => Promise.resolve(response(path === '/api/relocation-plan/recommendation' ? recommendation(decisionItem()) : plan))))
    Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
    const Location = () => <output data-testid="location">{useLocation().pathname}</output>
    render(<MemoryRouter initialEntries={['/now']}><App /><Location /></MemoryRouter>)

    fireEvent.click(await screen.findByRole('button', { name: 'Review decision' }))
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/plan'))
    const card = await screen.findByRole('article', { name: 'Choose an area' })
    await waitFor(() => expect(card).toHaveFocus())
    expect(card).toHaveClass('is-found')
    expect(screen.getByRole('button', { name: /Choose an area/ })).toHaveAttribute('aria-expanded', 'true')
  })
})
