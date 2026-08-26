import { type KeyboardEvent, type ReactNode, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Accordion, Alert, Badge, Button, Card, Col, Dropdown, Form, Row, Spinner, Stack } from 'react-bootstrap'
import {
  changeTaskStatus,
  createTask,
  fetchRelocationPlan,
  replaceTask,
  returnParentToAutomaticStatus,
  PlanRequestError,
  type RelocationPlan as RelocationPlanData,
  type RelocationTask,
  type TaskCategory,
  type TaskPriority,
  type TaskStatus,
  type TaskWrite,
} from './api/relocationPlan'
import { hasDuplicatePlanItemTitle } from './titleUniqueness'
import { MilestoneDecisionFoundation } from './MilestoneDecisionFoundation'
import { useFind } from './FindContext'
import { returnPlanToTopEvent, savePlanPositionEvent } from './planWorkspaceEvents'

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
  employment: 'Employment',
  family: 'Family',
  financial: 'Financial',
  healthcare: 'Healthcare',
  housing: 'Housing',
  logistics: 'Logistics',
}

const categoryOrder = Object.keys(categoryLabels) as TaskCategory[]
type CategoryFilter = TaskCategory | 'uncategorized'

const planExpansionStateVersion = 1
const planScrollStateVersion = 1
const planFilterStateVersion = 1
const allCategoryFilters = [...categoryOrder, 'uncategorized'] as const

interface StoredPlanExpansionState {
  version: number
  expandedPhaseIds: string[]
  expandedCompletedPhaseIds: string[]
}

function expansionStorageKey(planId: string) {
  return `gotime:plan:${planId}:expansion`
}

function scrollStorageKey(planId: string) {
  return `gotime:plan:${planId}:scroll`
}

function filterStorageKey(planId: string) {
  return `gotime:plan:${planId}:filters`
}

function readCategoryFilters(planId: string) {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(filterStorageKey(planId)) ?? 'null') as { version?: unknown; categories?: unknown } | null
    if (parsed?.version !== planFilterStateVersion || !Array.isArray(parsed.categories)) return new Set<CategoryFilter>()
    const categories = parsed.categories as unknown[]
    if (
      !categories.every((value) => typeof value === 'string' && allCategoryFilters.includes(value as CategoryFilter))
      || new Set(categories).size !== categories.length
    ) return new Set<CategoryFilter>()
    return new Set<CategoryFilter>(allCategoryFilters.filter((category) => categories.includes(category)))
  } catch {
    return new Set<CategoryFilter>()
  }
}

function writeCategoryFilters(planId: string, filters: Set<CategoryFilter>) {
  try {
    sessionStorage.setItem(filterStorageKey(planId), JSON.stringify({
      version: planFilterStateVersion,
      categories: allCategoryFilters.filter((category) => filters.has(category)),
    }))
  } catch {
    // Filtering remains usable when browser storage is unavailable.
  }
}

function readScrollPosition(planId: string) {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(scrollStorageKey(planId)) ?? 'null') as { version?: unknown; y?: unknown } | null
    if (parsed?.version !== planScrollStateVersion || typeof parsed.y !== 'number' || !Number.isFinite(parsed.y) || parsed.y < 0) return null
    return parsed.y
  } catch {
    return null
  }
}

function writeScrollPosition(planId: string, y: number) {
  try {
    sessionStorage.setItem(scrollStorageKey(planId), JSON.stringify({ version: planScrollStateVersion, y: Math.max(0, y) }))
  } catch {
    // Plan navigation remains usable when browser storage is unavailable.
  }
}

function readExpansionState(planId: string, validPhaseIds: Set<string>) {
  try {
    const value = sessionStorage.getItem(expansionStorageKey(planId))
    if (!value) return { phases: new Set<string>(), completed: new Set<string>() }
    const parsed = JSON.parse(value) as Partial<StoredPlanExpansionState>
    if (
      parsed.version !== planExpansionStateVersion
      || !Array.isArray(parsed.expandedPhaseIds)
      || !Array.isArray(parsed.expandedCompletedPhaseIds)
      || !parsed.expandedPhaseIds.every((id) => typeof id === 'string')
      || !parsed.expandedCompletedPhaseIds.every((id) => typeof id === 'string')
    ) {
      return { phases: new Set<string>(), completed: new Set<string>() }
    }
    return {
      phases: new Set(parsed.expandedPhaseIds.filter((id) => validPhaseIds.has(id))),
      completed: new Set(parsed.expandedCompletedPhaseIds.filter((id) => validPhaseIds.has(id))),
    }
  } catch {
    return { phases: new Set<string>(), completed: new Set<string>() }
  }
}

interface TaskDraft {
  title: string
  description: string
  phaseId: string
  categories: TaskCategory[]
  status: TaskStatus
  assignees: string
  startDate: string
  dueDate: string
  priority: TaskPriority
  dependencies: string[]
  parentTaskId: string
  subtaskPosition: string
}

function emptyDraft(phaseId: string): TaskDraft {
  return {
    title: '',
    description: '',
    phaseId,
    categories: [],
    status: 'not_started',
    assignees: '',
    startDate: '',
    dueDate: '',
    priority: 'medium',
    dependencies: [],
    parentTaskId: '',
    subtaskPosition: '',
  }
}

function draftFromTask(task: RelocationTask): TaskDraft {
  return {
    title: task.title,
    description: task.description ?? '',
    phaseId: task.phase_id,
    categories: [...task.categories],
    status: task.status,
    assignees: task.assignees.join(', '),
    startDate: task.start_date ?? '',
    dueDate: task.due_date ?? '',
    priority: task.priority,
    dependencies: [...task.dependency_task_ids],
    parentTaskId: task.parent_task_id ?? '',
    subtaskPosition: task.subtask_position?.toString() ?? '',
  }
}

