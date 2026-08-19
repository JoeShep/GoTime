import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RelocationPlanExperience } from './RelocationPlanExperience'
import type {
  RelocationPlan,
  RelocationTaskRecommendation,
} from './api/relocationPlan'

const phases = [
  { id: 'decide', title: 'Decide where and how to move', position: 10 },
  { id: 'prepare', title: 'Prepare for the move', position: 20 },
  { id: 'move', title: 'Make the move', position: 30 },
  { id: 'settle', title: 'Settle in', position: 40 },
]

const initialPlan: RelocationPlan = {
  id: 'family-relocation-plan',
  title: 'Relocate the family to Northern California',
  phases,
  milestones: [],
  decisions: [],
  tasks: [
    {
      id: 'choose-mover',
      title: 'Choose a mover',
      description: null,
      phase_id: 'prepare',
      categories: ['logistics'],
      status: 'not_started',
      assignees: ['Joe'],
      start_date: null,
      due_date: '2026-08-15',
      priority: 'high',
      dependency_task_ids: [],
      blocked: false,
    },
    {
      id: 'pay-deposit',
      title: 'Pay the mover deposit',
      description: null,
      phase_id: 'prepare',
      categories: ['financial'],
      status: 'not_started',
      assignees: ['Sarah'],
      start_date: null,
      due_date: null,
      priority: 'medium',
      dependency_task_ids: ['choose-mover'],
      blocked: true,
    },
  ],
}

const completedPlan: RelocationPlan = {
  ...initialPlan,
  tasks: initialPlan.tasks.map((task) =>
    task.id === 'choose-mover'
      ? { ...task, status: 'completed' }
      : { ...task, blocked: false },
  ),
}

function recommendation(
  taskId: string,
  title: string,
): RelocationTaskRecommendation {
  return {
    status: 'recommended',
    task_id: taskId,
    task_title: title,
    phase_id: 'prepare',
    phase_title: 'Prepare for the move',
    why: ['Its user priority is high.'],
    why_now: 'It is available to work on now and has no incomplete prerequisites.',
    directly_unblocks_task_ids: [],
    ranking_factors: {
      due_state: 'no_due_date',
      due_date: null,
      priority: 'high',
      task_status: 'not_started',
      directly_unblocks_count: 0,
      phase_position: 20,
    },
  }
}

function response(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body } as Response
}

afterEach(() => vi.unstubAllGlobals())

