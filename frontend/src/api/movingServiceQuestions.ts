export type ExperimentFixture =
  | 'storage_unknown'
  | 'complete'
  | 'invalid_ai_response'
  | 'adapter_unavailable'
  | 'adapter_timeout'
  | 'budget_unavailable'
  | 'ai_disabled'

export type SuggestionSource =
  | 'fake_ai_adapter'
  | 'deterministic_fallback'
  | 'none'

export interface MovingServiceQuestionSuggestion {
  question_id: string
  question: string
  why_it_matters: string
  answer_type: 'boolean' | 'enum'
  allowed_enum_values: string[] | null
  requires_user_confirmation: true
  grounding_details: string[]
}

export interface MovingServiceQuestionExperimentResult {
  suggestion: MovingServiceQuestionSuggestion | null
  source: SuggestionSource
  no_question_reason: string | null
  observability: {
    fixture_id: ExperimentFixture
    fallback_used: boolean
    fallback_reason: string | null
    estimated_cost: '$0.00'
  }
}

export async function fetchMovingServiceQuestion(
  fixture: ExperimentFixture,
  signal?: AbortSignal,
): Promise<MovingServiceQuestionExperimentResult> {
  const parameters = new URLSearchParams({ scenario: fixture })
  const response = await fetch(
    `/api/experiments/moving-service-question?${parameters}`,
    { signal },
  )

  if (!response.ok) {
    throw new Error(
      `Unable to load the experimental suggestion (${response.status}).`,
    )
  }

  return (await response.json()) as MovingServiceQuestionExperimentResult
}
