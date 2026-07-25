export type WorkArrangement = 'remote' | 'hybrid' | 'on_site' | 'flexible'
export const LIKELY_WORKPLACE_AREA_MAX_LENGTH = 120

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
  workArrangement?: WorkArrangement,
  acceptableCommuteMinutes?: number,
  likelyWorkplaceArea?: string,
  signal?: AbortSignal,
): Promise<Recommendation> {
  const parameters = new URLSearchParams()
  if (workArrangement) {
    parameters.set('work_arrangement', workArrangement)
  }
  if (acceptableCommuteMinutes !== undefined) {
    parameters.set('acceptable_commute_minutes', String(acceptableCommuteMinutes))
  }
  if (likelyWorkplaceArea !== undefined) {
    parameters.set('likely_workplace_area', likelyWorkplaceArea)
  }
  const query = parameters.size > 0 ? `?${parameters}` : ''
  const response = await fetch(
    `/api/recommendations/primary${query}`,
    { signal },
  )

  if (!response.ok) {
    throw new Error(`Unable to load the recommendation (${response.status}).`)
  }

  return (await response.json()) as Recommendation
}
