import { StrictMode } from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { Recommendation } from './api/recommendations'

vi.mock('./RelocationPlanExperience', () => ({
  RelocationPlanExperience: () => <div data-testid="relocation-plan" />,
}))

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

const commuteLimitRecommendation: Recommendation = {
  ...unclearRecommendation,
  what: 'Define the longest workable one-way commute before evaluating candidate locations.',
  why: [
    'Hybrid work makes commute viability relevant to the location decision.',
    'The suitable-employment assumption remains unconfirmed.',
  ],
  why_now: 'The longest workable one-way commute is still unclear.',
  relevant_dependencies: ['Maximum acceptable one-way commute'],
}

const clarifiedRecommendation: Recommendation = {
  ...commuteLimitRecommendation,
  what: 'Gather a likely workplace area before collecting commute evidence.',
  why: [
    'A one-way commute longer than 45 minutes would not be acceptable to the user.',
    'The suitable-employment assumption remains unconfirmed.',
  ],
  why_now: 'Candidate research can now use the submitted commute boundary.',
  relevant_dependencies: ['Likely workplace location', 'Credible travel-time evidence'],
}

const evidenceRecommendation: Recommendation = {
  ...clarifiedRecommendation,
  what:
    'Clarify the most likely commute travel mode before gathering travel-time evidence.',
  why: [
    'San Jose is a user-provided likely workplace area, not a confirmed workplace.',
    'No route or travel time has been calculated.',
    'No candidate location currently passes or fails.',
    'The suitable-employment assumption remains unconfirmed.',
  ],
  why_now: 'The next step is to gather credible travel-time evidence.',
}

const travelModeRecommendation: Recommendation = {
  ...evidenceRecommendation,
  what:
    'Gather credible one-way public-transit travel-time evidence between candidate locations and the likely San Jose workplace area.',
  why: [
    'Public transit is user-provided planning context.',
    'Transit evidence must account for schedules, transfers, and station access.',
    'No route or travel time has been calculated.',
    'No candidate location currently passes or fails.',
    'The suitable-employment assumption remains unconfirmed.',
  ],
}

function responseWith(recommendation: Recommendation): Response {
  return {
    ok: true,
    status: 200,
    json: async () => recommendation,
  } as Response
}

function submitHybridWorkArrangement() {
  fireEvent.change(
    screen.getByLabelText(
      'What kind of work arrangement would make the move workable for your spouse?',
    ),
    { target: { value: 'hybrid' } },
  )
  fireEvent.click(screen.getByRole('button', { name: 'Use this requirement' }))
}

function submitCommuteLimit(value = '45') {
  fireEvent.change(
    screen.getByLabelText(
      'What is the longest one-way commute that would still make the move workable?',
    ),
    { target: { value } },
  )
  fireEvent.click(screen.getByRole('button', { name: 'Use this commute limit' }))
}

function submitWorkplaceArea(value = 'San Jose') {
  fireEvent.change(
    screen.getByLabelText('What area is your spouse most likely to work in?'),
    { target: { value } },
  )
  fireEvent.click(screen.getByRole('button', { name: 'Use this workplace area' }))
}