function writeFromDraft(draft: TaskDraft): TaskWrite {
  return {
    title: draft.title.trim(),
    description: draft.description.trim() || null,
    phase_id: draft.phaseId,
    categories: categoryOrder.filter((category) => draft.categories.includes(category)),
    status: draft.status,
    assignees: draft.assignees.split(',').map((name) => name.trim()).filter(Boolean),
    start_date: draft.startDate || null,
    due_date: draft.dueDate || null,
    priority: draft.priority,
    dependency_task_ids: draft.dependencies,
    parent_task_id: draft.parentTaskId || null,
    subtask_position: draft.parentTaskId && draft.subtaskPosition !== '' ? Number(draft.subtaskPosition) : null,
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

function CategoryLabels({ categories }: { categories: TaskCategory[] }) {
  if (categories.length === 0) {
    return <span className="text-muted">Uncategorized</span>
  }
  return (
    <span className="task-category-labels d-inline-flex flex-wrap gap-1">
      {categoryOrder.filter((category) => categories.includes(category)).map((category) => (
        <Badge bg="light" text="dark" key={category}>{categoryLabels[category]}</Badge>
      ))}
    </span>
  )
}

interface PersistentCategoryDropdownProps {
  children: ReactNode
  id: string
  onInteraction?: () => void
  toggleAriaLabel?: string
  toggleClassName?: string
  toggleLabel: ReactNode
}

function PersistentCategoryDropdown({
  children,
  id,
  onInteraction,
  toggleAriaLabel,
  toggleClassName,
  toggleLabel,
}: PersistentCategoryDropdownProps) {
  const [show, setShow] = useState(false)
  const toggleRef = useRef<HTMLButtonElement>(null)

  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key !== 'Escape' || !show) return
    event.preventDefault()
    event.stopPropagation()
    setShow(false)
    toggleRef.current?.focus()
  }

  return (
    <Dropdown
      autoClose="outside"
      onKeyDown={handleKeyDown}
      onToggle={(nextShow) => {
        onInteraction?.()
        setShow(nextShow)
      }}
      show={show}
    >
      <Dropdown.Toggle
        aria-label={toggleAriaLabel}
        className={toggleClassName}
        id={id}
        ref={toggleRef}
        variant="outline-secondary"
      >
        {toggleLabel}
      </Dropdown.Toggle>
      <Dropdown.Menu className="category-menu p-3">{children}</Dropdown.Menu>
    </Dropdown>
  )
}

function taskMatchesCategoryFilters(
  task: RelocationTask,
  filters: Set<CategoryFilter>,
) {
  return filters.size === 0
    || task.categories.some((category) => filters.has(category))
    || (task.categories.length === 0 && filters.has('uncategorized'))
}

