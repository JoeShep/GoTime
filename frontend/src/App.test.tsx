import { StrictMode } from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { Recommendation } from './api/recommendations'

const assumption = {
  id: 'spouse-employment',
  description:
    'Suitable employment for the spouse exists within one or more viable Northern California candidate regions.',
  status: 'unconfirmed',
  related_decision_ids: ['target-location'],
  validation_method: 'Research employers, interviews, or job offers.',
}

const unclearRecommendation: Recommendation = {
  what: 'Clarify spouse employment requirements before choosing a final target location.',
  why: ['Employment requirements affect which locations are viable.'],
  why_now: 'Clarifying them makes the target-location decision more ready.',
  related_decision_id: 'target-location',
  relevant_dependencies: ['Expected employment income'],
  blocked_downstream_work: ['Neighborhood research'],
  related_assumptions: [assumption],
}

const clarifiedRecommendation: Recommendation = {
  ...unclearRecommendation,
  what: 'Evaluate candidate locations against the clarified employment requirements.',
  why: [
    'Clarified employment requirements provide criteria for comparing locations.',
    'The suitable-employment assumption remains unconfirmed.',
  ],
  why_now: 'Candidate regions can now be evaluated without choosing a final location.',
  relevant_dependencies: ['Suitable employment availability'],
}

function responseWith(recommendation: Recommendation): Response {
  return {
    ok: true,
    status: 200,
    json: async () => recommendation,
  } as Response
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('recommendation screen', () => {
  it('shows loading while the initial unclear recommendation is pending', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => undefined)))

    render(<App />)

    expect(screen.getByRole('status')).toHaveTextContent('Loading recommendation')
    expect(fetch).toHaveBeenCalledWith(
      '/api/recommendations/primary?employment_requirements=unclear',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
  })

  it('renders the unclear recommendation and its explanation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(responseWith(unclearRecommendation)))

    render(<App />)

    expect(await screen.findByRole('heading', { name: unclearRecommendation.what })).toBeVisible()
    expect(screen.getByText(unclearRecommendation.why[0])).toBeVisible()
    expect(screen.getByText(unclearRecommendation.why_now)).toBeVisible()
    expect(screen.getByText('Expected employment income')).toBeVisible()
    expect(screen.getByText('Neighborhood research')).toBeVisible()
    expect(screen.getByText(assumption.description)).toBeVisible()
    expect(screen.getByText('unconfirmed')).toBeVisible()
    expect(screen.queryByText('target-location')).not.toBeInTheDocument()
    expect(
      screen.getByText('Have you clarified what employment would need to provide?'),
    ).toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Yes, we’ve clarified the requirements' }),
    ).toBeVisible()
  })

  it('confirms the state update and renders the clarified recommendation', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(responseWith(unclearRecommendation))
      .mockResolvedValueOnce(responseWith(clarifiedRecommendation))
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await screen.findByRole('heading', { name: unclearRecommendation.what })

    fireEvent.click(
      screen.getByRole('button', { name: 'Yes, we’ve clarified the requirements' }),
    )

    expect(
      await screen.findByRole('heading', { name: clarifiedRecommendation.what }),
    ).toBeVisible()
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/recommendations/primary?employment_requirements=clarified',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    expect(screen.getByText('The suitable-employment assumption remains unconfirmed.')).toBeVisible()
    expect(screen.getByText('unconfirmed')).toBeVisible()
    expect(screen.getByText('Employment requirements marked as clarified.')).toBeVisible()
    expect(
      screen.queryByText('Have you clarified what employment would need to provide?'),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Yes, we’ve clarified the requirements' }),
    ).not.toBeInTheDocument()
  })

  it('does not let an obsolete response overwrite the clarified recommendation', async () => {
    let resolveObsolete: ((response: Response) => void) | undefined
    const obsoleteRequest = new Promise<Response>((resolve) => {
      resolveObsolete = resolve
    })
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(obsoleteRequest)
      .mockResolvedValueOnce(responseWith(unclearRecommendation))
      .mockResolvedValueOnce(responseWith(clarifiedRecommendation))
    vi.stubGlobal('fetch', fetchMock)

    render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
    await screen.findByRole('heading', { name: unclearRecommendation.what })

    fireEvent.click(
      screen.getByRole('button', { name: 'Yes, we’ve clarified the requirements' }),
    )

    expect(
      await screen.findByRole('heading', { name: clarifiedRecommendation.what }),
    ).toBeVisible()

    await act(async () => {
      resolveObsolete?.(responseWith(unclearRecommendation))
      await obsoleteRequest
    })

    expect(screen.getByRole('heading', { name: clarifiedRecommendation.what })).toBeVisible()
    expect(
      screen.queryByRole('heading', { name: unclearRecommendation.what }),
    ).not.toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert', { name: 'Recommendation unavailable' })).not.toBeInTheDocument()
  })

  it('renders an error when the clarified recommendation request fails', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(responseWith(unclearRecommendation))
      .mockResolvedValueOnce({ ok: false, status: 503 } as Response)
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await screen.findByRole('heading', { name: unclearRecommendation.what })

    fireEvent.click(
      screen.getByRole('button', { name: 'Yes, we’ve clarified the requirements' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent('Recommendation unavailable')
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Unable to load the recommendation (503).',
    )
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Yes, we’ve clarified the requirements' }),
    ).not.toBeInTheDocument()
  })
})