function submitTravelMode(value = 'public_transit') {
  fireEvent.change(
    screen.getByLabelText('How would your spouse most likely commute?'),
    { target: { value } },
  )
  fireEvent.click(screen.getByRole('button', { name: 'Use this travel mode' }))
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('recommendation screen', () => {
  it('uses responsive outer gutters without changing desktop padding', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => undefined)))

    const { container } = render(<App />)

    expect(container.querySelector('.app-container')).toHaveClass('py-4')
    expect(container.querySelector('.next-step-card > .card-body')).toHaveClass(
      'py-4',
      'px-0',
      'p-sm-4',
      'p-md-5',
    )
  })

  it('shows loading while the initial unclear recommendation is pending', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => undefined)))

    render(<App />)

    expect(screen.getByRole('status')).toHaveTextContent('Loading recommendation')
    expect(fetch).toHaveBeenCalledWith(
      '/api/recommendations/primary',
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
      screen.getByText(
        'What kind of work arrangement would make the move workable for your spouse?',
      ),
    ).toBeVisible()
    expect(
      screen.getByLabelText(
        'What kind of work arrangement would make the move workable for your spouse?',
      ),
    ).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Use this requirement' })).toBeDisabled()
    const primaryRecommendation = screen.getByText('Employment planning recommendation')
    const experimentHeading = screen.getByRole('heading', {
      name: 'Something else worth clarifying',
    })
    expect(
      primaryRecommendation.compareDocumentPosition(experimentHeading) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(
      screen.getByRole('button', { name: 'Get a suggested question' }),
    ).toBeVisible()
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('submits hybrid work and requests a commute boundary without submitting its draft', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(responseWith(unclearRecommendation))
      .mockResolvedValueOnce(responseWith(commuteLimitRecommendation))
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await screen.findByRole('heading', { name: unclearRecommendation.what })

    fireEvent.change(
      screen.getByLabelText(
        'What kind of work arrangement would make the move workable for your spouse?',
      ),
      { target: { value: 'hybrid' } },
    )

    expect(fetchMock).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: 'Use this requirement' }))

    expect(await screen.findByRole('heading', { name: commuteLimitRecommendation.what })).toBeVisible()
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/recommendations/primary?work_arrangement=hybrid',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    expect(screen.getByText('unconfirmed')).toBeVisible()
    expect(screen.getByText('Work arrangement recorded: Hybrid.')).toBeVisible()
    expect(
      screen.queryByText(
        'What kind of work arrangement would make the move workable for your spouse?',
      ),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Use this requirement' }),
    ).not.toBeInTheDocument()
    expect(
      screen.getByLabelText(
        'What is the longest one-way commute that would still make the move workable?',
      ),
    ).toHaveValue(null)
    expect(screen.getByText('minutes')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Use this commute limit' })).toBeDisabled()

    fireEvent.change(
      screen.getByLabelText(
        'What is the longest one-way commute that would still make the move workable?',
      ),
      { target: { value: '45' } },
    )

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(screen.getByRole('button', { name: 'Use this commute limit' })).toBeEnabled()
  })

  it('submits a valid commute limit and renders the value-aware recommendation', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(responseWith(unclearRecommendation))
      .mockResolvedValueOnce(responseWith(commuteLimitRecommendation))
      .mockResolvedValueOnce(responseWith(clarifiedRecommendation))
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await screen.findByRole('heading', { name: unclearRecommendation.what })
    submitHybridWorkArrangement()
    await screen.findByRole('heading', { name: commuteLimitRecommendation.what })

    submitCommuteLimit()

    expect(
      await screen.findByRole('heading', { name: clarifiedRecommendation.what }),
    ).toBeVisible()
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/recommendations/primary?work_arrangement=hybrid&acceptable_commute_minutes=45',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    expect(
      screen.getByText('Maximum workable one-way commute recorded: 45 minutes.'),
    ).toBeVisible()
    expect(
      screen.queryByRole('button', { name: 'Use this commute limit' }),
    ).not.toBeInTheDocument()
    expect(
      screen.getByLabelText('What area is your spouse most likely to work in?'),
    ).toHaveAttribute('placeholder', 'San Jose or the surrounding area')
    expect(
      screen.getByRole('button', { name: 'Use this workplace area' }),
    ).toBeDisabled()
  })

  it('keeps workplace-area draft local, trims it, and submits it explicitly', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(responseWith(unclearRecommendation))
      .mockResolvedValueOnce(responseWith(commuteLimitRecommendation))
      .mockResolvedValueOnce(responseWith(clarifiedRecommendation))
      .mockResolvedValueOnce(responseWith(evidenceRecommendation))
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await screen.findByRole('heading', { name: unclearRecommendation.what })
    submitHybridWorkArrangement()
    await screen.findByRole('heading', { name: commuteLimitRecommendation.what })
    submitCommuteLimit()
    await screen.findByRole('heading', { name: clarifiedRecommendation.what })

    const input = screen.getByLabelText(
      'What area is your spouse most likely to work in?',
    )
    const button = screen.getByRole('button', { name: 'Use this workplace area' })

    expect(input).toHaveAttribute('maxlength', '120')
    fireEvent.change(input, { target: { value: '   ' } })
    expect(button).toBeDisabled()
    expect(fetchMock).toHaveBeenCalledTimes(3)

    fireEvent.change(input, { target: { value: 'a'.repeat(121) } })
    expect(button).toBeDisabled()
    expect(fetchMock).toHaveBeenCalledTimes(3)

    fireEvent.change(input, { target: { value: '  San Jose  ' } })
    expect(button).toBeEnabled()
    expect(fetchMock).toHaveBeenCalledTimes(3)
    fireEvent.click(button)

    expect(
      await screen.findByRole('heading', { name: evidenceRecommendation.what }),
    ).toBeVisible()
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/recommendations/primary?work_arrangement=hybrid&acceptable_commute_minutes=45&likely_workplace_area=San+Jose',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    expect(screen.getByText('Likely workplace area recorded: San Jose.')).toBeVisible()
    expect(
      screen.queryByRole('button', { name: 'Use this workplace area' }),
    ).not.toBeInTheDocument()
    expect(
      screen.getByLabelText('How would your spouse most likely commute?'),
    ).toHaveValue('')
    expect(screen.getByText('Drive')).toBeVisible()
    expect(screen.getByText('Public transit')).toBeVisible()
    expect(screen.getByText('Either driving or public transit')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Use this travel mode' })).toBeDisabled()
  })

  it('keeps travel-mode draft local and submits a mode-specific request', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(responseWith(unclearRecommendation))
      .mockResolvedValueOnce(responseWith(commuteLimitRecommendation))
      .mockResolvedValueOnce(responseWith(clarifiedRecommendation))
      .mockResolvedValueOnce(responseWith(evidenceRecommendation))
      .mockResolvedValueOnce(responseWith(travelModeRecommendation))
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await screen.findByRole('heading', { name: unclearRecommendation.what })
    submitHybridWorkArrangement()
    await screen.findByRole('heading', { name: commuteLimitRecommendation.what })
    submitCommuteLimit()
    await screen.findByRole('heading', { name: clarifiedRecommendation.what })
    submitWorkplaceArea()
    await screen.findByRole('heading', { name: evidenceRecommendation.what })

    fireEvent.change(
      screen.getByLabelText('How would your spouse most likely commute?'),
      { target: { value: 'public_transit' } },
    )

    expect(fetchMock).toHaveBeenCalledTimes(4)
    expect(screen.getByRole('button', { name: 'Use this travel mode' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Use this travel mode' }))

    expect(
      await screen.findByRole('heading', { name: travelModeRecommendation.what }),
    ).toBeVisible()
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/recommendations/primary?work_arrangement=hybrid&acceptable_commute_minutes=45&likely_workplace_area=San+Jose&travel_mode=public_transit',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    expect(
      screen.getByText('Intended commute mode recorded: Public transit.'),
    ).toBeVisible()
    expect(screen.queryByText('public_transit')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Use this travel mode' }),
    ).not.toBeInTheDocument()
  })

  it('does not let an obsolete response overwrite the travel-mode recommendation', async () => {
    let resolveObsolete: ((response: Response) => void) | undefined
    const obsoleteRequest = new Promise<Response>((resolve) => {
      resolveObsolete = resolve
    })
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(obsoleteRequest)
      .mockResolvedValueOnce(responseWith(unclearRecommendation))
      .mockResolvedValueOnce(responseWith(commuteLimitRecommendation))
      .mockResolvedValueOnce(responseWith(clarifiedRecommendation))
      .mockResolvedValueOnce(responseWith(evidenceRecommendation))
      .mockResolvedValueOnce(responseWith(travelModeRecommendation))
    vi.stubGlobal('fetch', fetchMock)

    render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
    await screen.findByRole('heading', { name: unclearRecommendation.what })

    submitHybridWorkArrangement()
    await screen.findByRole('heading', { name: commuteLimitRecommendation.what })
    submitCommuteLimit()
    await screen.findByRole('heading', { name: clarifiedRecommendation.what })
    submitWorkplaceArea()
    await screen.findByRole('heading', { name: evidenceRecommendation.what })
    submitTravelMode()

    expect(
      await screen.findByRole('heading', { name: travelModeRecommendation.what }),
    ).toBeVisible()

    await act(async () => {
      resolveObsolete?.(responseWith(unclearRecommendation))
      await obsoleteRequest
    })

    expect(
      screen.getByRole('heading', { name: travelModeRecommendation.what }),
    ).toBeVisible()
    expect(
      screen.queryByRole('heading', { name: unclearRecommendation.what }),
    ).not.toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('alert', { name: 'Recommendation unavailable' }),
    ).not.toBeInTheDocument()
  })

  it('renders an error when the travel-mode recommendation request fails', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(responseWith(unclearRecommendation))
      .mockResolvedValueOnce(responseWith(commuteLimitRecommendation))
      .mockResolvedValueOnce(responseWith(clarifiedRecommendation))
      .mockResolvedValueOnce(responseWith(evidenceRecommendation))
      .mockResolvedValueOnce({ ok: false, status: 503 } as Response)
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    await screen.findByRole('heading', { name: unclearRecommendation.what })

    submitHybridWorkArrangement()
    await screen.findByRole('heading', { name: commuteLimitRecommendation.what })
    submitCommuteLimit()
    await screen.findByRole('heading', { name: clarifiedRecommendation.what })
    submitWorkplaceArea()
    await screen.findByRole('heading', { name: evidenceRecommendation.what })
    submitTravelMode()

    expect(await screen.findByRole('alert')).toHaveTextContent('Recommendation unavailable')
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Unable to load the recommendation (503).',
    )
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Use this commute limit' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText('Maximum workable one-way commute recorded: 45 minutes.'),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText('Likely workplace area recorded: San Jose.'),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText('Intended commute mode recorded: Public transit.'),
    ).not.toBeInTheDocument()
  })
})
