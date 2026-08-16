import { useEffect, useMemo, useRef, useState } from 'react'
import { Accordion, Alert, Badge, Button, Card, Col, Form, Row, Spinner, Stack } from 'react-bootstrap'
import {
  changeTaskStatus,
  createTask,
  fetchRelocationPlan,
  replaceTask,
  type RelocationPlan as RelocationPlanData,
  type RelocationTask,
  type TaskCategory,
  type TaskPriority,
  type TaskStatus,
  type TaskWrite,
} from './api/relocationPlan'

const statusLabels: Record<TaskStatus, string> = {
  not_started: 'Not started',
  in_progress: 'In progress',
  completed: 'Completed',
}

const priorityLabels: Record<TaskPriority, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
}

const categoryLabels: Record<TaskCategory, string> = {
  administrative: 'Administrative',
  employment: 'Employment',
  family: 'Family',
  financial: 'Financial',
  healthcare: 'Healthcare',
  housing: 'Housing',
  logistics: 'Logistics',
}

interface TaskDraft {
  title: string
  description: string
  phaseId: string
  category: TaskCategory
  status: TaskStatus
  assignees: string
  startDate: string
  dueDate: string
  priority: TaskPriority
  dependencies: string[]
}

function emptyDraft(phaseId: string): TaskDraft {
  return {
    title: '',
    description: '',
    phaseId,
    category: 'logistics',
    status: 'not_started',
    assignees: '',
    startDate: '',
    dueDate: '',
    priority: 'medium',
    dependencies: [],
  }
}

function draftFromTask(task: RelocationTask): TaskDraft {
  return {
    title: task.title,
    description: task.description ?? '',
    phaseId: task.phase_id,
    category: task.category,
    status: task.status,
    assignees: task.assignees.join(', '),
    startDate: task.start_date ?? '',
    dueDate: task.due_date ?? '',
    priority: task.priority,
    dependencies: [...task.dependency_task_ids],
  }
}

function writeFromDraft(draft: TaskDraft): TaskWrite {
  return {
    title: draft.title.trim(),
    description: draft.description.trim() || null,
    phase_id: draft.phaseId,
    category: draft.category,
    status: draft.status,
    assignees: draft.assignees.split(',').map((name) => name.trim()).filter(Boolean),
    start_date: draft.startDate || null,
    due_date: draft.dueDate || null,
    priority: draft.priority,
    dependency_task_ids: draft.dependencies,
  }
}

export function generateTaskId(title: string): string {
  const slug = title
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 26)
    .replace(/-$/, '')
  return `${slug || 'task'}-${crypto.randomUUID()}`
}

