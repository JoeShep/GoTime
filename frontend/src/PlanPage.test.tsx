import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PlanPage } from './PlanPage'

const plan = { id: 'plan', title: 'Move our family', phases: [], tasks: [], milestones: [], decisions: [] }

afterEach(() => vi.unstubAllGlobals())

describe('Plan page', () => {
  it('shows the existing plan workspace without the Now hero or experiments', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true, status: 200, json: async () => plan } as Response)))
    render(<PlanPage />)
    expect(screen.getByRole('heading', { name: 'Family plan' })).toBeVisible()
    expect(await screen.findByText('Persistent plan')).toBeVisible()
    expect(screen.queryByText('What should I do next?')).not.toBeInTheDocument()
    expect(screen.queryByText('Employment planning recommendation')).not.toBeInTheDocument()
  })
})
