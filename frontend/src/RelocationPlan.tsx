import { type KeyboardEvent, type ReactNode, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Accordion, Alert, Badge, Button, Card, Col, Dropdown, Form, Modal, Row, Spinner, Stack } from 'react-bootstrap'
import {
  changeTaskStatus,
  createTask,
  fetchRelocationPlan,
  replaceTask,
  reorderSubtasks,
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
import { ExpansionChevron } from './ExpansionChevron'
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
  isSubtask: boolean
  parentTaskId: string
  subtaskPosition: string
  elapsedMin: string
  elapsedMax: string
  elapsedUnit: 'days' | 'weeks'
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
    isSubtask: false,
    parentTaskId: '',
    subtaskPosition: '',
    elapsedMin: '',
    elapsedMax: '',
    elapsedUnit: 'days',
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
    isSubtask: Boolean(task.parent_task_id),
    parentTaskId: task.parent_task_id ?? '',
    subtaskPosition: task.subtask_position?.toString() ?? '',
    elapsedMin: task.expected_elapsed_min_days?.toString() ?? '',
    elapsedMax: task.expected_elapsed_max_days?.toString() ?? '',
    elapsedUnit: 'days',
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
    parent_task_id: draft.isSubtask ? draft.parentTaskId || null : null,
    subtask_position: draft.isSubtask && draft.parentTaskId && draft.subtaskPosition !== '' ? Number(draft.subtaskPosition) : null,
    expected_elapsed_min_days: draft.elapsedMin === '' ? null : Number(draft.elapsedMin) * (draft.elapsedUnit === 'weeks' ? 7 : 1),
    expected_elapsed_max_days: draft.elapsedMax === '' ? null : Number(draft.elapsedMax) * (draft.elapsedUnit === 'weeks' ? 7 : 1),
  }
}

interface ConfirmationRequest {
  heading: string
  consequence: string
  confirmLabel: string
  action: () => Promise<void>
  returnFocus: HTMLElement | null
}