export function RelocationPlan({ onPlanChanged }: { onPlanChanged?: () => void }) {
  const [plan, setPlan] = useState<RelocationPlanData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState<TaskDraft | null>(null)
  const [dependencyQuery, setDependencyQuery] = useState('')
  const editorRef = useRef<HTMLDivElement>(null)
  const titleInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetchRelocationPlan(controller.signal)
      .then(setPlan)
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(requestError instanceof Error ? requestError.message : 'Unable to load the relocation plan.')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [])

  const taskById = useMemo(
    () => new Map(plan?.tasks.map((task) => [task.id, task]) ?? []),
    [plan],
  )
  const dependencyGroups = useMemo(() => {
    const normalizedQuery = dependencyQuery.trim().toLocaleLowerCase()
    return (plan?.phases ?? []).map((phase) => ({
      phase,
      tasks: (plan?.tasks ?? []).filter((task) =>
        task.id !== editingId
        && task.phase_id === phase.id
        && (task.status !== 'completed' || draft?.dependencies.includes(task.id))
        && task.title.toLocaleLowerCase().includes(normalizedQuery),
      ),
    })).filter((group) => group.tasks.length > 0)
  }, [dependencyQuery, draft?.dependencies, editingId, plan])

  useEffect(() => {
    if (!draft) return
    editorRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
    titleInputRef.current?.focus()
  }, [draft !== null, editingId])

  function beginAdd() {
    if (!plan) return
    setEditingId(null)
    setDraft(emptyDraft(plan.phases[0].id))
    setDependencyQuery('')
    setError(null)
    setNotice(null)
  }

  function beginEdit(task: RelocationTask) {
    setEditingId(task.id)
    setDraft(draftFromTask(task))
    setDependencyQuery('')
    setError(null)
    setNotice(null)
  }

  async function saveTask() {
    if (!draft || saving) return
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      const write = writeFromDraft(draft)
      const updated = editingId
        ? await replaceTask(editingId, write)
        : await createTask(generateTaskId(write.title), write)
      setPlan(updated)
      onPlanChanged?.()
      setDraft(null)
      setEditingId(null)
      setNotice(editingId ? 'Task updated.' : 'Task added.')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to save the task.')
    } finally {
      setSaving(false)
    }
  }

  async function updateStatus(task: RelocationTask, status: TaskStatus) {
    setSaving(true)
    setError(null)
    setNotice(null)
    try {
      setPlan(await changeTaskStatus(task.id, status))
      onPlanChanged?.()
      setNotice(`Status updated for ${task.title}.`)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to update task status.')
    } finally {
      setSaving(false)
    }
  }

  function renderTask(task: RelocationTask) {
    return (
      <article className={`task-item rounded-3 p-3 ${task.blocked ? 'is-blocked' : ''}`} key={task.id}>
        <div className="d-flex flex-wrap justify-content-between gap-3">
          <div>
            <div className="d-flex flex-wrap align-items-center gap-2 mb-1"><h4 className="task-title mb-0">{task.title}</h4>{task.blocked && <Badge bg="warning" text="dark">Blocked</Badge>}<Badge bg="light" text="dark">{priorityLabels[task.priority]}</Badge></div>
            <p className="text-muted mb-2">{categoryLabels[task.category]}{task.assignees.length > 0 ? ` · ${task.assignees.join(', ')}` : ' · Unassigned'}{task.due_date ? ` · Due ${task.due_date}` : ''}</p>
            {task.description && <p className="mb-2">{task.description}</p>}
            {task.dependency_task_ids.length > 0 && <p className="dependency-context mb-0"><strong>Depends on:</strong> {task.dependency_task_ids.map((id) => taskById.get(id)?.title ?? id).join(', ')}</p>}
          </div>
          <div className="task-actions d-flex flex-wrap align-items-start gap-2">
            <Form.Select aria-label={`Status for ${task.title}`} disabled={saving} value={task.status} onChange={(event) => void updateStatus(task, event.target.value as TaskStatus)}>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Form.Select>
            <Button variant="outline-secondary" onClick={() => beginEdit(task)}>Edit</Button>
          </div>
        </div>
      </article>
    )
  }

  return (
    <section className="relocation-plan mt-5" aria-labelledby="relocation-plan-heading">
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-3">
        <div>
          <p className="section-label mb-1">Persistent plan</p>
          <h2 className="detail-heading mb-0" id="relocation-plan-heading">
            {plan?.title ?? 'Family relocation plan'}
          </h2>
        </div>
        {plan && !draft && <Button onClick={beginAdd}>Add task</Button>}
      </div>

      {loading && <div className="py-4 text-center" role="status"><Spinner size="sm" /> <span>Loading relocation plan…</span></div>}
      {error && <Alert variant="danger">{error}</Alert>}
      {notice && <Alert variant="success">{notice}</Alert>}

      {draft && plan && (
        <div ref={editorRef}>
          <Card className="task-editor mb-4">
            <Card.Body>
              <Card.Title as="h3">{editingId ? 'Edit task' : 'Add task'}</Card.Title>
              <Form onSubmit={(event) => { event.preventDefault(); void saveTask() }}>
              <Stack direction="horizontal" gap={2} className="task-editor-actions sticky-top flex-wrap py-3 mb-3">
                <Button type="submit" disabled={saving}>
                  {saving ? (editingId ? 'Saving…' : 'Creating…') : (editingId ? 'Save changes' : 'Create task')}
                </Button>
                <Button type="button" variant="outline-secondary" disabled={saving} onClick={() => { setDraft(null); setEditingId(null); setDependencyQuery('') }}>Cancel</Button>
              </Stack>
              <Row className="g-3">
                <Col md={8}><Form.Group controlId="task-title"><Form.Label>Title</Form.Label><Form.Control ref={titleInputRef} required maxLength={200} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></Form.Group></Col>
                <Col md={4}><Form.Group controlId="task-phase"><Form.Label>Phase</Form.Label><Form.Select value={draft.phaseId} onChange={(event) => setDraft({ ...draft, phaseId: event.target.value })}>{plan.phases.map((phase) => <option key={phase.id} value={phase.id}>{phase.title}</option>)}</Form.Select></Form.Group></Col>
                <Col xs={12}><Form.Group controlId="task-description"><Form.Label>Description <span className="text-muted">(optional)</span></Form.Label><Form.Control as="textarea" rows={2} maxLength={2000} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></Form.Group></Col>
                <Col md={4}><Form.Group controlId="task-category"><Form.Label>Category</Form.Label><Form.Select value={draft.category} onChange={(event) => setDraft({ ...draft, category: event.target.value as TaskCategory })}>{Object.entries(categoryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Form.Select></Form.Group></Col>
                <Col md={4}><Form.Group controlId="task-priority"><Form.Label>Priority</Form.Label><Form.Select value={draft.priority} onChange={(event) => setDraft({ ...draft, priority: event.target.value as TaskPriority })}>{Object.entries(priorityLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Form.Select></Form.Group></Col>
                <Col md={4}><Form.Group controlId="task-status"><Form.Label>Status</Form.Label><Form.Select value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value as TaskStatus })}>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Form.Select></Form.Group></Col>
                <Col md={6}><Form.Group controlId="task-assignees"><Form.Label>Assignees <span className="text-muted">(optional)</span></Form.Label><Form.Control placeholder="Separate names with commas" value={draft.assignees} onChange={(event) => setDraft({ ...draft, assignees: event.target.value })} /></Form.Group></Col>
                <Col md={3}><Form.Group controlId="task-start-date"><Form.Label>Start date <span className="text-muted">(optional)</span></Form.Label><Form.Control type="date" value={draft.startDate} onChange={(event) => setDraft({ ...draft, startDate: event.target.value })} /></Form.Group></Col>
                <Col md={3}><Form.Group controlId="task-due-date"><Form.Label>Due date <span className="text-muted">(optional)</span></Form.Label><Form.Control type="date" value={draft.dueDate} onChange={(event) => setDraft({ ...draft, dueDate: event.target.value })} /></Form.Group></Col>
                <Col xs={12}>
                  <Form.Group>
                    <Form.Label>Dependencies <span className="text-muted">(optional)</span></Form.Label>
                    <Form.Control
                      className="mb-2"
                      type="search"
                      aria-label="Search dependencies"
                      placeholder="Search tasks"
                      value={dependencyQuery}
                      onChange={(event) => setDependencyQuery(event.target.value)}
                    />
                    <div className="dependency-options rounded-3 p-3">
                      {dependencyGroups.map(({ phase, tasks }) => (
                        <fieldset className="dependency-phase mb-3" key={phase.id}>
                          <legend className="dependency-phase-title mb-1">{phase.title}</legend>
                          {tasks.map((task) => (
                            <Form.Check key={task.id} id={`dependency-${task.id}`} label={`${task.title} (${statusLabels[task.status]})`} checked={draft.dependencies.includes(task.id)} onChange={(event) => setDraft({ ...draft, dependencies: event.target.checked ? [...draft.dependencies, task.id] : draft.dependencies.filter((id) => id !== task.id) })} />
                          ))}
                        </fieldset>
                      ))}
                      {!plan.tasks.some((task) => task.id !== editingId && (task.status !== 'completed' || draft.dependencies.includes(task.id))) && <p className="text-muted mb-0">No other tasks are available.</p>}
                      {plan.tasks.some((task) => task.id !== editingId && (task.status !== 'completed' || draft.dependencies.includes(task.id))) && dependencyGroups.length === 0 && <p className="text-muted mb-0">No tasks match your search.</p>}
                    </div>
                  </Form.Group>
                </Col>
              </Row>
              </Form>
            </Card.Body>
          </Card>
        </div>
      )}

      {plan?.phases.map((phase) => {
        const phaseTasks = plan.tasks.filter((task) => task.phase_id === phase.id)
        const activeTasks = phaseTasks.filter((task) => task.status !== 'completed')
        const completedTasks = phaseTasks.filter((task) => task.status === 'completed')
        return (
          <Card className="phase-card mb-3" key={phase.id}>
            <Card.Header as="h3">{phase.title}</Card.Header>
            <Card.Body>
              {phaseTasks.length === 0 && <p className="text-muted mb-0">No tasks in this phase yet.</p>}
              {activeTasks.length === 0 && completedTasks.length > 0 && <p className="text-muted mb-0">No active tasks in this phase.</p>}
              <Stack gap={3}>
                {activeTasks.map(renderTask)}
              </Stack>
              {completedTasks.length > 0 && (
                <Accordion className="completed-tasks mt-3">
                  <Accordion.Item eventKey="completed">
                    <Accordion.Header>Completed ({completedTasks.length})</Accordion.Header>
                    <Accordion.Body>
                      <Stack gap={3}>{completedTasks.map(renderTask)}</Stack>
                    </Accordion.Body>
                  </Accordion.Item>
                </Accordion>
              )}
            </Card.Body>
          </Card>
        )
      })}
    </section>
  )
}
