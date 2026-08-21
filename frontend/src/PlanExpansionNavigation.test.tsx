import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'
import App from './App'
import type { RelocationPlan } from './api/relocationPlan'

const plan: RelocationPlan = {
  id: 'navigation-plan',
  title: 'Move our family',
  phases: [
    { id: 'prepare', title: 'Prepare', position: 10 },
    { id: 'move', title: 'Move', position: 20 },
  ],
  tasks: [{
    id: 'pack', title: 'Pack', description: null, phase_id: 'prepare', categories: [],
    status: 'not_started', assignees: [], start_date: null, due_date: null,
    priority: 'medium', dependency_task_ids: [], blocked: false,
  }],
  milestones: [],
  decisions: [],
}

function response(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body } as Response
}

afterEach(() => {
  sessionStorage.clear()
  vi.unstubAllGlobals()
})

describe('Plan expansion across routes', () => {
  it('preserves expansion across Plan to Now to Plan navigation', async () => {
    vi.stubGlobal('fetch', vi.fn((path: string) => Promise.resolve(response(
      path === '/api/relocation-plan' ? plan : {
        task_id: 'pack', task_title: 'Pack', phase_id: 'prepare', phase_title: 'Prepare', why: ['Actionable'],
      },
    ))))
    render(<MemoryRouter initialEntries={['/plan']}><App /></MemoryRouter>)

    const prepare = await screen.findByRole('button', { name: /Prepare 1 remaining · 0 completed/ })
    fireEvent.click(prepare)
    expect(screen.getByRole('article', { name: 'Pack' })).toBeVisible()
    fireEvent.click(screen.getByRole('link', { name: 'Now' }))
    expect(await screen.findByText('What should I do next?')).toBeVisible()
    fireEvent.click(screen.getByRole('link', { name: 'Plan' }))

    expect(await screen.findByRole('button', { name: /Prepare 1 remaining · 0 completed/ })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('article', { name: 'Pack' })).toBeVisible()
  })
})