function requiredSubtaskText(count: number) {
  return `${count} required ${count === 1 ? 'subtask' : 'subtasks'}`
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
  const [hiddenSavedTaskId, setHiddenSavedTaskId] = useState<string | null>(null)
  const [taskTitleError, setTaskTitleError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState<TaskDraft | null>(null)
  const [dependencyQuery, setDependencyQuery] = useState('')
  const [expandedDependencyPhaseIds, setExpandedDependencyPhaseIds] = useState<Set<string>>(new Set())
  const [parentQuery, setParentQuery] = useState('')
  const [parentPickerOpen, setParentPickerOpen] = useState(false)
  const [parentError, setParentError] = useState<string | null>(null)
  const [confirmation, setConfirmation] = useState<ConfirmationRequest | null>(null)
  const [confirmationPending, setConfirmationPending] = useState(false)
  const [reorderingParentIds, setReorderingParentIds] = useState<Set<string>>(new Set())
  const [expandedPhaseIds, setExpandedPhaseIds] = useState<Set<string>>(new Set())
  const [expandedCompletedPhaseIds, setExpandedCompletedPhaseIds] = useState<Set<string>>(new Set())
  const [expandedParentIds, setExpandedParentIds] = useState<Set<string>>(new Set())
  const [expansionStateReady, setExpansionStateReady] = useState(false)
  const [pendingNavigation, setPendingNavigation] = useState<{ taskId: string; focus: 'card' | 'edit'; scroll: 'always' | 'if-needed' } | null>(null)
  const [foundTaskId, setFoundTaskId] = useState<string | null>(null)
  const [foundTaskFading, setFoundTaskFading] = useState(false)
  const [categoryFilters, setCategoryFilters] = useState<Set<CategoryFilter>>(new Set())
  const [addMenuOpen, setAddMenuOpen] = useState(false)
  const [creationType, setCreationType] = useState<'task' | 'milestone' | 'decision' | null>(null)
  const [foundationEditorOpen, setFoundationEditorOpen] = useState(false)
  const addToggleRef = useRef<HTMLButtonElement>(null)
  const editorRef = useRef<HTMLDivElement>(null)
  const titleInputRef = useRef<HTMLInputElement>(null)
  const taskRefs = useRef(new Map<string, HTMLElement>())
  const hiddenSavedTaskActionRef = useRef<HTMLButtonElement>(null)
  const moveButtonRefs = useRef(new Map<string, HTMLButtonElement>())
  const initializedPlanIdRef = useRef<string | null>(null)
  const preFilterExpandedPhaseIdsRef = useRef<Set<string> | null>(null)
  const scrollRestoredRef = useRef(false)
  const scrollWriteFrameRef = useRef<number | null>(null)
  const lastPlanScrollYRef = useRef(0)
  const preCreationScrollYRef = useRef(0)
  const editOriginRef = useRef<{ taskId: string; scrollY: number } | null>(null)

  const editorActive = Boolean(draft) || foundationEditorOpen || creationType !== null
  const elapsedMinimum = draft?.elapsedMin === '' ? null : Number(draft?.elapsedMin)
  const elapsedMaximum = draft?.elapsedMax === '' ? null : Number(draft?.elapsedMax)
  const elapsedMultiplier = draft?.elapsedUnit === 'weeks' ? 7 : 1
  const invalidElapsed = Boolean(draft && (
    (elapsedMinimum === null) !== (elapsedMaximum === null)
    || (elapsedMinimum !== null && (!Number.isInteger(elapsedMinimum) || elapsedMinimum < 0))
    || (elapsedMaximum !== null && (!Number.isInteger(elapsedMaximum) || elapsedMaximum < 0))
    || (elapsedMinimum !== null && elapsedMaximum !== null && elapsedMinimum > elapsedMaximum)
    || (elapsedMaximum !== null && elapsedMaximum * elapsedMultiplier > 3650)
  ))

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
  const dependencySearchActive = Boolean(dependencyQuery.trim())
  const categoryMatches = (task: RelocationTask) => (
    taskMatchesCategoryFilters(task, categoryFilters)
  )
  const eligibleParents = useMemo(() => {
    if (!plan || !draft) return []
    const query = parentQuery.trim().toLocaleLowerCase()
    return plan.tasks
      .filter((task) => (
        task.phase_id === draft.phaseId
        && !task.parent_task_id
        && task.id !== editingId
        && !((editingId && plan.tasks.find((candidate) => candidate.id === editingId)?.is_parent))
        && task.title.toLocaleLowerCase().includes(query)
      ))
      .sort((left, right) => left.title.localeCompare(right.title))
  }, [draft, editingId, parentQuery, plan])

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
    if (!pendingNavigation) return
    const taskElement = document.getElementById(`task-${pendingNavigation.taskId}`)
    if (!taskElement) return
    const focusElement = pendingNavigation.focus === 'edit'
      ? taskElement.querySelector<HTMLElement>('[data-task-edit-control]') ?? taskElement
      : taskElement
    const bounds = taskElement.getBoundingClientRect()
    const comfortablyVisible = bounds.top >= 72 && bounds.bottom <= window.innerHeight - 72
    if (pendingNavigation.scroll === 'always' || !comfortablyVisible) {
      const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
      taskElement.scrollIntoView?.({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' })
    }
    focusElement.focus({ preventScroll: true })
    if (plan) {
      window.requestAnimationFrame(() => {
        lastPlanScrollYRef.current = Math.max(0, window.scrollY)
        writeScrollPosition(plan.id, lastPlanScrollYRef.current)
      })
    }
    setPendingNavigation(null)
  }, [expandedCompletedPhaseIds, expandedParentIds, expandedPhaseIds, pendingNavigation, plan])

  useEffect(() => {
    if (!hiddenSavedTaskId) return
    const frame = window.requestAnimationFrame(() => hiddenSavedTaskActionRef.current?.focus())
    return () => window.cancelAnimationFrame(frame)
  }, [hiddenSavedTaskId])

  useEffect(() => {
    if (!foundTaskId) return
    const timeout = window.setTimeout(() => {
      const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
      if (reducedMotion) setFoundTaskId((current) => current === foundTaskId ? null : current)
      else setFoundTaskFading(true)
    }, 3000)
    return () => window.clearTimeout(timeout)
  }, [foundTaskId])

  useEffect(() => {
    if (!foundTaskId || !foundTaskFading) return
    const timeout = window.setTimeout(() => {
      setFoundTaskId((current) => current === foundTaskId ? null : current)
      setFoundTaskFading(false)
    }, 350)
    return () => window.clearTimeout(timeout)
  }, [foundTaskFading, foundTaskId])

  function highlightTask(taskId: string) {
    setFoundTaskFading(false)
    setFoundTaskId(taskId)
  }

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

  function revealTask(task: RelocationTask, focus: 'card' | 'edit' = 'card', scroll: 'always' | 'if-needed' = 'always') {
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
    highlightTask(task.id)
    if (task.parent_task_id) setExpandedParentIds((expanded) => new Set(expanded).add(task.parent_task_id!))
    if (task.is_parent) setExpandedParentIds((expanded) => new Set(expanded).add(task.id))
    if (task.status === 'completed') {
      setExpandedCompletedPhaseIds((expanded) => {
        const next = new Set(expanded)
        next.add(task.phase_id)
        return next
      })
    }
    setPendingNavigation({ taskId: task.id, focus, scroll })
  }

  function selectFinderResult(task: RelocationTask) {
    revealTask(task)
  }

  useEffect(() => {
    if (!target || !plan || !expansionStateReady) return
    if (target.decisionId) return
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
    setParentError(null)
    setParentPickerOpen(false)
    setParentQuery('')
    if (type !== 'task') return
    setEditingId(null)
    setDraft(emptyDraft(plan.phases[0].id))
    setDependencyQuery('')
    setExpandedDependencyPhaseIds(new Set())
  }

  function beginSubtask(parent: RelocationTask) {
    if (!plan || editorActive) return
    closeFind()
    preCreationScrollYRef.current = Math.max(0, window.scrollY)
    setCreationType('task')
    setEditingId(null)
    const next = emptyDraft(parent.phase_id)
    next.isSubtask = true
    next.parentTaskId = parent.id
    next.subtaskPosition = String(parent.subtask_count ?? 0)
    setDraft(next)
    setFilterNotice(null)
    setError(null)
    setTaskTitleError(null)
    setParentError(null)
    setParentPickerOpen(false)
    setParentQuery('')
    setDependencyQuery('')
    setExpandedDependencyPhaseIds(new Set())
  }

  function cancelCreation() {
    const restoreY = preCreationScrollYRef.current
    setCreationType(null)
    setDraft(null)
    setEditingId(null)
    setDependencyQuery('')
    setExpandedDependencyPhaseIds(new Set())
    setParentQuery('')
    setParentPickerOpen(false)
    setParentError(null)
    window.requestAnimationFrame(() => {
      window.scrollTo({ top: restoreY, left: 0, behavior: 'auto' })
      lastPlanScrollYRef.current = restoreY
      if (plan) writeScrollPosition(plan.id, restoreY)
      addToggleRef.current?.focus()
    })
  }

  function beginEdit(task: RelocationTask) {
    editOriginRef.current = { taskId: task.id, scrollY: Math.max(0, window.scrollY) }
    setFoundTaskId(null)
    setFoundTaskFading(false)
    setEditingId(task.id)
    setDraft(draftFromTask(task))
    setDependencyQuery('')
    setExpandedDependencyPhaseIds(new Set(plan?.tasks
      .filter((candidate) => task.dependency_task_ids.includes(candidate.id))
      .map((candidate) => candidate.phase_id) ?? []))
    setError(null)
    setTaskTitleError(null)
    setParentError(null)
    setParentPickerOpen(false)
    setParentQuery('')
  }

  function cancelEdit() {
    const origin = editOriginRef.current
    setDraft(null)
    setEditingId(null)
    setDependencyQuery('')
    setExpandedDependencyPhaseIds(new Set())
    setParentQuery('')
    setParentPickerOpen(false)
    setParentError(null)
    editOriginRef.current = null
    window.requestAnimationFrame(() => {
      if (!origin) return
      window.scrollTo({ top: origin.scrollY, left: 0, behavior: 'auto' })
      lastPlanScrollYRef.current = origin.scrollY
      if (plan) writeScrollPosition(plan.id, origin.scrollY)
      const taskElement = document.getElementById(`task-${origin.taskId}`)
      taskElement?.querySelector<HTMLElement>('[data-task-edit-control]')?.focus({ preventScroll: true })
      if (taskElement) highlightTask(origin.taskId)
    })
  }

  function requestConfirmation(request: Omit<ConfirmationRequest, 'returnFocus'>, returnFocus?: HTMLElement | null) {
    setConfirmation({ ...request, returnFocus: returnFocus ?? document.activeElement as HTMLElement | null })
  }

  function closeConfirmation() {
    const returnFocus = confirmation?.returnFocus
    setConfirmation(null)
    window.requestAnimationFrame(() => returnFocus?.focus())
  }

  async function persistTask(confirmParentPhaseMove = false) {
    if (!draft || taskEditorSaving) return
    setTaskEditorSaving(true)
    setError(null)
    try {
      const write = { ...writeFromDraft(draft), ...(confirmParentPhaseMove ? { confirm_parent_phase_move: true } : {}) }
      const createdId = editingId ?? generateTaskId(write.title)
      const updated = editingId
        ? await replaceTask(editingId, write)
        : await createTask(createdId, write)
      acceptPlan(updated)
      onPlanChanged?.()
      setDraft(null)
      setEditingId(null)
      if (!editingId) {
        setCreationType(null)
        const createdTask = updated.tasks.find((task) => task.id === createdId)
        if (createdTask) selectFinderResult(createdTask)
      } else {
        const savedTask = updated.tasks.find((task) => task.id === createdId)
        const origin = editOriginRef.current
        editOriginRef.current = null
        if (savedTask && !taskMatchesCategoryFilters(savedTask, categoryFilters)) {
          setFoundTaskId(null)
          setFoundTaskFading(false)
          setHiddenSavedTaskId(savedTask.id)
          window.requestAnimationFrame(() => {
            const restoreY = origin?.scrollY ?? lastPlanScrollYRef.current
            window.scrollTo({ top: restoreY, left: 0, behavior: 'auto' })
          })
        } else if (savedTask) {
          setHiddenSavedTaskId(null)
          revealTask(savedTask, 'edit', 'if-needed')
        }
      }
    } catch (requestError) {
      if (requestError instanceof PlanRequestError && requestError.code === 'duplicate_task_title') {
        setTaskTitleError(requestError.message)
        titleInputRef.current?.focus()
      } else if (editingId && requestError instanceof PlanRequestError && requestError.code === 'parent_phase_move_confirmation_required') {
        requestConfirmation({
          heading: `Move parent and ${requiredSubtaskText(plan?.tasks.find((task) => task.id === editingId)?.subtask_count ?? 0)}?`,
          consequence: 'Every required subtask will move to the selected phase with this parent. Their other fields and current progress will stay unchanged.',
          confirmLabel: 'Move parent and subtasks',
          action: () => persistTask(true),
        })
      } else {
        setError(requestError instanceof Error ? requestError.message : 'Unable to save the task.')
      }
    } finally {
      setTaskEditorSaving(false)
    }
  }

  function saveTask(returnFocus?: HTMLElement | null) {
    if (!draft || taskEditorSaving) return
    if (plan && hasDuplicatePlanItemTitle(plan.tasks, draft.title, editingId)) {
      setError(null)
      setTaskTitleError('A task with this title already exists in this plan.')
      titleInputRef.current?.focus()
      return
    }
    if (draft.isSubtask && !draft.parentTaskId) {
      setParentError('Select the parent Task for this required subtask.')
      return
    }
    const parent = plan?.tasks.find((task) => task.id === draft.parentTaskId)
    const existing = plan?.tasks.find((task) => task.id === editingId)
    const firstAttachmentChangesStatus = Boolean(
      draft.isSubtask
      && parent
      && (parent.subtask_count ?? 0) === 0
      && existing?.parent_task_id !== parent.id
      && parent.status !== draft.status
    )
    if (firstAttachmentChangesStatus && parent) {
      requestConfirmation({
        heading: 'Attach the first required subtask?',
        consequence: `“${parent.title}” will become ${statusLabels[draft.status].toLowerCase()} because its status will now be derived from this required subtask.`,
        confirmLabel: 'Attach required subtask',
        action: () => persistTask(),
      }, returnFocus)
      return
    }
    void persistTask()
  }

  async function updateStatus(task: RelocationTask, status: TaskStatus, returnFocus?: HTMLElement | null) {
    setPendingTaskStatusIds((current) => new Set(current).add(task.id))
    setError(null)
    try {
      acceptPlan(await changeTaskStatus(task.id, status))
      onPlanChanged?.()
    } catch (requestError) {
      if (requestError instanceof PlanRequestError && requestError.code === 'parent_status_override_confirmation_required') {
        requestConfirmation({
          heading: status === 'completed' ? 'Complete this parent manually?' : 'Override automatic parent status?',
          consequence: status === 'completed'
            ? 'Required subtasks are still incomplete. Completing the parent manually may unblock downstream work, and later subtask changes will not replace this override.'
            : `The parent will show ${statusLabels[status].toLowerCase()} even though its required subtasks imply ${statusLabels[task.automatic_status ?? task.status].toLowerCase()}. Later subtask changes will not replace this override.`,
          confirmLabel: status === 'completed' ? 'Complete parent manually' : 'Use manual status',
          action: async () => {
            acceptPlan(await changeTaskStatus(task.id, status, true))
            onPlanChanged?.()
          },
        }, returnFocus)
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
    try { acceptPlan(await returnParentToAutomaticStatus(task.id)); onPlanChanged?.() }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Unable to restore automatic status.') }
  }

  async function moveSubtask(parent: RelocationTask, orderedChildren: RelocationTask[], task: RelocationTask, direction: -1 | 1) {
    const index = orderedChildren.findIndex((candidate) => candidate.id === task.id)
    const destination = index + direction
    if (index < 0 || destination < 0 || destination >= orderedChildren.length || reorderingParentIds.has(parent.id)) return
    const next = [...orderedChildren]
    ;[next[index], next[destination]] = [next[destination], next[index]]
    const scrollY = window.scrollY
    setReorderingParentIds((current) => new Set(current).add(parent.id))
    setError(null)
    try {
      acceptPlan(await reorderSubtasks(parent.id, next.map((child) => child.id)))
      onPlanChanged?.()
      const nextIndex = destination
      const preferredDirection = direction === -1 && nextIndex === 0 ? 1 : direction === 1 && nextIndex === next.length - 1 ? -1 : direction
      window.requestAnimationFrame(() => {
        window.scrollTo({ top: scrollY, left: 0, behavior: 'auto' })
        moveButtonRefs.current.get(`${task.id}:${preferredDirection}`)?.focus({ preventScroll: true })
      })
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to reorder required subtasks.')
    } finally {
      setReorderingParentIds((current) => { const nextIds = new Set(current); nextIds.delete(parent.id); return nextIds })
    }
  }

  function renderTask(
    task: RelocationTask,
    isSubtask = false,
    parentExpansion?: { expanded: boolean; toggle: () => void },
    movement?: { parent: RelocationTask; children: RelocationTask[]; index: number },
  ) {
    const titleId = `task-title-${task.id}`
    return (
      <article
        aria-labelledby={titleId}
        className={`task-item rounded-3 p-2 p-sm-3 ${isSubtask ? 'is-subtask' : ''} ${task.blocked ? 'is-blocked' : ''} ${foundTaskId === task.id ? `is-found${foundTaskFading ? ' is-found-fading' : ''}` : ''}`}
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
            {task.is_parent && parentExpansion && <Button aria-controls={`subtask-list-${task.id}`} aria-expanded={parentExpansion.expanded} className="subtask-progress-toggle d-inline-flex align-items-center gap-1 p-0 mb-1" onClick={parentExpansion.toggle} variant="link"><span>{task.completed_subtask_count ?? 0} of {requiredSubtaskText(task.subtask_count ?? 0)} completed</span><ExpansionChevron expanded={parentExpansion.expanded} /></Button>}
            <div className="task-metadata d-flex flex-wrap align-items-center gap-1 gap-sm-2 mb-2"><CategoryLabels categories={task.categories} /><span className="text-muted">{task.assignees.length > 0 ? task.assignees.join(', ') : 'Unassigned'}{task.start_date ? ` · Recommendations begin ${task.start_date}` : ''}{task.due_date ? ` · Due by ${task.due_date}` : ''}</span></div>
            {task.description && <p className="mb-2">{task.description}</p>}
            {task.dependency_task_ids.length > 0 && <p className="dependency-context mb-0"><strong>Depends on:</strong> {task.dependency_task_ids.map((id) => taskById.get(id)?.title ?? id).join(', ')}</p>}
          </div>
          <div className="task-actions d-flex flex-wrap align-items-start gap-2">
            {movement && <div className="d-flex gap-1" aria-label={`Order ${task.title}`} role="group"><Button disabled={movement.index === 0 || reorderingParentIds.has(movement.parent.id)} onClick={() => void moveSubtask(movement.parent, movement.children, task, -1)} ref={(element) => { if (element) moveButtonRefs.current.set(`${task.id}:-1`, element); else moveButtonRefs.current.delete(`${task.id}:-1`) }} size="sm" variant="outline-secondary">Move up</Button><Button disabled={movement.index === movement.children.length - 1 || reorderingParentIds.has(movement.parent.id)} onClick={() => void moveSubtask(movement.parent, movement.children, task, 1)} ref={(element) => { if (element) moveButtonRefs.current.set(`${task.id}:1`, element); else moveButtonRefs.current.delete(`${task.id}:1`) }} size="sm" variant="outline-secondary">Move down</Button></div>}
            <Form.Select aria-label={`Status for ${task.title}`} disabled={pendingTaskStatusIds.has(task.id)} value={task.status} onChange={(event) => void updateStatus(task, event.target.value as TaskStatus, event.currentTarget)}>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Form.Select>
            {task.is_parent && <Button variant="outline-primary" onClick={() => beginSubtask(task)}>Add subtask</Button>}
            {task.manual_status_override && <Button variant="outline-secondary" onClick={() => void returnToAutomaticStatus(task)}>Return to automatic status</Button>}
            <Button data-task-edit-control variant="outline-secondary" onClick={() => beginEdit(task)}>Edit</Button>
          </div>
        </div>
      </article>
    )
  }

  function renderTaskGroup(task: RelocationTask, phaseTasks: RelocationTask[]) {
    if (!task.is_parent) return renderTask(task)
    const allSubtasks = (plan?.tasks ?? [])
      .filter((candidate) => candidate.parent_task_id === task.id)
      .sort((left, right) => (left.subtask_position ?? 0) - (right.subtask_position ?? 0) || left.id.localeCompare(right.id))
    const visibleIds = new Set(phaseTasks.map((candidate) => candidate.id))
    const subtasks = allSubtasks.filter((candidate) => visibleIds.has(candidate.id))
    const expanded = expandedParentIds.has(task.id)
    return <div className="parent-task-group" key={task.id}>
      {renderTask(task, false, { expanded, toggle: () => setExpandedParentIds((current) => { const next = new Set(current); if (next.has(task.id)) next.delete(task.id); else next.add(task.id); return next }) })}
      {expanded && <Stack className="subtask-list gap-1 gap-sm-2 mt-2" id={`subtask-list-${task.id}`}>{subtasks.map((subtask) => renderTask(subtask, true, undefined, { parent: task, children: allSubtasks, index: allSubtasks.findIndex((candidate) => candidate.id === subtask.id) }))}</Stack>}
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
      {hiddenSavedTaskId && (
        <Alert
          className="filter-clear-notice position-fixed start-50 translate-middle-x mb-3 shadow-sm"
          dismissible
          onClose={() => setHiddenSavedTaskId(null)}
          role="status"
          variant="info"
        >
          <span>Task saved but hidden by the current filter.</span>{' '}
          <Button
            className="p-0 align-baseline"
            onClick={() => {
              const savedTask = plan?.tasks.find((task) => task.id === hiddenSavedTaskId)
              setHiddenSavedTaskId(null)
              if (savedTask) selectFinderResult(savedTask)
            }}
            ref={hiddenSavedTaskActionRef}
            variant="link"
          >Show task</Button>
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
        onRecommendationChanged={onPlanChanged}
        onDecisionTargetConsumed={consumeTarget}
        onTaskTargeted={selectFinderResult}
        onPlanUpdated={acceptPlan}
        plan={plan}
        targetDecisionId={target?.decisionId}
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
              <Form onSubmit={(event) => { event.preventDefault(); saveTask((event.nativeEvent as SubmitEvent).submitter as HTMLElement | null) }}>
              <Stack direction="horizontal" gap={2} className="task-editor-actions sticky-top flex-wrap py-3 mb-3">
                <Button type="submit" disabled={taskEditorSaving || invalidElapsed}>
                  {taskEditorSaving ? (editingId ? 'Saving…' : 'Creating…') : (editingId ? 'Save changes' : 'Create task')}
                </Button>
                <Button type="button" variant="outline-secondary" disabled={taskEditorSaving} onClick={() => {
                  if (!editingId && creationType === 'task') cancelCreation()
                  else cancelEdit()
                }}>Cancel</Button>
              </Stack>
              <Row className="g-3">
                <Col md={8}><Form.Group controlId="task-title"><Form.Label>Title</Form.Label><Form.Control aria-describedby="task-title-error" aria-invalid={Boolean(taskTitleError)} isInvalid={Boolean(taskTitleError)} ref={titleInputRef} required maxLength={200} value={draft.title} onChange={(event) => { const title = event.target.value; setDraft({ ...draft, title }); setTaskTitleError(plan && hasDuplicatePlanItemTitle(plan.tasks, title, editingId) ? 'A task with this title already exists in this plan.' : null) }} /><Form.Control.Feedback id="task-title-error" type="invalid">{taskTitleError}</Form.Control.Feedback></Form.Group></Col>
                <Col md={4}><Form.Group controlId="task-phase"><Form.Label>Phase</Form.Label><Form.Select disabled={draft.isSubtask && Boolean(draft.parentTaskId)} value={draft.phaseId} onChange={(event) => { setDraft({ ...draft, phaseId: event.target.value, parentTaskId: '' }); setParentError(null); setParentPickerOpen(draft.isSubtask) }}>{plan.phases.map((phase) => <option key={phase.id} value={phase.id}>{phase.title}</option>)}</Form.Select></Form.Group></Col>
                <Col xs={12}>
                  <Form.Group>
                    <Form.Check
                      checked={draft.isSubtask}
                      disabled={Boolean(editingId && plan.tasks.find((task) => task.id === editingId)?.is_parent)}
                      id="task-is-subtask"
                      label="This task is a subtask"
                      onChange={(event) => {
                        const isSubtask = event.target.checked
                        setDraft({ ...draft, isSubtask, parentTaskId: isSubtask ? draft.parentTaskId : '', subtaskPosition: isSubtask ? draft.subtaskPosition : '' })
                        setParentError(null)
                        setParentPickerOpen(isSubtask && !draft.parentTaskId)
                      }}
                    />
                    {draft.isSubtask && draft.parentTaskId && !parentPickerOpen && (() => {
                      const selectedParent = plan.tasks.find((task) => task.id === draft.parentTaskId)
                      return selectedParent ? <div className="selected-parent d-flex flex-wrap align-items-center justify-content-between gap-2 mt-2 p-2 rounded-2">
                        <span><strong>Part of {selectedParent.title}</strong><span className="d-block small text-muted"><CategoryLabels categories={selectedParent.categories} /> · {statusLabels[selectedParent.status]}</span></span>
                        <Button onClick={() => { setParentPickerOpen(true); setParentQuery('') }} size="sm" type="button" variant="outline-secondary">Change</Button>
                      </div> : null
                    })()}
                    {draft.isSubtask && (parentPickerOpen || !draft.parentTaskId) && <div className="parent-picker mt-2 p-2 rounded-2">
                      <Form.Label htmlFor="parent-search">Parent Task</Form.Label>
                      <Form.Control autoFocus id="parent-search" onChange={(event) => setParentQuery(event.target.value)} placeholder="Search eligible Tasks in this phase" type="search" value={parentQuery} />
                      <div aria-label="Eligible parent Tasks" className="parent-picker-results d-grid gap-1 mt-2" role="listbox">
                        {eligibleParents.map((candidate) => <button aria-selected={candidate.id === draft.parentTaskId} className="parent-picker-option text-start rounded-2 p-2" key={candidate.id} onClick={() => { setDraft({ ...draft, isSubtask: true, parentTaskId: candidate.id, phaseId: candidate.phase_id, subtaskPosition: draft.subtaskPosition || String(candidate.subtask_count ?? 0) }); setParentError(null); setParentPickerOpen(false); setParentQuery('') }} role="option" type="button"><strong className="d-block">{candidate.title}</strong><span className="small text-muted"><CategoryLabels categories={candidate.categories} /> · {statusLabels[candidate.status]}</span></button>)}
                        {eligibleParents.length === 0 && <p className="small text-muted mb-0">No eligible parent Tasks match this search in the selected phase.</p>}
                      </div>
                    </div>}
                    {parentError && <div className="invalid-feedback d-block" role="alert">{parentError}</div>}
                  </Form.Group>
                </Col>
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
                <Col xs={12}><Form.Group controlId="task-assignees"><Form.Label>Assignees <span className="text-muted">(optional)</span></Form.Label><Form.Control placeholder="Separate names with commas" value={draft.assignees} onChange={(event) => setDraft({ ...draft, assignees: event.target.value })} /></Form.Group></Col>
                <Col xs={12}>
                  <fieldset className="recommendation-timing-group rounded-3 p-3">
                    <legend className="form-label float-none w-auto mb-2">Recommendation timing <span className="text-muted">(optional)</span></legend>
                    <Row className="g-3">
                      <Col className="task-date-field" xs={12} lg={6}><Form.Group controlId="task-start-date"><Form.Label>Do not recommend before</Form.Label><Form.Control aria-describedby="task-start-date-help" type="date" value={draft.startDate} onChange={(event) => setDraft({ ...draft, startDate: event.target.value })} /><Form.Text id="task-start-date-help">You can still start or complete it earlier.</Form.Text></Form.Group></Col>
                      <Col className="task-date-field" xs={12} lg={6}><Form.Group controlId="task-due-date"><Form.Label>Due by</Form.Label><Form.Control type="date" value={draft.dueDate} onChange={(event) => setDraft({ ...draft, dueDate: event.target.value })} /></Form.Group></Col>
                    </Row>
                  </fieldset>
                </Col>
                <Col xs={12}>
                  <fieldset className="elapsed-time-group rounded-3 p-3">
                    <legend className="form-label float-none w-auto mb-2">Expected elapsed time <span className="text-muted">(optional)</span></legend>
                    {editingId && plan.tasks.find((task) => task.id === editingId)?.is_parent
                      ? <p className="mb-0"><strong>Expected elapsed time:</strong> {(() => {
                        const parent = plan.tasks.find((task) => task.id === editingId)
                        const minimum = parent?.derived_expected_elapsed_min_days
                        const maximum = parent?.derived_expected_elapsed_max_days
                        return minimum == null || maximum == null ? 'Unknown, derived from required subtasks' : `${minimum}–${maximum} days, derived from required subtasks`
                      })()}</p>
                      : <>
                        <div className="elapsed-time-fields d-flex flex-wrap align-items-end gap-2">
                          <Form.Group controlId="task-elapsed-min"><Form.Label>From</Form.Label><Form.Control isInvalid={invalidElapsed} min={0} max={3650} step={1} type="number" value={draft.elapsedMin} onChange={(event) => setDraft({ ...draft, elapsedMin: event.target.value })} /></Form.Group>
                          <Form.Group controlId="task-elapsed-max"><Form.Label>to</Form.Label><Form.Control isInvalid={invalidElapsed} min={0} max={3650} step={1} type="number" value={draft.elapsedMax} onChange={(event) => setDraft({ ...draft, elapsedMax: event.target.value })} /></Form.Group>
                          <Form.Group controlId="task-elapsed-unit"><Form.Label>Unit</Form.Label><Form.Select value={draft.elapsedUnit} onChange={(event) => setDraft({ ...draft, elapsedUnit: event.target.value as 'days' | 'weeks' })}><option value="days">days</option><option value="weeks">weeks</option></Form.Select></Form.Group>
                          <Button variant="outline-secondary" type="button" onClick={() => setDraft({ ...draft, elapsedMin: '0', elapsedMax: '0', elapsedUnit: 'days' })}>Same day</Button>
                          {(draft.elapsedMin !== '' || draft.elapsedMax !== '') && <Button variant="link" type="button" onClick={() => setDraft({ ...draft, elapsedMin: '', elapsedMax: '' })}>Clear</Button>}
                        </div>
                        {invalidElapsed && <div className="invalid-feedback d-block" role="alert">Enter both whole-number values, from smallest to largest, within 3,650 elapsed days.</div>}
                        <Form.Text>Include waiting time from beginning this Task until it can be considered complete.</Form.Text>
                      </>}
                  </fieldset>
                </Col>
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
                      {dependencyGroups.map(({ phase, tasks }) => {
                        const expanded = dependencySearchActive || expandedDependencyPhaseIds.has(phase.id)
                        const selectedCount = plan.tasks.filter((task) => task.phase_id === phase.id && draft.dependencies.includes(task.id)).length
                        return <fieldset className="dependency-phase mb-2" key={phase.id}>
                          <legend className="dependency-phase-title mb-0 w-100">
                            <button
                              aria-controls={`dependency-phase-options-${phase.id}`}
                              aria-expanded={expanded}
                              className="dependency-phase-toggle d-flex w-100 align-items-center justify-content-between gap-2 rounded-2 px-2 py-2 text-start"
                              disabled={dependencySearchActive}
                              onClick={() => setExpandedDependencyPhaseIds((current) => { const next = new Set(current); if (next.has(phase.id)) next.delete(phase.id); else next.add(phase.id); return next })}
                              type="button"
                            >
                              <span>{phase.title} · {selectedCount} selected</span>
                              <ExpansionChevron expanded={expanded} />
                            </button>
                          </legend>
                          {expanded && <div className="dependency-phase-options px-2 pt-1" id={`dependency-phase-options-${phase.id}`}>
                            {tasks.map((task) => (
                              <Form.Check key={task.id} id={`dependency-${task.id}`} label={`${task.title} (${statusLabels[task.status]})`} checked={draft.dependencies.includes(task.id)} onChange={(event) => setDraft({ ...draft, dependencies: event.target.checked ? [...draft.dependencies, task.id] : draft.dependencies.filter((id) => id !== task.id) })} />
                            ))}
                          </div>}
                        </fieldset>
                      })}
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
                <ExpansionChevron expanded={phaseExpanded} />
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
    <Modal
      aria-labelledby="task-confirmation-title"
      backdrop="static"
      centered
      className="task-confirmation-modal"
      onHide={() => { if (!confirmationPending) closeConfirmation() }}
      restoreFocus={false}
      show={Boolean(confirmation)}
    >
      <Modal.Header closeButton={!confirmationPending}>
        <Modal.Title as="h2" id="task-confirmation-title">{confirmation?.heading}</Modal.Title>
      </Modal.Header>
      <Modal.Body><p className="mb-0">{confirmation?.consequence}</p></Modal.Body>
      <Modal.Footer>
        <Button disabled={confirmationPending} onClick={closeConfirmation} variant="outline-secondary">Cancel</Button>
        <Button disabled={confirmationPending} onClick={() => {
          if (!confirmation) return
          const request = confirmation
          setConfirmationPending(true)
          void request.action()
            .then(() => {
              setConfirmation(null)
              window.requestAnimationFrame(() => request.returnFocus?.focus())
            })
            .catch((requestError) => {
              setError(requestError instanceof Error ? requestError.message : 'Unable to complete the requested change.')
              setConfirmation(null)
              window.requestAnimationFrame(() => request.returnFocus?.focus())
            })
            .finally(() => setConfirmationPending(false))
        }}>{confirmationPending ? 'Saving…' : confirmation?.confirmLabel}</Button>
      </Modal.Footer>
    </Modal>
    </>
  )
}
