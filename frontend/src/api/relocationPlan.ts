export type TaskStatus = 'not_started' | 'in_progress' | 'completed'
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical'
export type TaskCategory =
  | 'administrative'
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
