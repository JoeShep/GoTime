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
  categories: TaskCategory[]
  status: TaskStatus
  assignees: string[]
  start_date: string | null
  due_date: string | null
  priority: TaskPriority
  dependency_task_ids: string[]
  blocked: boolean
  parent_task_id?: string | null
  subtask_position?: number | null
  stored_status?: TaskStatus | null
  automatic_status?: TaskStatus | null
  manual_status_override?: TaskStatus | null
  is_parent?: boolean
  subtask_count?: number
  completed_subtask_count?: number
}

export interface Milestone {
  id: string
  title: string
  description: string | null
  target_earliest_date: string | null
  target_latest_date: string | null
  status: 'pending' | 'achieved'
  achieved_at: string | null
}

export interface DecisionOption {
  id: string
  title: string
  description: string | null
}

export interface Decision {
  id: string
  title: string
  description: string | null
  milestone_id: string
  options: DecisionOption[]
  status: 'unresolved' | 'resolved'
  selected_option_id: string | null
  preparation_task_ids?: string[]
  preparation_readiness?: 'no_preparation_tracked' | 'preparation_incomplete' | 'ready_to_decide'
  completed_preparation_task_count?: number
}

export interface RelocationPlan {
  id: string
  title: string
  phases: Phase[]
  tasks: RelocationTask[]
  milestones: Milestone[]
  decisions: Decision[]
}

export type MilestoneWrite = Omit<Milestone, 'id' | 'status' | 'achieved_at'>
export type DecisionWrite = Pick<Decision, 'title' | 'description' | 'milestone_id' | 'options'> & { preparation_task_ids: string[] }

export interface TaskWrite {
  title: string
  description: string | null
  phase_id: string
  categories: TaskCategory[]
  status: TaskStatus
  assignees: string[]
  start_date: string | null
  due_date: string | null
  priority: TaskPriority
  dependency_task_ids: string[]
  parent_task_id?: string | null
  subtask_position?: number | null
  confirm_parent_phase_move?: boolean
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

export type PlanErrorCode =
  | 'duplicate_task_title'
  | 'duplicate_milestone_title'
  | 'duplicate_decision_title'
  | 'parent_phase_move_confirmation_required'
  | 'parent_status_override_confirmation_required'
  | 'decision_preparation_confirmation_required'
  | 'decision_preparation_hierarchy_conflict'

export class PlanRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: PlanErrorCode | null = null,
  ) {
    super(message)
    this.name = 'PlanRequestError'
  }
}

async function planRequest(path: string, init?: RequestInit): Promise<RelocationPlan> {
  const response = await fetch(path, init)
  if (!response.ok) {
    let message = `Unable to save the relocation plan (${response.status}).`
    let code: PlanErrorCode | null = null
    try {
      const body = (await response.json()) as {
        detail?: string | Array<{ msg?: string }> | { code?: PlanErrorCode; message?: string }
      }
      if (typeof body.detail === 'string') {
        message = body.detail
      } else if (Array.isArray(body.detail)) {
        message = body.detail.map((item) => item.msg).filter(Boolean).join(' ') || message
      } else if (body.detail && typeof body.detail === 'object') {
        message = body.detail.message || message
        code = body.detail.code ?? null
      }
    } catch {
      // Keep the bounded status-based message when the response is not JSON.
    }
    throw new PlanRequestError(message, response.status, code)
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
  confirmManualOverride = false,
): Promise<RelocationPlan> {
  return planRequest(
    `/api/relocation-plan/tasks/${encodeURIComponent(id)}/status`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, ...(confirmManualOverride ? { confirm_manual_override: true } : {}) }),
    },
  )
}

export function returnParentToAutomaticStatus(id: string): Promise<RelocationPlan> {
  return planRequest(`/api/relocation-plan/tasks/${encodeURIComponent(id)}/status-override`, {
    method: 'DELETE',
  })
}

export function reorderSubtasks(parentId: string, childTaskIds: string[]): Promise<RelocationPlan> {
  return planRequest(`/api/relocation-plan/tasks/${encodeURIComponent(parentId)}/subtasks/order`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ child_task_ids: childTaskIds }),
  })
}

export function createMilestone(id: string, milestone: MilestoneWrite) {
  return planRequest('/api/relocation-plan/milestones', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, ...milestone }),
  })
}

export function replaceMilestone(id: string, milestone: MilestoneWrite) {
  return planRequest(`/api/relocation-plan/milestones/${encodeURIComponent(id)}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(milestone),
  })
}

export function changeMilestoneAchievement(id: string, achieved: boolean) {
  return planRequest(`/api/relocation-plan/milestones/${encodeURIComponent(id)}/achievement`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ achieved }),
  })
}

export function createDecision(id: string, decision: DecisionWrite) {
  return planRequest('/api/relocation-plan/decisions', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, ...decision }),
  })
}

export function replaceDecision(id: string, decision: DecisionWrite) {
  return planRequest(`/api/relocation-plan/decisions/${encodeURIComponent(id)}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(decision),
  })
}

export function changeDecisionSelection(id: string, selectedOptionId: string | null, confirmNotReady = false) {
  return planRequest(`/api/relocation-plan/decisions/${encodeURIComponent(id)}/selection`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ selected_option_id: selectedOptionId, confirm_not_ready: confirmNotReady }),
  })
}
