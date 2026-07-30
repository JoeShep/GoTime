import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MovingServiceQuestionExperiment } from './MovingServiceQuestionExperiment'
import type {
  MovingServiceQuestionExperimentResult,
  SuggestionSource,
} from './api/movingServiceQuestions'

const storageSuggestion = {
  question_id: 'ai-temporary-storage-v1',
  question: 'Will you need temporary storage between homes?',
  why_it_matters:
    'Storage needs can change which moving-service models are practical to investigate.',
  answer_type: 'boolean' as const,
  allowed_enum_values: null,
  requires_user_confirmation: true as const,
  grounding_details: [
    'For an interstate move handled by a household-goods mover, a possible need for temporary storage before final delivery is relevant when identifying the services to request.',
  ],
}

function experimentResult(
  source: SuggestionSource = 'fake_ai_adapter',
): MovingServiceQuestionExperimentResult {
  return {
    suggestion: storageSuggestion,
    source,
    no_question_reason: null,
    observability: {
      fixture_id:
        source === 'deterministic_fallback'
          ? 'invalid_ai_response'
          : 'storage_unknown',
      fallback_used: source === 'deterministic_fallback',
      fallback_reason:
        source === 'deterministic_fallback'
          ? 'invalid_adapter_response'
          : null,
      estimated_cost: '$0.00',
    },
  }
}

function responseWith(
  result: MovingServiceQuestionExperimentResult,
): Response {
  return {
    ok: true,
    status: 200,
    json: async () => result,
  } as Response
}

async function requestSuggestion() {
  fireEvent.click(
    screen.getByRole('button', { name: 'Get a suggested question' }),
  )
  return screen.findByText(storageSuggestion.question)
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('moving-service question experiment', () => {
  it('does not invoke the experiment until the user explicitly requests it', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<MovingServiceQuestionExperiment />)

    expect(
      screen.getByRole('heading', {
        name: 'Something else worth clarifying',
      }),
    ).toBeVisible()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows suggestion loading after the explicit action', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => undefined)))

    render(<MovingServiceQuestionExperiment />)
    fireEvent.click(
      screen.getByRole('button', { name: 'Get a suggested question' }),
    )

    expect(screen.getByRole('status')).toHaveTextContent(
      'Loading experimental suggestion',
    )
  })

  it('renders a fake-adapter result as an experimental suggestion', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responseWith(experimentResult())),
    )

    render(<MovingServiceQuestionExperiment />)
    await requestSuggestion()

    expect(screen.getByText('Experimental suggestion')).toBeVisible()
    expect(screen.getByText(storageSuggestion.why_it_matters)).toBeVisible()
    expect(screen.queryByText('Fake AI adapter')).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(
      '/api/experiments/moving-service-question?scenario=storage_unknown',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
  })

  it('renders deterministic fallback as useful planning-guide guidance', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          responseWith(experimentResult('deterministic_fallback')),
        ),
    )

    render(
      <MovingServiceQuestionExperiment fixture="invalid_ai_response" />,
    )
    await requestSuggestion()

    expect(
      screen.getByText('Suggested from GoTime’s planning guide'),
    ).toBeVisible()
    expect(
      screen.queryByRole('alert', { name: 'Suggestion unavailable' }),
    ).not.toBeInTheDocument()
  })

  it('reveals supplied grounding details on request', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responseWith(experimentResult())),
    )

    render(<MovingServiceQuestionExperiment />)
    await requestSuggestion()
    fireEvent.click(
      screen.getByRole('button', { name: 'Why are you asking?' }),
    )

    expect(screen.getByText('Why GoTime is asking')).toBeVisible()
    expect(
      screen.getByText(storageSuggestion.grounding_details[0]),
    ).toBeVisible()
  })

  it('dismisses the suggestion locally without implying a state update', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responseWith(experimentResult())),
    )

    render(<MovingServiceQuestionExperiment />)
    await requestSuggestion()
    fireEvent.click(screen.getByRole('button', { name: 'Not relevant' }))

    expect(screen.queryByText(storageSuggestion.question)).not.toBeInTheDocument()
    expect(
      screen.getByText('Suggestion dismissed. No GoTime state was changed.'),
    ).toBeVisible()
  })

  it('keeps an answered suggestion local and confirms the trusted-state boundary', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(responseWith(experimentResult())),
    )

    render(<MovingServiceQuestionExperiment />)
    await requestSuggestion()
    fireEvent.click(screen.getByRole('button', { name: 'Answer this' }))

    const confirmation = screen.getByRole('button', {
      name: 'Confirm for this demonstration',
    })
    expect(confirmation).toBeDisabled()
    fireEvent.click(screen.getByRole('radio', { name: 'Yes' }))
    expect(confirmation).toBeEnabled()
    fireEvent.click(confirmation)

    expect(
      screen.getByText(
        'Answer confirmed locally for this experiment. Trusted GoTime state was not changed.',
      ),
    ).toBeVisible()
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('renders a bounded error state and permits an explicit retry', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 503 } as Response)
      .mockResolvedValueOnce(responseWith(experimentResult()))
    vi.stubGlobal('fetch', fetchMock)

    render(<MovingServiceQuestionExperiment />)
    fireEvent.click(
      screen.getByRole('button', { name: 'Get a suggested question' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Suggestion unavailable',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    expect(await screen.findByText(storageSuggestion.question)).toBeVisible()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('does not allow an obsolete fixture response to overwrite current state', async () => {
    let resolveObsolete: ((response: Response) => void) | undefined
    const obsoleteRequest = new Promise<Response>((resolve) => {
      resolveObsolete = resolve
    })
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(obsoleteRequest))

    const { rerender } = render(
      <MovingServiceQuestionExperiment fixture="storage_unknown" />,
    )
    fireEvent.click(
      screen.getByRole('button', { name: 'Get a suggested question' }),
    )
    expect(screen.getByRole('status')).toBeVisible()

    rerender(<MovingServiceQuestionExperiment fixture="complete" />)

    await act(async () => {
      resolveObsolete?.(responseWith(experimentResult()))
      await obsoleteRequest
    })

    expect(screen.queryByText(storageSuggestion.question)).not.toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Get a suggested question' }),
    ).toBeVisible()
  })
})
