import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { NowPage } from './NowPage'
import { MemoryRouter } from 'react-router'

const plan = { id: 'plan', title: 'Move our family', phases: [], tasks: [], milestones: [], decisions: [] }
const recommendation = {
  status: 'recommended', task_id: 'contact', task_title: 'Contact the realtor',
  phase_id: 'prepare', phase_title: 'Prepare', why: ['It is actionable.'],
  why_now: 'It can unlock a decision.', directly_unblocks_task_ids: [], ranking_factors: null,
}

function response(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body } as Response
}

afterEach(() => vi.unstubAllGlobals())

describe('Now page', () => {
  it('shows the persisted plan title as Our goal and only the persisted recommendation', async () => {
    const fetchMock = vi.fn((path: string) => Promise.resolve(response(
      path === '/api/relocation-plan' ? plan : recommendation,
    )))
    vi.stubGlobal('fetch', fetchMock)
    render(<MemoryRouter><NowPage /></MemoryRouter>)

    expect(await screen.findByText('Move our family')).toBeVisible()
    expect(screen.getByText('Our goal')).toBeVisible()
    expect(await screen.findByRole('heading', { name: 'Contact the realtor' })).toBeVisible()
    expect(screen.queryByText('Persistent plan')).not.toBeInTheDocument()
    expect(screen.queryByText('Employment planning recommendation')).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('fetches a current recommendation whenever Now is mounted', async () => {
    const fetchMock = vi.fn((path: string) => Promise.resolve(response(
      path === '/api/relocation-plan' ? plan : recommendation,
    )))
    vi.stubGlobal('fetch', fetchMock)
    const first = render(<MemoryRouter><NowPage /></MemoryRouter>)
    await screen.findByRole('heading', { name: 'Contact the realtor' })
    first.unmount()
    render(<MemoryRouter><NowPage /></MemoryRouter>)
    await screen.findByRole('heading', { name: 'Contact the realtor' })
    expect(fetchMock.mock.calls.filter(([path]) => String(path).startsWith('/api/relocation-plan/recommendation?'))).toHaveLength(2)
  })
})