describe('relocation-plan recommendation experience', () => {
  it('displays the returned stored-task recommendation and explanation', async () => {
    vi.stubGlobal('fetch', vi.fn((path: string) => {
      if (path === '/api/relocation-plan/recommendation') {
        return Promise.resolve(response(recommendation('choose-mover', 'Choose a mover')))
      }
      return Promise.resolve(response(initialPlan))
    }))

    const { container } = render(<RelocationPlanExperience />)

    expect(await screen.findByText('Primary recommendation')).toBeVisible()
    expect(container.querySelector('.primary-recommendation')).toHaveClass('mx-2', 'mx-sm-0')
    expect(screen.getAllByRole('heading', { name: 'Choose a mover' })).toHaveLength(2)
    expect(screen.getByText('Its user priority is high.')).toBeVisible()
    expect(screen.getByText(/Why now:/).closest('p')).toHaveTextContent(
      'It is available to work on now',
    )
  })

  it('changes the recommendation after completing the recommended task', async () => {
    let completed = false
    vi.stubGlobal('fetch', vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan/recommendation') {
        return Promise.resolve(
          response(
            completed
              ? recommendation('pay-deposit', 'Pay the mover deposit')
              : recommendation('choose-mover', 'Choose a mover'),
          ),
        )
      }
      if (path.endsWith('/status') && init?.method === 'PATCH') {
        completed = true
        return Promise.resolve(response(completedPlan))
      }
      return Promise.resolve(response(completed ? completedPlan : initialPlan))
    }))

    render(<RelocationPlanExperience />)
    await screen.findByText('Its user priority is high.')
    expect(screen.getAllByRole('heading', { name: 'Choose a mover' })).toHaveLength(2)

    fireEvent.change(screen.getByLabelText('Status for Choose a mover'), {
      target: { value: 'completed' },
    })

    await waitFor(() => {
      expect(
        screen.getAllByRole('heading', { name: 'Pay the mover deposit' }),
      ).toHaveLength(2)
    })
    fireEvent.click(screen.getByRole('button', { name: 'Completed (1)' }))
    expect(screen.getByLabelText('Status for Choose a mover')).toHaveValue('completed')
  })

  it('does not refresh the task recommendation for Milestone-only changes', async () => {
    const planWithMilestone: RelocationPlan = {
      ...initialPlan,
      milestones: [{
        id: 'start-selling-home',
        title: 'Start selling our home',
        description: null,
        target_earliest_date: '2027-01-01',
        target_latest_date: null,
        status: 'pending',
        achieved_at: null,
      }],
    }
    const achievedPlan: RelocationPlan = {
      ...planWithMilestone,
      milestones: [{
        ...planWithMilestone.milestones[0],
        status: 'achieved',
        achieved_at: '2026-08-19T03:00:00Z',
      }],
    }
    let recommendationRequests = 0
    vi.stubGlobal('fetch', vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan/recommendation') {
        recommendationRequests += 1
        return Promise.resolve(response(recommendation('choose-mover', 'Choose a mover')))
      }
      if (path.endsWith('/achievement') && init?.method === 'PATCH') {
        return Promise.resolve(response(achievedPlan))
      }
      return Promise.resolve(response(planWithMilestone))
    }))

    render(<RelocationPlanExperience />)
    await screen.findByRole('button', { name: 'Mark achieved' })
    expect(recommendationRequests).toBe(1)
    fireEvent.click(screen.getByRole('button', { name: 'Mark achieved' }))

    expect(screen.getByRole('heading', { name: 'Start selling our home' })).toBeVisible()
    await screen.findByRole('button', { name: 'Return to pending' })
    expect(recommendationRequests).toBe(1)
    expect(screen.queryByText('Loading next task…')).not.toBeInTheDocument()
  })

  it('does not let an obsolete recommendation overwrite the latest plan revision', async () => {
    let resolveObsolete: ((value: Response) => void) | undefined
    const obsoleteRequest = new Promise<Response>((resolve) => {
      resolveObsolete = resolve
    })
    let recommendationRequests = 0
    let completed = false
    vi.stubGlobal('fetch', vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan/recommendation') {
        recommendationRequests += 1
        if (recommendationRequests === 1) return obsoleteRequest
        return Promise.resolve(
          response(recommendation('pay-deposit', 'Pay the mover deposit')),
        )
      }
      if (path.endsWith('/status') && init?.method === 'PATCH') {
        completed = true
        return Promise.resolve(response(completedPlan))
      }
      return Promise.resolve(response(completed ? completedPlan : initialPlan))
    }))

    render(<RelocationPlanExperience />)
    await screen.findByRole('heading', { name: 'Choose a mover' })
    fireEvent.change(screen.getByLabelText('Status for Choose a mover'), {
      target: { value: 'completed' },
    })

    await waitFor(() => {
      expect(
        screen.getAllByRole('heading', { name: 'Pay the mover deposit' }),
      ).toHaveLength(2)
    })

    await act(async () => {
      resolveObsolete?.(
        response(recommendation('choose-mover', 'Choose a mover')),
      )
      await obsoleteRequest
    })

    expect(
      screen.getAllByRole('heading', { name: 'Pay the mover deposit' }),
    ).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'Completed (1)' }))
    expect(
      screen.getAllByRole('heading', { name: 'Choose a mover' }),
    ).toHaveLength(1)
  })
})