export function RelocationPlan({ onPlanChanged }: { onPlanChanged?: () => void }) {
  const { closeFind, consumeTarget, isOpen: findIsOpen, setEditorOpen, target } = useFind()
  const [plan, setPlan] = useState<RelocationPlanData | null>(null)
  const [loading, setLoading] = useState(true)
  const [taskEditorSaving, setTaskEditorSaving] = useState(false)
  const [pendingTaskStatusIds, setPendingTaskStatusIds] = useState<Set<string>>(new Set())
  const [error, setError] = useState<string | null>(null)
  const [filterNotice, setFilterNotice] = useState<string | null>(null)
  const [taskTitleError, setTaskTitleError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState<TaskDraft | null>(null)
  const [dependencyQuery, setDependencyQuery] = useState('')
  const [expandedPhaseIds, setExpandedPhaseIds] = useState<Set<string>>(new Set())
  const [expandedCompletedPhaseIds, setExpandedCompletedPhaseIds] = useState<Set<string>>(new Set())
  const [expandedParentIds, setExpandedParentIds] = useState<Set<string>>(new Set())
  const [expansionStateReady, setExpansionStateReady] = useState(false)
  const [pendingNavigationTaskId, setPendingNavigationTaskId] = useState<string | null>(null)
  const [foundTaskId, setFoundTaskId] = useState<string | null>(null)
  const [categoryFilters, setCategoryFilters] = useState<Set<CategoryFilter>>(new Set())
  const [addMenuOpen, setAddMenuOpen] = useState(false)
  const [creationType, setCreationType] = useState<'task' | 'milestone' | 'decision' | null>(null)
  const [foundationEditorOpen, setFoundationEditorOpen] = useState(false)
  const addToggleRef = useRef<HTMLButtonElement>(null)
  const editorRef = useRef<HTMLDivElement>(null)
  const titleInputRef = useRef<HTMLInputElement>(null)
  const taskRefs = useRef(new Map<string, HTMLElement>())
  const initializedPlanIdRef = useRef<string | null>(null)
  const preFilterExpandedPhaseIdsRef = useRef<Set<string> | null>(null)
  const scrollRestoredRef = useRef(false)
  const scrollWriteFrameRef = useRef<number | null>(null)
  const lastPlanScrollYRef = useRef(0)
  const preCreationScrollYRef = useRef(0)

  const editorActive = Boolean(draft) || foundationEditorOpen || creationType !== null

  function acceptPlan(updated: RelocationPlanData) {
    setPlan({ ...updated, milestones: updated.milestones ?? [], decisions: updated.decisions ?? [] })
  }

  useEffect(() => {
    const controller = new AbortController()
    fetchRelocationPlan(controller.signal)
      .then(acceptPlan)
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

  useEffect(() => {
    setEditorOpen(editorActive)
    return () => setEditorOpen(false)
  }, [editorActive, setEditorOpen])

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
  const categoryMatches = (task: RelocationTask) => (
    taskMatchesCategoryFilters(task, categoryFilters)
  )

  useEffect(() => {
    if (!plan || initializedPlanIdRef.current === plan.id) return
    const validPhaseIds = new Set(plan.phases.map((phase) => phase.id))
    const stored = readExpansionState(plan.id, validPhaseIds)
    const storedFilters = readCategoryFilters(plan.id)
    const matching = new Set(plan.tasks
      .filter((task) => taskMatchesCategoryFilters(task, storedFilters))
      .map((task) => task.phase_id))
    initializedPlanIdRef.current = plan.id
    preFilterExpandedPhaseIdsRef.current = storedFilters.size > 0 ? new Set(stored.phases) : null
    setCategoryFilters(storedFilters)
    setExpandedPhaseIds(storedFilters.size > 0 ? new Set([...stored.phases, ...matching]) : stored.phases)
    setExpandedCompletedPhaseIds(stored.completed)
    setExpansionStateReady(true)
  }, [plan])

  useEffect(() => {
    if (!plan || !expansionStateReady || initializedPlanIdRef.current !== plan.id) return
    const stored: StoredPlanExpansionState = {
      version: planExpansionStateVersion,
      expandedPhaseIds: [...(
        categoryFilters.size > 0
          ? preFilterExpandedPhaseIdsRef.current ?? new Set<string>()
          : expandedPhaseIds
      )],
      expandedCompletedPhaseIds: [...expandedCompletedPhaseIds],
    }
    try {
      sessionStorage.setItem(expansionStorageKey(plan.id), JSON.stringify(stored))
    } catch {
      // Expansion remains usable when browser storage is unavailable.
    }
  }, [categoryFilters, expandedCompletedPhaseIds, expandedPhaseIds, expansionStateReady, plan])

  useEffect(() => {
    if (!plan || !expansionStateReady || initializedPlanIdRef.current !== plan.id) return
    writeCategoryFilters(plan.id, categoryFilters)
  }, [categoryFilters, expansionStateReady, plan])

  useEffect(() => {
    if (!plan) return
    const key = `gotime:plan:${plan.id}:subtasks`
    try {
      const parsed = JSON.parse(sessionStorage.getItem(key) ?? '[]') as unknown
      if (Array.isArray(parsed)) setExpandedParentIds(new Set(parsed.filter((id): id is string => typeof id === 'string')))
    } catch { /* Subtask expansion remains usable without storage. */ }
  }, [plan?.id])

  useEffect(() => {
    if (!plan) return
    try { sessionStorage.setItem(`gotime:plan:${plan.id}:subtasks`, JSON.stringify([...expandedParentIds])) } catch { /* bounded session state only */ }
  }, [expandedParentIds, plan?.id])

  useLayoutEffect(() => {
    if (!plan || !expansionStateReady || scrollRestoredRef.current || target) return
    scrollRestoredRef.current = true
    const storedY = readScrollPosition(plan.id)
    if (storedY === null) return
    const maximumY = Math.max(0, document.documentElement.scrollHeight - window.innerHeight)
    const restoredY = Math.min(storedY, maximumY)
    lastPlanScrollYRef.current = restoredY
    window.scrollTo({ top: restoredY, left: 0, behavior: 'auto' })
  }, [expandedCompletedPhaseIds, expandedPhaseIds, expansionStateReady, plan, target])

  useLayoutEffect(() => {
    if (!plan || !expansionStateReady) return
    function saveBoundedScroll() {
      lastPlanScrollYRef.current = Math.max(0, window.scrollY)
      if (scrollWriteFrameRef.current !== null) return
      scrollWriteFrameRef.current = window.requestAnimationFrame(() => {
        scrollWriteFrameRef.current = null
        writeScrollPosition(plan!.id, lastPlanScrollYRef.current)
      })
    }
    window.addEventListener('scroll', saveBoundedScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', saveBoundedScroll)
      if (scrollWriteFrameRef.current !== null) window.cancelAnimationFrame(scrollWriteFrameRef.current)
      scrollWriteFrameRef.current = null
      writeScrollPosition(plan.id, lastPlanScrollYRef.current)
    }
  }, [expansionStateReady, plan])

  useLayoutEffect(() => {
    if (!plan || !expansionStateReady) return
    function saveCurrentPosition() {
      lastPlanScrollYRef.current = Math.max(0, window.scrollY)
      writeScrollPosition(plan!.id, lastPlanScrollYRef.current)
    }
    function saveTopPosition() {
      lastPlanScrollYRef.current = 0
      writeScrollPosition(plan!.id, 0)
    }
    window.addEventListener(savePlanPositionEvent, saveCurrentPosition)
    window.addEventListener(returnPlanToTopEvent, saveTopPosition)
    return () => {
      window.removeEventListener(savePlanPositionEvent, saveCurrentPosition)
      window.removeEventListener(returnPlanToTopEvent, saveTopPosition)
    }
  }, [expansionStateReady, plan])

  useEffect(() => {
    if (!filterNotice) return
    const timeout = window.setTimeout(() => setFilterNotice(null), 6000)
    return () => window.clearTimeout(timeout)
  }, [filterNotice])

  useEffect(() => {
    if (findIsOpen) setFilterNotice(null)
  }, [findIsOpen])

  useEffect(() => {
    if (!draft) return
    editorRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
    titleInputRef.current?.focus()
  }, [draft !== null, editingId])

  useEffect(() => {
    if (!pendingNavigationTaskId) return
    const taskElement = taskRefs.current.get(pendingNavigationTaskId)
    if (!taskElement) return
    taskElement.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
    taskElement.focus({ preventScroll: true })
    if (plan) {
      window.requestAnimationFrame(() => {
        lastPlanScrollYRef.current = Math.max(0, window.scrollY)
        writeScrollPosition(plan.id, lastPlanScrollYRef.current)
      })
    }
    setPendingNavigationTaskId(null)
  }, [expandedCompletedPhaseIds, expandedPhaseIds, pendingNavigationTaskId, plan])

  function matchingPhaseIds(filters: Set<CategoryFilter>) {
    if (!plan) return new Set<string>()
    return new Set(plan.tasks
      .filter((task) => taskMatchesCategoryFilters(task, filters))
      .map((task) => task.phase_id))
  }

  function updateCategoryFilters(next: Set<CategoryFilter>) {
    setFilterNotice(null)
    const filterWasActive = categoryFilters.size > 0
    const filterWillBeActive = next.size > 0
    if (!filterWasActive && filterWillBeActive) {
      preFilterExpandedPhaseIdsRef.current = new Set(expandedPhaseIds)
    }
    if (filterWillBeActive) {
      const matching = matchingPhaseIds(next)
      setExpandedPhaseIds((expanded) => new Set([...expanded, ...matching]))
    } else if (filterWasActive) {
      setExpandedPhaseIds(new Set(preFilterExpandedPhaseIdsRef.current ?? []))
      preFilterExpandedPhaseIdsRef.current = null
    }
    setCategoryFilters(next)
  }

  function togglePhase(phaseId: string) {
    setExpandedPhaseIds((expanded) => {
      const next = new Set(expanded)
      if (next.has(phaseId)) next.delete(phaseId)
      else next.add(phaseId)
      return next
    })
  }

  function selectFinderResult(task: RelocationTask) {
    setFilterNotice(null)
    if (!taskMatchesCategoryFilters(task, categoryFilters)) {
      const restored = preFilterExpandedPhaseIdsRef.current ?? new Set<string>()
      setExpandedPhaseIds(new Set([...restored, task.phase_id]))
      preFilterExpandedPhaseIdsRef.current = null
      setCategoryFilters(new Set())
      setFilterNotice(`Category filter cleared to show “${task.title}.”`)
    } else {
      setExpandedPhaseIds((expanded) => new Set(expanded).add(task.phase_id))
    }
    setFoundTaskId(task.id)
    if (task.parent_task_id) setExpandedParentIds((expanded) => new Set(expanded).add(task.parent_task_id!))
    if (task.is_parent) setExpandedParentIds((expanded) => new Set(expanded).add(task.id))
    if (task.status === 'completed') {
      setExpandedCompletedPhaseIds((expanded) => {
        const next = new Set(expanded)
        next.add(task.phase_id)
        return next
      })
    }
    setPendingNavigationTaskId(task.id)
  }

  useEffect(() => {
    if (!target || !plan || !expansionStateReady) return
    const task = plan.tasks.find((candidate) => candidate.id === target.taskId)
    scrollRestoredRef.current = true
    if (task) selectFinderResult(task)
    else if (target.source === 'recommendation') {
      setFilterNotice('The recommended task is no longer available.')
    }
    consumeTarget()
  }, [consumeTarget, expansionStateReady, plan, target])

  function beginCreation(type: 'task' | 'milestone' | 'decision') {
    if (!plan || editorActive) return
    closeFind()
    setAddMenuOpen(false)
    preCreationScrollYRef.current = Math.max(0, window.scrollY)
    setCreationType(type)
    setFilterNotice(null)
    setError(null)
    setTaskTitleError(null)
    if (type !== 'task') return
    setEditingId(null)
    setDraft(emptyDraft(plan.phases[0].id))
    setDependencyQuery('')
  }

  function beginSubtask(parent: RelocationTask) {
    if (!plan || editorActive) return
    closeFind()
    preCreationScrollYRef.current = Math.max(0, window.scrollY)
    setCreationType('task')
    setEditingId(null)
    const next = emptyDraft(parent.phase_id)
    next.parentTaskId = parent.id
    next.subtaskPosition = String(parent.subtask_count ?? 0)
    setDraft(next)
    setFilterNotice(null)
    setError(null)
    setTaskTitleError(null)
  }

  function cancelCreation() {
    const restoreY = preCreationScrollYRef.current
    setCreationType(null)
    setDraft(null)
    setEditingId(null)
    setDependencyQuery('')
    window.requestAnimationFrame(() => {
      window.scrollTo({ top: restoreY, left: 0, behavior: 'auto' })
      lastPlanScrollYRef.current = restoreY
      if (plan) writeScrollPosition(plan.id, restoreY)
      addToggleRef.current?.focus()
    })
  }

  function beginEdit(task: RelocationTask) {
    setEditingId(task.id)
    setDraft(draftFromTask(task))
    setDependencyQuery('')
    setError(null)
    setTaskTitleError(null)
  }

  async function saveTask() {
    if (!draft || taskEditorSaving) return
    if (plan && hasDuplicatePlanItemTitle(plan.tasks, draft.title, editingId)) {
      setError(null)
      setTaskTitleError('A task with this title already exists in this plan.')
      titleInputRef.current?.focus()
      return
    }
    setTaskEditorSaving(true)
    setError(null)
    try {
      const write = writeFromDraft(draft)
      const createdId = editingId ?? generateTaskId(write.title)
      const updated = editingId
        ? await replaceTask(editingId, write)
        : await createTask(createdId, write)
      acceptPlan(updated)
      let parentStatusNotice: string | null = null
      if (write.parent_task_id) {
        const parent = updated.tasks.find((task) => task.id === write.parent_task_id)
        if (parent?.subtask_count === 1) {
          parentStatusNotice = `“${parent.title}” is now ${statusLabels[parent.status].toLowerCase()} because its status is derived from required subtasks.`
        }
      }
      onPlanChanged?.()
      setDraft(null)
      setEditingId(null)
      if (!editingId) {
        setCreationType(null)
        const createdTask = updated.tasks.find((task) => task.id === createdId)
        if (createdTask) selectFinderResult(createdTask)
      }
      if (parentStatusNotice) setFilterNotice(parentStatusNotice)
    } catch (requestError) {
      if (requestError instanceof PlanRequestError && requestError.code === 'duplicate_task_title') {
        setTaskTitleError(requestError.message)
        titleInputRef.current?.focus()
      } else if (editingId && requestError instanceof PlanRequestError && requestError.code === 'parent_phase_move_confirmation_required' && window.confirm(requestError.message)) {
        const updated = await replaceTask(editingId, { ...writeFromDraft(draft), confirm_parent_phase_move: true })
        acceptPlan(updated)
        setDraft(null)
        setEditingId(null)
      } else {
        setError(requestError instanceof Error ? requestError.message : 'Unable to save the task.')
      }
    } finally {
      setTaskEditorSaving(false)
    }
  }

  async function updateStatus(task: RelocationTask, status: TaskStatus) {
    setPendingTaskStatusIds((current) => new Set(current).add(task.id))
    setError(null)
    try {
      acceptPlan(await changeTaskStatus(task.id, status))
      onPlanChanged?.()
    } catch (requestError) {
      if (requestError instanceof PlanRequestError && requestError.code === 'parent_status_override_confirmation_required' && window.confirm(requestError.message)) {
        try {
          acceptPlan(await changeTaskStatus(task.id, status, true))
          onPlanChanged?.()
        } catch (confirmedError) {
          setError(confirmedError instanceof Error ? confirmedError.message : 'Unable to update task status.')
        }
      } else setError(requestError instanceof Error ? requestError.message : 'Unable to update task status.')
    } finally {
      setPendingTaskStatusIds((current) => {
        const next = new Set(current)
        next.delete(task.id)
        return next
      })
    }
  }

  async function returnToAutomaticStatus(task: RelocationTask) {
    setError(null)
    try { acceptPlan(await returnParentToAutomaticStatus(task.id)) }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Unable to restore automatic status.') }
  }

  function renderTask(task: RelocationTask, isSubtask = false) {
    const titleId = `task-title-${task.id}`
    return (
      <article
        aria-labelledby={titleId}
        className={`task-item rounded-3 p-2 p-sm-3 ${isSubtask ? 'is-subtask' : ''} ${task.blocked ? 'is-blocked' : ''} ${foundTaskId === task.id ? 'is-found' : ''}`}
        id={`task-${task.id}`}
        key={task.id}
        ref={(element) => {
          if (element) taskRefs.current.set(task.id, element)
          else taskRefs.current.delete(task.id)
        }}
        tabIndex={-1}
      >
        <div className="task-card-layout d-flex flex-wrap justify-content-between gap-2 gap-sm-3">
          <div>
            <div className="task-heading-row d-flex flex-wrap align-items-center gap-1 gap-sm-2 mb-1"><h4 className="task-title mb-0" id={titleId}>{task.title}</h4>{task.blocked && <Badge bg="warning" text="dark">Blocked</Badge>}{task.manual_status_override && <Badge bg="info" text="dark">Manual status</Badge>}<Badge bg="light" text="dark">{priorityLabels[task.priority]}</Badge></div>
            {task.parent_task_id && <p className="small text-muted mb-1">Part of: {taskById.get(task.parent_task_id)?.title ?? task.parent_task_id}</p>}
            {task.is_parent && <p className="small fw-semibold mb-1">{task.completed_subtask_count ?? 0} of {task.subtask_count ?? 0} subtasks completed</p>}
            <div className="task-metadata d-flex flex-wrap align-items-center gap-1 gap-sm-2 mb-2"><CategoryLabels categories={task.categories} /><span className="text-muted">{task.assignees.length > 0 ? task.assignees.join(', ') : 'Unassigned'}{task.due_date ? ` · Due ${task.due_date}` : ''}</span></div>
            {task.description && <p className="mb-2">{task.description}</p>}
            {task.dependency_task_ids.length > 0 && <p className="dependency-context mb-0"><strong>Depends on:</strong> {task.dependency_task_ids.map((id) => taskById.get(id)?.title ?? id).join(', ')}</p>}
          </div>
          <div className="task-actions d-flex flex-wrap align-items-start gap-2">
            <Form.Select aria-label={`Status for ${task.title}`} disabled={pendingTaskStatusIds.has(task.id)} value={task.status} onChange={(event) => void updateStatus(task, event.target.value as TaskStatus)}>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Form.Select>
            {task.is_parent && <Button variant="outline-primary" onClick={() => beginSubtask(task)}>Add subtask</Button>}
            {task.manual_status_override && <Button variant="outline-secondary" onClick={() => void returnToAutomaticStatus(task)}>Return to automatic status</Button>}
            <Button variant="outline-secondary" onClick={() => beginEdit(task)}>Edit</Button>
          </div>
        </div>
      </article>
    )
  }

  function renderTaskGroup(task: RelocationTask, phaseTasks: RelocationTask[]) {
    if (!task.is_parent) return renderTask(task)
    const subtasks = phaseTasks
      .filter((candidate) => candidate.parent_task_id === task.id)
      .sort((left, right) => (left.subtask_position ?? 0) - (right.subtask_position ?? 0) || left.id.localeCompare(right.id))
    const expanded = expandedParentIds.has(task.id)
    return <div className="parent-task-group" key={task.id}>
      <div className="d-flex align-items-center gap-2 mb-1">
        <Button aria-expanded={expanded} className="subtask-toggle" onClick={() => setExpandedParentIds((current) => { const next = new Set(current); if (next.has(task.id)) next.delete(task.id); else next.add(task.id); return next })} size="sm" variant="link">{expanded ? 'Hide' : 'Show'} subtasks</Button>
      </div>
      {renderTask(task)}
      {expanded && <Stack className="subtask-list gap-1 gap-sm-2 mt-2">{subtasks.map((subtask) => renderTask(subtask, true))}</Stack>}
    </div>
  }

  return (
    <>
    <header className="plan-page-heading d-flex flex-wrap align-items-start justify-content-between gap-2 px-2 px-sm-0 pt-0 pt-sm-4 mb-3">
      <div>
        <p className="section-label mb-1">Plan</p>
        <h1 className="detail-heading mb-0">Family plan</h1>
      </div>
      {plan && (
        <Dropdown
          align="end"
          autoClose
          className="plan-add-menu"
          onKeyDown={(event) => {
            if (event.key !== 'Escape' || !addMenuOpen) return
            event.preventDefault()
            event.stopPropagation()
            setAddMenuOpen(false)
            addToggleRef.current?.focus()
          }}
          onToggle={(show) => {
            if (show && !editorActive) {
              closeFind()
              setFilterNotice(null)
            }
            setAddMenuOpen(show && !editorActive)
          }}
          show={addMenuOpen}
        >
          <Dropdown.Toggle className="plan-add-toggle" disabled={editorActive} id="plan-add" ref={addToggleRef}>Add</Dropdown.Toggle>
          <Dropdown.Menu aria-label="Add to Plan" className="plan-add-menu-list p-1" role="menu">
            <Dropdown.Item as="button" onClick={() => beginCreation('task')} role="menuitem">
              <strong className="d-block">Task</strong>
              <span className="d-block text-muted">Something that needs to be done</span>
            </Dropdown.Item>
            <Dropdown.Item as="button" onClick={() => beginCreation('milestone')} role="menuitem">
              <strong className="d-block">Milestone</strong>
              <span className="d-block text-muted">An important outcome or moment</span>
            </Dropdown.Item>
            <Dropdown.Item as="button" disabled={plan.milestones.length === 0} onClick={() => beginCreation('decision')} role="menuitem">
              <strong className="d-block">Decision</strong>
              <span className="d-block text-muted">A choice that needs to be made</span>
            </Dropdown.Item>
          </Dropdown.Menu>
        </Dropdown>
      )}
    </header>
    <section className="relocation-plan mt-3" aria-labelledby="relocation-plan-heading">
      <div className="plan-heading d-flex flex-wrap align-items-center justify-content-between gap-3 px-2 px-sm-0 mb-3">
        <div>
          <p className="section-label mb-1">Persistent plan</p>
          <h2 className="detail-heading mb-0" id="relocation-plan-heading">
            {plan?.title ?? 'Family relocation plan'}
          </h2>
        </div>
      </div>

      {loading && <div className="py-4 text-center" role="status"><Spinner size="sm" /> <span>Loading relocation plan…</span></div>}
      {error && <Alert variant="danger">{error}</Alert>}
      {filterNotice && (
        <Alert
          className="filter-clear-notice position-fixed start-50 translate-middle-x mb-3 shadow-sm"
          dismissible
          onClose={() => setFilterNotice(null)}
          role="status"
          variant="info"
        >
          {filterNotice}
        </Alert>
      )}

      {plan && !draft && <MilestoneDecisionFoundation
        creationType={creationType === 'milestone' || creationType === 'decision' ? creationType : null}
        onCreationCanceled={cancelCreation}
        onCreationSaved={() => setCreationType(null)}
        onEditorOpenChange={setFoundationEditorOpen}
        onItemRevealed={() => {
          window.requestAnimationFrame(() => {
            lastPlanScrollYRef.current = Math.max(0, window.scrollY)
            writeScrollPosition(plan.id, lastPlanScrollYRef.current)
          })
        }}
        onPlanUpdated={acceptPlan}
        plan={plan}
      />}

      {plan && !draft && (
        <div className="task-discovery px-2 px-sm-0 mb-3">
        <PersistentCategoryDropdown
          id="category-filter"
          onInteraction={() => setFilterNotice(null)}
          toggleAriaLabel="Filter by categories"
          toggleLabel={`Categories${categoryFilters.size > 0 ? ` (${categoryFilters.size})` : ''}`}
        >
          {categoryOrder.map((category) => (
            <Form.Check
              checked={categoryFilters.has(category)}
              id={`category-filter-${category}`}
              key={category}
              label={categoryLabels[category]}
              onChange={(event) => {
                const next = new Set(categoryFilters)
                if (event.target.checked) next.add(category)
                else next.delete(category)
                updateCategoryFilters(next)
              }}
            />
          ))}
          <Form.Check
            checked={categoryFilters.has('uncategorized')}
            id="category-filter-uncategorized"
            label="Uncategorized"
            onChange={(event) => {
              const next = new Set(categoryFilters)
              if (event.target.checked) next.add('uncategorized')
              else next.delete('uncategorized')
              updateCategoryFilters(next)
            }}
          />
          {categoryFilters.size > 0 && <Button className="mt-2 p-0" variant="link" type="button" onClick={() => updateCategoryFilters(new Set())}>Clear all</Button>}
        </PersistentCategoryDropdown>
        </div>
      )}

      {draft && plan && (
        <div ref={editorRef}>
          <Card className="task-editor mb-4">
            <Card.Body>
              <Card.Title as="h3">{editingId ? 'Edit task' : 'Add task'}</Card.Title>
              <Form onSubmit={(event) => { event.preventDefault(); void saveTask() }}>
              <Stack direction="horizontal" gap={2} className="task-editor-actions sticky-top flex-wrap py-3 mb-3">
                <Button type="submit" disabled={taskEditorSaving}>
                  {taskEditorSaving ? (editingId ? 'Saving…' : 'Creating…') : (editingId ? 'Save changes' : 'Create task')}
                </Button>
                <Button type="button" variant="outline-secondary" disabled={taskEditorSaving} onClick={() => {
                  if (!editingId && creationType === 'task') cancelCreation()
                  else { setDraft(null); setEditingId(null); setDependencyQuery('') }
                }}>Cancel</Button>
              </Stack>
              <Row className="g-3">
                <Col md={8}><Form.Group controlId="task-title"><Form.Label>Title</Form.Label><Form.Control aria-describedby="task-title-error" aria-invalid={Boolean(taskTitleError)} isInvalid={Boolean(taskTitleError)} ref={titleInputRef} required maxLength={200} value={draft.title} onChange={(event) => { const title = event.target.value; setDraft({ ...draft, title }); setTaskTitleError(plan && hasDuplicatePlanItemTitle(plan.tasks, title, editingId) ? 'A task with this title already exists in this plan.' : null) }} /><Form.Control.Feedback id="task-title-error" type="invalid">{taskTitleError}</Form.Control.Feedback></Form.Group></Col>
                <Col md={4}><Form.Group controlId="task-phase"><Form.Label>Phase</Form.Label><Form.Select disabled={Boolean(draft.parentTaskId)} value={draft.phaseId} onChange={(event) => setDraft({ ...draft, phaseId: event.target.value })}>{plan.phases.map((phase) => <option key={phase.id} value={phase.id}>{phase.title}</option>)}</Form.Select></Form.Group></Col>
                <Col md={8}><Form.Group controlId="task-parent"><Form.Label>Part of <span className="text-muted">(optional)</span></Form.Label><Form.Select disabled={Boolean(editingId && plan.tasks.find((task) => task.id === editingId)?.is_parent)} value={draft.parentTaskId} onChange={(event) => { const parentTaskId = event.target.value; const parent = plan.tasks.find((task) => task.id === parentTaskId); setDraft({ ...draft, parentTaskId, phaseId: parent?.phase_id ?? draft.phaseId, subtaskPosition: parentTaskId ? draft.subtaskPosition || String(parent?.subtask_count ?? 0) : '' }) }}><option value="">Not a subtask</option>{plan.tasks.filter((task) => !task.parent_task_id && task.id !== editingId).map((task) => <option key={task.id} value={task.id}>{task.title}</option>)}</Form.Select></Form.Group></Col>
                {draft.parentTaskId && <Col md={4}><Form.Group controlId="task-subtask-position"><Form.Label>Subtask order</Form.Label><Form.Control min={0} type="number" value={draft.subtaskPosition} onChange={(event) => setDraft({ ...draft, subtaskPosition: event.target.value })} /></Form.Group></Col>}
                <Col xs={12}><Form.Group controlId="task-description"><Form.Label>Description <span className="text-muted">(optional)</span></Form.Label><Form.Control as="textarea" rows={2} maxLength={2000} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></Form.Group></Col>
                <Col md={4}>
                  <Form.Group controlId="task-categories">
                    <Form.Label>Categories (optional)</Form.Label>
                    <PersistentCategoryDropdown
                      id="task-categories"
                      toggleClassName="category-select-toggle text-start w-100"
                      toggleLabel={draft.categories.length > 0 ? categoryOrder.filter((category) => draft.categories.includes(category)).map((category) => categoryLabels[category]).join(', ') : 'Select categories'}
                    >
                      {categoryOrder.map((category) => (
                        <Form.Check
                          checked={draft.categories.includes(category)}
                          id={`task-category-${category}`}
                          key={category}
                          label={categoryLabels[category]}
                          onChange={(event) => setDraft({
                            ...draft,
                            categories: event.target.checked
                              ? categoryOrder.filter((item) => item === category || draft.categories.includes(item))
                              : draft.categories.filter((item) => item !== category),
                          })}
                        />
                      ))}
                      {draft.categories.length > 0 && <Button className="mt-2 p-0" variant="link" type="button" onClick={() => setDraft({ ...draft, categories: [] })}>Clear all</Button>}
                    </PersistentCategoryDropdown>
                  </Form.Group>
                </Col>
                <Col md={4}><Form.Group controlId="task-priority"><Form.Label>Priority</Form.Label><Form.Select value={draft.priority} onChange={(event) => setDraft({ ...draft, priority: event.target.value as TaskPriority })}>{Object.entries(priorityLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Form.Select></Form.Group></Col>
                <Col md={4}><Form.Group controlId="task-status"><Form.Label>Status</Form.Label><Form.Select disabled={Boolean(editingId && plan.tasks.find((task) => task.id === editingId)?.is_parent)} value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value as TaskStatus })}>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Form.Select></Form.Group></Col>
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

      {plan && categoryFilters.size > 0 && !plan.tasks.some(categoryMatches) && (
        <p className="text-muted py-4 mb-0">No tasks match the selected categories.</p>
      )}

      {plan && (
        <div className="phase-list-heading d-flex flex-wrap align-items-center justify-content-between gap-2 px-1 px-sm-0 mb-2">
          <h3 className="h5 mb-0" id="task-phases-heading">Task phases</h3>
          <div className="d-flex flex-wrap gap-2" aria-label="Phase display controls">
            <Button
              className="phase-display-control"
              onClick={() => setExpandedPhaseIds(new Set(plan.phases
                .filter((phase) => categoryFilters.size === 0 || plan.tasks.some((task) => task.phase_id === phase.id && categoryMatches(task)))
                .map((phase) => phase.id)))}
              size="sm"
              type="button"
              variant="outline-secondary"
            >
              Expand all
            </Button>
            <Button
              className="phase-display-control"
              onClick={() => {
                setExpandedPhaseIds(new Set())
                setExpandedCompletedPhaseIds(new Set())
              }}
              size="sm"
              type="button"
              variant="outline-secondary"
            >
              Collapse all
            </Button>
          </div>
        </div>
      )}

      {plan?.phases.map((phase) => {
        const allPhaseTasks = plan.tasks.filter((task) => task.phase_id === phase.id)
        const matchingIds = new Set(allPhaseTasks.filter(categoryMatches).map((task) => task.id))
        const visibleTopLevelTasks = allPhaseTasks.filter((task) => !task.parent_task_id && (
          categoryFilters.size === 0 || matchingIds.has(task.id)
          || allPhaseTasks.some((candidate) => candidate.parent_task_id === task.id && matchingIds.has(candidate.id))
        ))
        if (categoryFilters.size > 0 && visibleTopLevelTasks.length === 0) return null
        const countableTasks = allPhaseTasks.filter((task) => !task.is_parent && categoryMatches(task))
        const activeTasks = countableTasks.filter((task) => task.status !== 'completed')
        const completedTasks = countableTasks.filter((task) => task.status === 'completed')
        const groupCompleted = (task: RelocationTask) => task.status === 'completed' && (
          !task.is_parent || allPhaseTasks.filter((candidate) => candidate.parent_task_id === task.id).every((child) => child.status === 'completed')
        )
        const activeGroups = visibleTopLevelTasks.filter((task) => !groupCompleted(task))
        const completedGroups = visibleTopLevelTasks.filter(groupCompleted)
        const phaseExpanded = expandedPhaseIds.has(phase.id)
        const completedExpanded = expandedCompletedPhaseIds.has(phase.id)
        const bodyId = `phase-body-${phase.id}`
        return (
          <Card className="phase-card" key={phase.id}>
            <Card.Header aria-label={phase.title} as="h4" className="p-0">
              <button
                aria-controls={bodyId}
                aria-expanded={phaseExpanded}
                aria-label={`${phase.title} ${activeTasks.length} remaining · ${completedTasks.length} completed`}
                className="phase-toggle d-flex w-100 align-items-center justify-content-between gap-3 border-0 px-3 py-3 text-start"
                onClick={() => togglePhase(phase.id)}
                onKeyDown={(event) => {
                  if (event.key !== 'Enter' && event.key !== ' ') return
                  event.preventDefault()
                  togglePhase(phase.id)
                }}
                type="button"
              >
                <span>
                  <span className="phase-title d-block">{phase.title}</span>
                  <span className="phase-counts d-block fw-normal">{activeTasks.length} remaining · {completedTasks.length} completed</span>
                </span>
                <span aria-hidden="true" className={`phase-chevron flex-shrink-0 ${phaseExpanded ? 'is-expanded' : ''}`}>›</span>
              </button>
            </Card.Header>
            {phaseExpanded && <Card.Body className="px-1 py-2 p-sm-3" id={bodyId}>
              {visibleTopLevelTasks.length === 0 && <p className="text-muted mb-0">No tasks in this phase yet.</p>}
              {activeTasks.length === 0 && completedTasks.length > 0 && <p className="text-muted mb-0">No active tasks in this phase.</p>}
              <Stack className="task-list gap-1 gap-sm-3">
                {activeGroups.map((task) => renderTaskGroup(task, allPhaseTasks.filter((candidate) => categoryFilters.size === 0 || categoryMatches(candidate) || candidate.id === task.id)))}
              </Stack>
              {completedTasks.length > 0 && (
                <Accordion
                  activeKey={completedExpanded ? 'completed' : null}
                  className="completed-tasks mt-3"
                  onSelect={(eventKey) => {
                    setExpandedCompletedPhaseIds((expanded) => {
                      const next = new Set(expanded)
                      if (eventKey === 'completed') next.add(phase.id)
                      else next.delete(phase.id)
                      return next
                    })
                  }}
                >
                  <Accordion.Item eventKey="completed">
                    <Accordion.Header>Completed ({completedTasks.length})</Accordion.Header>
                    <Accordion.Body className="completed-task-list-body">
                      {completedExpanded && <Stack className="task-list gap-1 gap-sm-3">{completedGroups.map((task) => renderTaskGroup(task, allPhaseTasks.filter((candidate) => categoryFilters.size === 0 || categoryMatches(candidate) || candidate.id === task.id)))}</Stack>}
                    </Accordion.Body>
                  </Accordion.Item>
                </Accordion>
              )}
            </Card.Body>}
          </Card>
        )
      })}
    </section>
    </>
  )
}
