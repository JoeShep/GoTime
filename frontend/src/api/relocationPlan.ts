export type TaskStatus = 'not_started' | 'in_progress' | 'completed'
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical'
export type TaskCategory =
  | 'employment'
  | 'family'
  | 'financial'
  | 'healthcare'
  | 'housing'
  | 'logistics'

export interface Phase {
  id: string
  title: string
  position: number
}

export interface RelocationTask {
  id: string
  title: string
  description: string | null
  phase_id: string
  category: TaskCategory
  status: TaskStatus
  assignees: string[]
  start_date: string | null
  due_date: string | null
  priority: TaskPriority
  dependency_task_ids: string[]
  blocked: boolean
}

export interface RelocationPlan {
  id: string
  title: string
  phases: Phase[]
  tasks: RelocationTask[]
}

export interface TaskWrite {
  title: string
  description: string | null
  phase_id: string
  category: TaskCategory
  status: TaskStatus
  assignees: string[]
  start_date: string | null
  due_date: string | null
  priority: TaskPriority
  dependency_task_ids: string[]
}

export interface RankingFactors {
  due_state: 'overdue' | 'due_today' | 'upcoming' | 'no_due_date'
  due_date: string | null
  priority: TaskPriority
  task_status: TaskStatus
  directly_unblocks_count: number
  phase_position: number
}

export interface RelocationTaskRecommendation {
  status: 'recommended' | 'no_actionable_task'
  task_id: string | null
  task_title: string | null
  phase_id: string | null
  phase_title: string | null
  why: string[]
  why_now: string
  directly_unblocks_task_ids: string[]
  ranking_factors: RankingFactors | null
}

async function planRequest(path: string, init?: RequestInit): Promise<RelocationPlan> {
  const response = await fetch(path, init)
  if (!response.ok) {
    let message = `Unable to save the relocation plan (${response.status}).`
    try {
      const body = (await response.json()) as { detail?: string | Array<{ msg?: string }> }
      if (typeof body.detail === 'string') {
        message = body.detail
      } else if (Array.isArray(body.detail)) {
        message = body.detail.map((item) => item.msg).filter(Boolean).join(' ') || message
      }
    } catch {
      // Keep the bounded status-based message when the response is not JSON.
    }
    throw new Error(message)
  }
  return (await response.json()) as RelocationPlan
}

export function fetchRelocationPlan(signal?: AbortSignal): Promise<RelocationPlan> {
  return planRequest('/api/relocation-plan', { signal })
}

export async function fetchRelocationTaskRecommendation(
  signal?: AbortSignal,
): Promise<RelocationTaskRecommendation> {
  const response = await fetch('/api/relocation-plan/recommendation', { signal })
  if (!response.ok) {
    throw new Error(`Unable to load the next-task recommendation (${response.status}).`)
  }
  return (await response.json()) as RelocationTaskRecommendation
}

export function createTask(id: string, task: TaskWrite): Promise<RelocationPlan> {
  return planRequest('/api/relocation-plan/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, ...task }),
  })
}

export function replaceTask(id: string, task: TaskWrite): Promise<RelocationPlan> {
  return planRequest(`/api/relocation-plan/tasks/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(task),
  })
}

export function changeTaskStatus(
  id: string,
  status: TaskStatus,
): Promise<RelocationPlan> {
  return planRequest(
    `/api/relocation-plan/tasks/${encodeURIComponent(id)}/status`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    },
  )
}
