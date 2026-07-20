export type EmploymentRequirementsState = 'unclear' | 'clarified'

export interface Assumption {
  id: string
  description: string
  status: string
  related_decision_ids: string[]
  validation_method: string
}

export interface Recommendation {
  what: string
  why: string[]
  why_now: string
  related_decision_id: string | null
  relevant_dependencies: string[]
  blocked_downstream_work: string[]
  related_assumptions: Assumption[]
}

export async function fetchPrimaryRecommendation(
  employmentRequirements: EmploymentRequirementsState,
  signal?: AbortSignal,
): Promise<Recommendation> {
  const response = await fetch(
    `/api/recommendations/primary?employment_requirements=${employmentRequirements}`,
    { signal },
  )

  if (!response.ok) {
    throw new Error(`Unable to load the recommendation (${response.status}).`)
  }

  return (await response.json()) as Recommendation
}
