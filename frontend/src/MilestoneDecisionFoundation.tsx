import { useEffect, useRef, useState } from 'react'
import { Alert, Badge, Button, Card, Col, Form, Modal, Overlay, Popover, Row, Stack } from 'react-bootstrap'
import {
  changeDecisionSelection,
  changeMilestoneAchievement,
  createDecision,
  createMilestone,
  PlanRequestError,
  replaceDecision,
  replaceMilestone,
  type Decision,
  type DecisionOption,
  type Milestone,
  type RelocationPlan,
  type RelocationTask,
} from './api/relocationPlan'
import { hasDuplicatePlanItemTitle } from './titleUniqueness'
import { ExpansionChevron } from './ExpansionChevron'

interface Props {
  plan: RelocationPlan
  onPlanUpdated: (plan: RelocationPlan) => void
  creationType?: 'milestone' | 'decision' | null
  onCreationCanceled?: () => void
  onCreationSaved?: () => void
  onEditorOpenChange?: (open: boolean) => void
  onItemRevealed?: () => void
  onRecommendationChanged?: () => void
  onTaskTargeted?: (task: RelocationTask) => void
  targetDecisionId?: string
  onDecisionTargetConsumed?: () => void
}

type MilestoneDraft = Pick<Milestone, 'title' | 'description' | 'target_earliest_date' | 'target_latest_date' | 'timing_mode' | 'governed_phase_id'>
type DecisionDraft = Pick<Decision, 'title' | 'description' | 'milestone_id' | 'options'> & { preparation_task_ids: string[] }

const emptyMilestone = (): MilestoneDraft => ({
  title: '', description: '', target_earliest_date: null, target_latest_date: null,
  timing_mode: 'target_window', governed_phase_id: null,
})

const itemId = (title: string, kind: string) => {
  const slug = title.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 24)
  return `${slug || kind}-${crypto.randomUUID()}`
}

const newOption = (): DecisionOption => ({
  id: `option-${crypto.randomUUID()}`, title: '', description: null,
})

const monthNames = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

function dateParts(value: string) {
  const [year, month, day] = value.split('-').map(Number)
  return { year, month, day }
}

function displayDate(value: string, includeYear = true) {
  const { year, month, day } = dateParts(value)
  return `${monthNames[month - 1]} ${day}${includeYear ? `, ${year}` : ''}`
}

export function formatMilestoneTiming(milestone: Pick<Milestone, 'target_earliest_date' | 'target_latest_date' | 'timing_mode'>) {
  const earliest = milestone.target_earliest_date
  const latest = milestone.target_latest_date
  if (milestone.timing_mode === 'fixed_date') {
    return earliest ? `Fixed date: ${displayDate(earliest)}` : 'Fixed date not set'
  }
  if (!earliest) {
    return latest
      ? `Target: on or before ${displayDate(latest)}`
      : 'Target timing not set'
  }
  if (!latest) return `Target: on or after ${displayDate(earliest)}`
  if (earliest === latest) return `Target: ${displayDate(earliest)}`
  const earliestParts = dateParts(earliest)
  const latestParts = dateParts(latest)
  if (earliestParts.year === latestParts.year) {
    return `Target: ${displayDate(earliest, false)} – ${displayDate(latest)}`
  }
  return `Target: ${displayDate(earliest)} – ${displayDate(latest)}`
}

export function MilestoneDecisionFoundation({
  plan,
  onPlanUpdated,
  creationType = null,
  onCreationCanceled,
  onCreationSaved,
  onEditorOpenChange,
  onItemRevealed,
  onRecommendationChanged,
  onTaskTargeted,
  targetDecisionId,
  onDecisionTargetConsumed,
}: Props) {
  const [milestoneDraft, setMilestoneDraft] = useState<MilestoneDraft | null>(null)
  const [milestoneId, setMilestoneId] = useState<string | null>(null)
  const [decisionDraft, setDecisionDraft] = useState<DecisionDraft | null>(null)
  const [decisionId, setDecisionId] = useState<string | null>(null)
  const [pendingActions, setPendingActions] = useState<Set<string>>(new Set())
  const [error, setError] = useState<string | null>(null)
  const [milestoneTitleError, setMilestoneTitleError] = useState<string | null>(null)
  const [decisionTitleError, setDecisionTitleError] = useState<string | null>(null)
  const [preparationQuery, setPreparationQuery] = useState('')
  const [preparationSearchActive, setPreparationSearchActive] = useState(false)
  const [expandedMilestones, setExpandedMilestones] = useState<Set<string>>(() => {
    try { return new Set(JSON.parse(sessionStorage.getItem(`gotime:milestone-expansion:${plan.id}:v1`) ?? '[]') as string[]) }
    catch { return new Set() }
  })
  const [expandedDecisions, setExpandedDecisions] = useState<Set<string>>(() => {
    try { return new Set(JSON.parse(sessionStorage.getItem(`gotime:decision-expansion:${plan.id}:v1`) ?? '[]') as string[]) }
    catch { return new Set() }
  })
  const [expandedPreparation, setExpandedPreparation] = useState<Set<string>>(() => {
    try { return new Set(JSON.parse(sessionStorage.getItem(`gotime:decision-preparation:${plan.id}:v1`) ?? '[]') as string[]) }
    catch { return new Set() }
  })
  const [expandedTiming, setExpandedTiming] = useState<Set<string>>(() => {
    try { return new Set(JSON.parse(sessionStorage.getItem(`gotime:milestone-timing:${plan.id}:v1`) ?? '[]') as string[]) }
    catch { return new Set() }
  })
  const [selectionConfirmation, setSelectionConfirmation] = useState<{ decisionId: string; optionId: string; returnFocus: HTMLElement } | null>(null)
  const [readinessHelpDecisionId, setReadinessHelpDecisionId] = useState<string | null>(null)
  const [foundItem, setFoundItem] = useState<{ type: 'milestone' | 'decision'; id: string } | null>(null)
  const [pendingReveal, setPendingReveal] = useState<{ type: 'milestone' | 'decision'; id: string } | null>(null)
  const milestoneTitleRef = useRef<HTMLInputElement>(null)
  const decisionTitleRef = useRef<HTMLInputElement>(null)
  const itemRefs = useRef(new Map<string, HTMLElement>())
  const readinessHelpRefs = useRef(new Map<string, HTMLButtonElement>())
  const suppressReadinessHelpFocusRef = useRef(false)

  useEffect(() => {
    if (creationType === 'milestone') {
      setDecisionDraft(null)
      setDecisionId(null)
      setMilestoneId(null)
      setMilestoneDraft(emptyMilestone())
      setError(null)
      setMilestoneTitleError(null)
    } else if (creationType === 'decision' && plan.milestones.length > 0) {
      setMilestoneDraft(null)
      setMilestoneId(null)
      setDecisionId(null)
      setDecisionDraft({ title: '', description: '', milestone_id: plan.milestones[0].id, options: [newOption(), newOption()], preparation_task_ids: [] })
      setError(null)
      setDecisionTitleError(null)
    }
  }, [creationType, plan.milestones])

  useEffect(() => {
    sessionStorage.setItem(`gotime:decision-preparation:${plan.id}:v1`, JSON.stringify([...expandedPreparation]))
  }, [expandedPreparation, plan.id])

  useEffect(() => {
    sessionStorage.setItem(`gotime:milestone-expansion:${plan.id}:v1`, JSON.stringify([...expandedMilestones]))
  }, [expandedMilestones, plan.id])

  useEffect(() => {
    sessionStorage.setItem(`gotime:milestone-timing:${plan.id}:v1`, JSON.stringify([...expandedTiming]))
  }, [expandedTiming, plan.id])

  useEffect(() => {
    const eligibleMilestoneIds = new Set(plan.milestones
      .filter((milestone) => milestone.timing_mode === 'fixed_date' && Boolean(milestone.governed_phase_id) && Boolean(milestone.timing) && milestone.timing?.status !== 'no_work_linked')
      .map((milestone) => milestone.id))
    setExpandedTiming((current) => {
      const next = new Set([...current].filter((id) => eligibleMilestoneIds.has(id)))
      return next.size === current.size ? current : next
    })
  }, [plan.milestones])

  useEffect(() => {
    sessionStorage.setItem(`gotime:decision-expansion:${plan.id}:v1`, JSON.stringify([...expandedDecisions]))
  }, [expandedDecisions, plan.id])

  useEffect(() => {
    onEditorOpenChange?.(Boolean(milestoneDraft || decisionDraft))
  }, [decisionDraft, milestoneDraft, onEditorOpenChange])

  useEffect(() => {
    if (milestoneDraft) milestoneTitleRef.current?.focus()
    else if (decisionDraft) decisionTitleRef.current?.focus()
  }, [decisionDraft !== null, milestoneDraft !== null])

  useEffect(() => {
    if (!pendingReveal) return
    const element = itemRefs.current.get(`${pendingReveal.type}:${pendingReveal.id}`)
    if (!element) return
    element.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
    element.focus({ preventScroll: true })
    setPendingReveal(null)
    onItemRevealed?.()
  }, [onItemRevealed, pendingReveal, plan])

  useEffect(() => {
    if (!targetDecisionId) return
    const decision = plan.decisions.find((item) => item.id === targetDecisionId)
    if (decision) {
      setExpandedMilestones((current) => new Set(current).add(decision.milestone_id))
      setExpandedDecisions((current) => new Set(current).add(decision.id))
      setFoundItem({ type: 'decision', id: decision.id })
      setPendingReveal({ type: 'decision', id: decision.id })
    }
    onDecisionTargetConsumed?.()
  }, [onDecisionTargetConsumed, plan.decisions, targetDecisionId])

  useEffect(() => {
    if (!readinessHelpDecisionId) return
    const dismiss = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      event.preventDefault()
      const button = readinessHelpRefs.current.get(readinessHelpDecisionId)
      setReadinessHelpDecisionId(null)
      suppressReadinessHelpFocusRef.current = true
      button?.focus()
      window.requestAnimationFrame(() => { suppressReadinessHelpFocusRef.current = false })
    }
    document.addEventListener('keydown', dismiss)
    return () => document.removeEventListener('keydown', dismiss)
  }, [readinessHelpDecisionId])

  function closeReadinessHelp(decisionId: string) {
    const button = readinessHelpRefs.current.get(decisionId)
    setReadinessHelpDecisionId(null)
    suppressReadinessHelpFocusRef.current = true
    button?.focus()
    window.requestAnimationFrame(() => { suppressReadinessHelpFocusRef.current = false })
  }

  async function perform(
    key: string,
    action: () => Promise<RelocationPlan>,
    handleError?: (reason: unknown) => boolean,
  ) {
    setPendingActions((current) => new Set(current).add(key))
    setError(null)
    try {
      const updated = await action()
      onPlanUpdated(updated)
      if (!key.startsWith('milestone-') && key !== 'save-milestone') onRecommendationChanged?.()
      return updated
    }
    catch (reason) {
      if (!handleError?.(reason)) {
        setError(reason instanceof Error ? reason.message : 'Unable to update the plan.')
      }
      return null
    }
    finally {
      setPendingActions((current) => {
        const next = new Set(current)
        next.delete(key)
        return next
      })
    }
  }

  async function saveMilestone() {
    if (!milestoneDraft) return
    if (hasDuplicatePlanItemTitle(plan.milestones, milestoneDraft.title, milestoneId)) {
      setError(null)
      setMilestoneTitleError('A milestone with this title already exists in this plan.')
      milestoneTitleRef.current?.focus()
      return
    }
    if (
      milestoneDraft.target_earliest_date
      && milestoneDraft.target_latest_date
      && milestoneDraft.target_latest_date < milestoneDraft.target_earliest_date
    ) return
    const write = { ...milestoneDraft, description: milestoneDraft.description?.trim() || null }
    const createdId = milestoneId ?? itemId(write.title, 'milestone')
    const saved = await perform('save-milestone', () => milestoneId
      ? replaceMilestone(milestoneId, write)
      : createMilestone(createdId, write), (reason) => {
        if (!(reason instanceof PlanRequestError) || reason.code !== 'duplicate_milestone_title') return false
        setMilestoneTitleError(reason.message)
        milestoneTitleRef.current?.focus()
        return true
      })
    if (!saved) return
    setMilestoneDraft(null)
    setMilestoneId(null)
    if (!milestoneId) {
      setFoundItem({ type: 'milestone', id: createdId })
      setPendingReveal({ type: 'milestone', id: createdId })
      onCreationSaved?.()
    }
  }

  async function saveDecision() {
    if (!decisionDraft) return
    if (hasDuplicatePlanItemTitle(plan.decisions, decisionDraft.title, decisionId)) {
      setError(null)
      setDecisionTitleError('A decision with this title already exists in this plan.')
      decisionTitleRef.current?.focus()
      return
    }
    const write = {
      ...decisionDraft,
      description: decisionDraft.description?.trim() || null,
      options: decisionDraft.options.map((option) => ({
        ...option, title: option.title.trim(), description: option.description?.trim() || null,
      })),
    }
    const createdId = decisionId ?? itemId(write.title, 'decision')
    const saved = await perform('save-decision', () => decisionId
      ? replaceDecision(decisionId, write)
      : createDecision(createdId, write), (reason) => {
        if (!(reason instanceof PlanRequestError) || reason.code !== 'duplicate_decision_title') return false
        setDecisionTitleError(reason.message)
        decisionTitleRef.current?.focus()
        return true
      })
    if (!saved) return
    setDecisionDraft(null)
    setDecisionId(null)
    if (!decisionId) {
      const created = saved.decisions.find((decision) => decision.id === createdId)
      if (created) setExpandedMilestones((current) => new Set(current).add(created.milestone_id))
      setExpandedDecisions((current) => new Set(current).add(createdId))
      setFoundItem({ type: 'decision', id: createdId })
      setPendingReveal({ type: 'decision', id: createdId })
      onCreationSaved?.()
    }
  }

  const invalidTargetWindow = Boolean(
    milestoneDraft?.target_earliest_date
    && milestoneDraft.target_latest_date
    && milestoneDraft.target_latest_date < milestoneDraft.target_earliest_date,
  )
  const phaseById = new Map(plan.phases.map((phase) => [phase.id, phase]))
  const taskById = new Map(plan.tasks.map((task) => [task.id, task]))
  const preparationCandidates = [...plan.tasks].sort((left, right) =>
    (phaseById.get(left.phase_id)?.position ?? 0) - (phaseById.get(right.phase_id)?.position ?? 0)
      || left.title.localeCompare(right.title),
  ).filter((task) => {
    const query = preparationQuery.trim().toLocaleLowerCase()
    return Boolean(query) && task.title.toLocaleLowerCase().includes(query)
  })
  const readinessLabel = (decision: Decision) => decision.preparation_readiness === 'ready_to_decide'
    ? 'Ready to decide'
    : decision.preparation_readiness === 'preparation_incomplete'
      ? 'Preparation incomplete'
      : 'No preparation tasks'

  return (
    <section className="plan-foundation mb-4" aria-labelledby="plan-foundation-heading">
      <div className="plan-foundation-heading px-2 px-sm-0 mb-3">
        <h4 className="h4 mb-0" id="plan-foundation-heading">Milestones and decisions</h4>
      </div>
      {error && <Alert variant="danger">{error}</Alert>}

      {milestoneDraft && <Card className="plan-foundation-card mb-3"><Card.Body>
        <Card.Title className="plan-foundation-title">{milestoneId ? 'Edit milestone' : 'Add milestone'}</Card.Title>
        <Form onSubmit={(event) => { event.preventDefault(); void saveMilestone() }}>
          <Row className="g-3">
            <Col xs={12}><Form.Group controlId="milestone-title"><Form.Label>Name</Form.Label><Form.Control aria-describedby="milestone-title-error" aria-invalid={Boolean(milestoneTitleError)} isInvalid={Boolean(milestoneTitleError)} ref={milestoneTitleRef} required maxLength={200} value={milestoneDraft.title} onChange={(event) => { const title = event.target.value; setMilestoneDraft({ ...milestoneDraft, title }); setMilestoneTitleError(hasDuplicatePlanItemTitle(plan.milestones, title, milestoneId) ? 'A milestone with this title already exists in this plan.' : null) }} /><Form.Control.Feedback id="milestone-title-error" type="invalid">{milestoneTitleError}</Form.Control.Feedback></Form.Group></Col>
            <Col xs={12}><Form.Group controlId="milestone-description"><Form.Label>Description <span className="text-muted">(optional)</span></Form.Label><Form.Control as="textarea" maxLength={2000} value={milestoneDraft.description ?? ''} onChange={(event) => setMilestoneDraft({ ...milestoneDraft, description: event.target.value })} /></Form.Group></Col>
            <Col xs={12}><fieldset><legend className="form-label">Timing</legend><Form.Check checked={(milestoneDraft.timing_mode ?? 'target_window') === 'target_window'} id="milestone-timing-window" inline label="Target window" name="milestone-timing-mode" type="radio" onChange={() => setMilestoneDraft({ ...milestoneDraft, timing_mode: 'target_window', governed_phase_id: null })} /><Form.Check checked={milestoneDraft.timing_mode === 'fixed_date'} id="milestone-timing-fixed" inline label="Fixed date" name="milestone-timing-mode" type="radio" onChange={() => { const fixed = milestoneDraft.target_earliest_date ?? milestoneDraft.target_latest_date; setMilestoneDraft({ ...milestoneDraft, timing_mode: 'fixed_date', target_earliest_date: fixed, target_latest_date: fixed }) }} /></fieldset></Col>
            {milestoneDraft.timing_mode === 'fixed_date' ? <>
              <Col sm={6}><Form.Group controlId="milestone-fixed-date"><Form.Label>Fixed date</Form.Label><Form.Control required type="date" value={milestoneDraft.target_earliest_date ?? ''} onChange={(event) => { const value = event.target.value || null; setMilestoneDraft({ ...milestoneDraft, target_earliest_date: value, target_latest_date: value }) }} /></Form.Group></Col>
              <Col sm={6}><Form.Group controlId="milestone-governed-phase"><Form.Label>Work to finish before this date</Form.Label><Form.Select value={milestoneDraft.governed_phase_id ?? ''} onChange={(event) => setMilestoneDraft({ ...milestoneDraft, governed_phase_id: event.target.value || null })}><option value="">No phase selected</option>{plan.phases.map((phase) => <option key={phase.id} value={phase.id}>{phase.title}</option>)}</Form.Select><Form.Text>All active work in this phase—including work added later—will be planned backward from the fixed date.</Form.Text></Form.Group></Col>
            </> : <>
              <Col sm={6}><Form.Group controlId="milestone-earliest"><Form.Label>Earliest target date <span className="text-muted">(optional)</span></Form.Label><Form.Control type="date" value={milestoneDraft.target_earliest_date ?? ''} onChange={(event) => setMilestoneDraft({ ...milestoneDraft, target_earliest_date: event.target.value || null })} /><Form.Text>Planning guidance; not a task start date.</Form.Text></Form.Group></Col>
              <Col sm={6}><Form.Group controlId="milestone-latest"><Form.Label>Latest target date <span className="text-muted">(optional)</span></Form.Label><Form.Control aria-describedby="milestone-latest-help" isInvalid={invalidTargetWindow} min={milestoneDraft.target_earliest_date ?? undefined} type="date" value={milestoneDraft.target_latest_date ?? ''} onChange={(event) => setMilestoneDraft({ ...milestoneDraft, target_latest_date: event.target.value || null })} /><Form.Control.Feedback type="invalid">Latest target must be on or after the earliest target.</Form.Control.Feedback><Form.Text id="milestone-latest-help">Leave blank for an open-ended “on or after” target.</Form.Text></Form.Group></Col>
            </>}
          </Row>
          <Stack direction="horizontal" gap={2} className="mt-3"><Button type="submit" disabled={pendingActions.has('save-milestone') || invalidTargetWindow}>Save milestone</Button><Button variant="outline-secondary" disabled={pendingActions.has('save-milestone')} onClick={() => { const creating = !milestoneId; setMilestoneDraft(null); setMilestoneId(null); setMilestoneTitleError(null); if (creating) onCreationCanceled?.() }}>Cancel</Button></Stack>
        </Form>
      </Card.Body></Card>}

      {decisionDraft && <Card className="plan-foundation-card mb-3"><Card.Body>
        <Card.Title className="plan-foundation-title">{decisionId ? 'Edit decision' : 'Add decision'}</Card.Title>
        <Form onSubmit={(event) => { event.preventDefault(); void saveDecision() }}>
          <Row className="g-3">
            <Col md={8}><Form.Group controlId="decision-title"><Form.Label>Decision</Form.Label><Form.Control aria-describedby="decision-title-error" aria-invalid={Boolean(decisionTitleError)} isInvalid={Boolean(decisionTitleError)} ref={decisionTitleRef} required maxLength={200} value={decisionDraft.title} onChange={(event) => { const title = event.target.value; setDecisionDraft({ ...decisionDraft, title }); setDecisionTitleError(hasDuplicatePlanItemTitle(plan.decisions, title, decisionId) ? 'A decision with this title already exists in this plan.' : null) }} /><Form.Control.Feedback id="decision-title-error" type="invalid">{decisionTitleError}</Form.Control.Feedback></Form.Group></Col>
            <Col md={4}><Form.Group controlId="decision-milestone"><Form.Label>Milestone</Form.Label><Form.Select value={decisionDraft.milestone_id} onChange={(event) => setDecisionDraft({ ...decisionDraft, milestone_id: event.target.value })}>{plan.milestones.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</Form.Select></Form.Group></Col>
            <Col xs={12}><Form.Group controlId="decision-description"><Form.Label>Context <span className="text-muted">(optional)</span></Form.Label><Form.Control as="textarea" maxLength={2000} value={decisionDraft.description ?? ''} onChange={(event) => setDecisionDraft({ ...decisionDraft, description: event.target.value })} /></Form.Group></Col>
            <Col xs={12}><Form.Group controlId="decision-preparation-search">
              <Form.Label>Work needed before deciding</Form.Label>
              {decisionDraft.preparation_task_ids.length > 0 && <div className="selected-preparation-tasks d-flex flex-wrap gap-2 mb-2" aria-label="Selected preparation tasks">{decisionDraft.preparation_task_ids.map((taskId) => taskById.get(taskId)).filter((task): task is RelocationTask => Boolean(task)).map((task) => <span className="selected-preparation-task d-inline-flex align-items-center gap-1 rounded-pill" key={task.id}><span>{task.title}</span><Button aria-label={`Remove ${task.title}`} className="selected-preparation-remove p-0" size="sm" variant="link" onClick={() => setDecisionDraft({ ...decisionDraft, preparation_task_ids: decisionDraft.preparation_task_ids.filter((id) => id !== task.id) })}>×</Button></span>)}</div>}
              <div onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setPreparationSearchActive(false) }}>
                <Form.Control aria-controls="decision-preparation-results" aria-expanded={preparationSearchActive && Boolean(preparationQuery.trim())} autoComplete="off" placeholder="Search tasks" type="search" value={preparationQuery} onChange={(event) => { setPreparationQuery(event.target.value); setPreparationSearchActive(true) }} onFocus={() => setPreparationSearchActive(true)} />
              {preparationSearchActive && preparationQuery.trim() && <div className="decision-preparation-picker border rounded mt-2 p-2" id="decision-preparation-results" role="group" aria-label="Preparation task search results">
                {preparationCandidates.length === 0 && <p className="small text-muted mb-0">No matching Tasks.</p>}
                {preparationCandidates.map((task) => {
                  const parent = task.parent_task_id ? taskById.get(task.parent_task_id) : null
                  const checked = decisionDraft.preparation_task_ids.includes(task.id)
                  const paired = decisionDraft.preparation_task_ids.some((selectedId) => {
                    const selected = taskById.get(selectedId)
                    return selected?.parent_task_id === task.id || task.parent_task_id === selectedId
                  })
                  return <Form.Check
                    checked={checked}
                    disabled={!checked && paired}
                    id={`decision-preparation-${task.id}`}
                    key={task.id}
                    label={<><strong>{task.title}</strong><span className="d-block small text-muted">{phaseById.get(task.phase_id)?.title} · {task.status.replace('_', ' ')} · {task.categories.length ? task.categories.join(', ') : 'Uncategorized'}{parent ? ` · Part of ${parent.title}` : ''}</span></>}
                    onChange={(event) => { setDecisionDraft({ ...decisionDraft, preparation_task_ids: event.target.checked ? [...decisionDraft.preparation_task_ids, task.id] : decisionDraft.preparation_task_ids.filter((id) => id !== task.id) }); setPreparationQuery('') }}
                  />
                })}
              </div>}
              </div>
              <Form.Text>Readiness reflects the current effective status of the selected work; it never selects an option.</Form.Text>
            </Form.Group></Col>
            <Col xs={12}><Form.Label>Options</Form.Label>{decisionDraft.options.map((option, index) => <div className="decision-option-row d-flex flex-wrap flex-sm-nowrap gap-2 mb-2" key={option.id}><Form.Control className="decision-option-input" aria-label={`Option ${index + 1}`} required maxLength={200} value={option.title} onChange={(event) => setDecisionDraft({ ...decisionDraft, options: decisionDraft.options.map((item, itemIndex) => itemIndex === index ? { ...item, title: event.target.value } : item) })} /><Button aria-label={`Move option ${index + 1} up`} disabled={index === 0} variant="outline-secondary" onClick={() => { const options = [...decisionDraft.options]; [options[index - 1], options[index]] = [options[index], options[index - 1]]; setDecisionDraft({ ...decisionDraft, options }) }}>↑</Button><Button aria-label={`Remove option ${index + 1}`} disabled={decisionDraft.options.length <= 2 || option.id === plan.decisions.find((item) => item.id === decisionId)?.selected_option_id} variant="outline-secondary" onClick={() => setDecisionDraft({ ...decisionDraft, options: decisionDraft.options.filter((_, itemIndex) => itemIndex !== index) })}>Remove</Button></div>)}</Col>
          </Row>
          <Button size="sm" variant="outline-secondary" onClick={() => setDecisionDraft({ ...decisionDraft, options: [...decisionDraft.options, newOption()] })}>Add option</Button>
          <Stack direction="horizontal" gap={2} className="mt-3"><Button type="submit" disabled={pendingActions.has('save-decision')}>Save decision</Button><Button variant="outline-secondary" disabled={pendingActions.has('save-decision')} onClick={() => { const creating = !decisionId; setDecisionDraft(null); setDecisionId(null); setDecisionTitleError(null); if (creating) onCreationCanceled?.() }}>Cancel</Button></Stack>
        </Form>
      </Card.Body></Card>}

      {plan.milestones.length === 0 && !milestoneDraft && <p className="text-muted">No milestones yet.</p>}
      <Row className="milestone-stack g-3">{plan.milestones.map((milestone) => {
        const decisions = plan.decisions.filter((decision) => decision.milestone_id === milestone.id)
        const resolvedCount = decisions.filter((decision) => decision.status === 'resolved').length
        const milestoneExpanded = expandedMilestones.has(milestone.id)
        const timingExpanded = expandedTiming.has(milestone.id)
        const timingDisclosureEligible = milestone.timing_mode === 'fixed_date' && Boolean(milestone.governed_phase_id) && Boolean(milestone.timing) && milestone.timing?.status !== 'no_work_linked'
        return <Col className="milestone-column" xs={12} key={milestone.id}><Card
        aria-labelledby={`milestone-title-${milestone.id}`}
        as="article"
        className={`plan-foundation-card plan-foundation-item ${foundItem?.type === 'milestone' && foundItem.id === milestone.id ? 'is-found' : ''}`}
        ref={(element: HTMLElement | null) => {
          if (element) itemRefs.current.set(`milestone:${milestone.id}`, element)
          else itemRefs.current.delete(`milestone:${milestone.id}`)
        }}
        tabIndex={-1}
      ><Card.Body>
        <div className="d-flex align-items-start justify-content-between gap-2">
          <button aria-controls={`milestone-body-${milestone.id}`} aria-expanded={milestoneExpanded} className="foundation-expansion-toggle d-inline-flex align-items-center gap-2 p-0 text-start" onClick={() => setExpandedMilestones((current) => { const next = new Set(current); if (next.has(milestone.id)) next.delete(milestone.id); else next.add(milestone.id); return next })} type="button"><Card.Title className="plan-foundation-title milestone-title mb-0" as="h4" id={`milestone-title-${milestone.id}`}>{milestone.title}</Card.Title><ExpansionChevron expanded={milestoneExpanded} /></button>
          <Badge className="align-self-start flex-shrink-0" bg={milestone.status === 'achieved' ? 'success' : 'secondary'}>{milestone.status === 'achieved' ? 'Achieved' : 'Pending'}</Badge>
        </div>
        <p className="plan-foundation-metadata text-muted mb-1">{formatMilestoneTiming(milestone)}</p>
        {milestone.timing && <div className="milestone-timing-summary mt-2">
          {milestone.timing.status !== 'no_work_linked' && <Badge bg={milestone.timing.status === 'likely_to_miss' ? 'danger' : milestone.timing.status === 'at_risk' ? 'warning' : milestone.timing.status === 'time_to_begin' ? 'primary' : 'secondary'} text={milestone.timing.status === 'at_risk' ? 'dark' : undefined}>{{ timing_incomplete: 'Timing incomplete', not_yet_time_sensitive: 'Not yet time-sensitive', time_to_begin: 'Time to begin', at_risk: 'At risk', likely_to_miss: 'Likely to miss' }[milestone.timing.status]}</Badge>}
          {milestone.timing.status === 'no_work_linked' && <p className="text-muted mb-1"><strong>No work linked yet</strong></p>}
          {milestone.timing.status !== 'no_work_linked' && <p className="small text-muted mt-1 mb-1">{milestone.timing.summary}</p>}
          {timingDisclosureEligible && <>
          <Button aria-controls={`milestone-timing-${milestone.id}`} aria-expanded={timingExpanded} className="p-0" size="sm" variant="link" onClick={() => setExpandedTiming((current) => { const next = new Set(current); if (next.has(milestone.id)) next.delete(milestone.id); else next.add(milestone.id); return next })}>View timing</Button>
          {timingExpanded && <div className="milestone-timing-details border rounded-3 p-3 mt-2" id={`milestone-timing-${milestone.id}`}>
            {milestone.governed_phase_id && <p><strong>Work to finish before this date:</strong> {phaseById.get(milestone.governed_phase_id)?.title}</p>}
            {milestone.timing.duration_min_days != null && milestone.timing.duration_max_days != null && <p><strong>Critical path:</strong> {milestone.timing.duration_min_days}–{milestone.timing.duration_max_days} elapsed days</p>}
            {milestone.timing.conservative_latest_start && <p><strong>Safe start:</strong> {displayDate(milestone.timing.conservative_latest_start)}</p>}
            {milestone.timing.last_plausible_start && <p><strong>Last plausible start:</strong> {displayDate(milestone.timing.last_plausible_start)}</p>}
            {milestone.timing.actionable_task_ids.length > 0 && <div><strong>Current actionable step</strong>{milestone.timing.actionable_task_ids.map((taskId) => taskById.get(taskId)).filter((task): task is RelocationTask => Boolean(task)).map((task) => <Button className="d-block p-0" key={task.id} variant="link" onClick={() => onTaskTargeted?.(task)}>{task.title}</Button>)}</div>}
            {milestone.timing.critical_path_task_ids.length > 0 && <div className="mt-2"><strong>Critical-path Tasks</strong>{milestone.timing.critical_path_task_ids.map((taskId) => taskById.get(taskId)).filter((task): task is RelocationTask => Boolean(task)).map((task) => <Button className="d-block p-0" key={task.id} variant="link" onClick={() => onTaskTargeted?.(task)}>{task.title}</Button>)}</div>}
            {milestone.timing.missing_duration_task_ids.length > 0 && <div className="mt-2"><strong>Missing estimates</strong>{milestone.timing.missing_duration_task_ids.map((taskId) => taskById.get(taskId)).filter((task): task is RelocationTask => Boolean(task)).map((task) => <div className="d-flex align-items-center justify-content-between gap-2" key={task.id}><span>{task.title}</span><Button size="sm" variant="outline-secondary" onClick={() => onTaskTargeted?.(task)}>Add estimate</Button></div>)}</div>}
            {milestone.timing.conflicts.map((conflict) => <Alert className="mt-2 mb-0" key={conflict} variant="warning">{conflict}</Alert>)}
            {milestone.timing.duration_min_days == null && milestone.timing.missing_duration_task_ids.length === 0 && milestone.timing.actionable_task_ids.length === 0 && milestone.timing.critical_path_task_ids.length === 0 && milestone.timing.conflicts.length === 0 && <p className="text-muted mb-0">Timing details are not available yet.</p>}
          </div>}
          </>}
        </div>}
        <p className="milestone-decision-summary text-muted mb-0">{decisions.length} {decisions.length === 1 ? 'Decision' : 'Decisions'} · {resolvedCount} resolved</p>
        {milestoneExpanded && <div id={`milestone-body-${milestone.id}`}>
        {milestone.description && <p className="mt-2">{milestone.description}</p>}
        <Stack direction="horizontal" gap={2} className="flex-wrap mt-2"><Button size="sm" variant="outline-secondary" onClick={() => { setDecisionDraft(null); setDecisionId(null); setMilestoneId(milestone.id); setMilestoneDraft({ title: milestone.title, description: milestone.description, target_earliest_date: milestone.target_earliest_date, target_latest_date: milestone.target_latest_date, timing_mode: milestone.timing_mode ?? 'target_window', governed_phase_id: milestone.governed_phase_id ?? null }) }}>Edit</Button><Button size="sm" variant={milestone.status === 'achieved' ? 'outline-secondary' : 'success'} disabled={pendingActions.has(`milestone-achievement-${milestone.id}`)} onClick={() => void perform(`milestone-achievement-${milestone.id}`, () => changeMilestoneAchievement(milestone.id, milestone.status !== 'achieved'))}>{milestone.status === 'achieved' ? 'Return to pending' : 'Mark achieved'}</Button></Stack>
        <Row className="decision-grid g-3 mt-0">{decisions.map((decision, decisionIndex) => {
          const decisionExpanded = expandedDecisions.has(decision.id)
          const preparationExpanded = expandedPreparation.has(decision.id)
          const fullRow = decisions.length === 1 || (decisions.length % 2 === 1 && decisionIndex === decisions.length - 1)
          return <Col className={`decision-column ${fullRow ? 'decision-column-full' : 'decision-column-paired'}`} xs={12} lg={fullRow ? 12 : 6} key={decision.id}><Card
          aria-labelledby={`decision-title-${decision.id}`}
          as="article"
          className={`decision-card plan-foundation-item ${foundItem?.type === 'decision' && foundItem.id === decision.id ? 'is-found' : ''}`}
          ref={(element: HTMLElement | null) => {
            if (element) itemRefs.current.set(`decision:${decision.id}`, element)
            else itemRefs.current.delete(`decision:${decision.id}`)
          }}
          tabIndex={-1}
        ><Card.Body>
          <div className="d-flex flex-wrap align-items-start justify-content-between gap-2">
            <button aria-controls={`decision-body-${decision.id}`} aria-expanded={decisionExpanded} className="foundation-expansion-toggle d-inline-flex align-items-center gap-2 p-0 text-start" onClick={() => setExpandedDecisions((current) => { const next = new Set(current); if (next.has(decision.id)) next.delete(decision.id); else next.add(decision.id); return next })} type="button"><Card.Title className="decision-title mb-0" as="h5" id={`decision-title-${decision.id}`}>{decision.title}</Card.Title><ExpansionChevron expanded={decisionExpanded} /></button>
            <span className="d-flex flex-wrap align-items-center gap-1"><Badge bg={decision.status === 'resolved' ? 'success' : 'warning'} text={decision.status === 'resolved' ? undefined : 'dark'}>{decision.status === 'resolved' ? 'Resolved' : 'Unresolved'}</Badge><Badge bg={decision.preparation_readiness === 'ready_to_decide' ? 'success' : 'secondary'}>{readinessLabel(decision)}</Badge><Button
              aria-expanded={readinessHelpDecisionId === decision.id}
              aria-label={`About ${readinessLabel(decision)}`}
              className="readiness-help-button d-inline-flex align-items-center justify-content-center rounded-circle p-0"
              onClick={() => readinessHelpDecisionId === decision.id ? closeReadinessHelp(decision.id) : setReadinessHelpDecisionId(decision.id)}
              onFocus={() => { if (!suppressReadinessHelpFocusRef.current) setReadinessHelpDecisionId(decision.id) }}
              ref={(element: HTMLButtonElement | null) => { if (element) readinessHelpRefs.current.set(decision.id, element); else readinessHelpRefs.current.delete(decision.id) }}
              size="sm"
              variant="outline-secondary"
            >i</Button><Overlay
              onHide={() => closeReadinessHelp(decision.id)}
              placement="bottom"
              rootClose
              show={readinessHelpDecisionId === decision.id}
              target={() => readinessHelpRefs.current.get(decision.id) ?? null}
            ><Popover id={`readiness-help-${decision.id}`}><Popover.Body>Preparation tasks are work you want completed before making this decision. GoTime uses their current status to estimate whether the decision is ready.</Popover.Body></Popover></Overlay></span>
          </div>
          {(decision.preparation_task_ids?.length ?? 0) > 0 && <>
            <Button aria-controls={`decision-preparation-list-${decision.id}`} aria-expanded={preparationExpanded} className="subtask-progress-toggle d-inline-flex align-items-center gap-1 p-0 mt-1 mb-1" variant="link" onClick={() => { setExpandedDecisions((current) => new Set(current).add(decision.id)); setExpandedPreparation((current) => { const next = new Set(current); if (next.has(decision.id)) next.delete(decision.id); else next.add(decision.id); return next }) }}>
              <span>{decision.completed_preparation_task_count ?? 0} of {decision.preparation_task_ids?.length ?? 0} preparation {(decision.preparation_task_ids?.length ?? 0) === 1 ? 'task' : 'tasks'} completed</span><ExpansionChevron expanded={preparationExpanded} />
            </Button>
          </>}
          {decisionExpanded && <div id={`decision-body-${decision.id}`}>
          {(decision.preparation_task_ids?.length ?? 0) === 0 && <p className="small text-muted mt-2 mb-2">Add tasks that should be completed before making this decision.</p>}
          {decision.description && <p className="plan-foundation-metadata mt-2">{decision.description}</p>}
          {decision.status === 'resolved' && decision.preparation_readiness === 'preparation_incomplete' && <Alert variant="warning">This decision is resolved, but its preparation is incomplete. Review the selected option if needed.</Alert>}
          {preparationExpanded && <div id={`decision-preparation-list-${decision.id}`} className="mb-2">{(decision.preparation_task_ids ?? []).map((taskId) => taskById.get(taskId)).filter((task): task is RelocationTask => Boolean(task)).map((task) => <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 border-top py-2" key={task.id}><span><strong className="d-block">{task.title}</strong><small className="text-muted">{phaseById.get(task.phase_id)?.title} · {task.status.replace('_', ' ')}</small></span><Button size="sm" variant="outline-secondary" onClick={() => { setExpandedMilestones((current) => new Set(current).add(milestone.id)); setExpandedDecisions((current) => new Set(current).add(decision.id)); window.requestAnimationFrame(() => onTaskTargeted?.(task)) }}>View task</Button></div>)}</div>}
          <div className="decision-controls"><Form.Group><Form.Label>Select an option</Form.Label><Form.Select aria-label={`Selection for ${decision.title}`} disabled={pendingActions.has(`decision-selection-${decision.id}`)} value={decision.selected_option_id ?? ''} onChange={(event) => { const optionId = event.target.value; if (!optionId) { void perform(`decision-selection-${decision.id}`, () => changeDecisionSelection(decision.id, null)); return } if (decision.preparation_readiness !== 'ready_to_decide') { setSelectionConfirmation({ decisionId: decision.id, optionId, returnFocus: event.currentTarget }); return } void perform(`decision-selection-${decision.id}`, () => changeDecisionSelection(decision.id, optionId)) }}><option value="">Unresolved</option>{decision.options.map((option) => <option key={option.id} value={option.id}>{option.title}</option>)}</Form.Select></Form.Group>
          <Button className="mt-2" size="sm" variant="outline-secondary" onClick={() => { setMilestoneDraft(null); setMilestoneId(null); setDecisionId(decision.id); setDecisionDraft({ title: decision.title, description: decision.description, milestone_id: decision.milestone_id, options: decision.options, preparation_task_ids: decision.preparation_task_ids ?? [] }) }}>Edit decision</Button></div>
          </div>}
        </Card.Body></Card></Col>
        })}</Row>
        </div>}
      </Card.Body></Card></Col>
      })}</Row>
      <Modal centered onHide={() => { const focus = selectionConfirmation?.returnFocus; setSelectionConfirmation(null); window.requestAnimationFrame(() => focus?.focus()) }} show={Boolean(selectionConfirmation)}>
        <Modal.Header closeButton><Modal.Title as="h2">Decide before preparation is complete?</Modal.Title></Modal.Header>
        <Modal.Body>Some tracked preparation work is incomplete. Selecting an option is still allowed, but readiness does not endorse the choice.</Modal.Body>
        <Modal.Footer><Button variant="outline-secondary" onClick={() => { const focus = selectionConfirmation?.returnFocus; setSelectionConfirmation(null); window.requestAnimationFrame(() => focus?.focus()) }}>Cancel</Button><Button onClick={() => { if (!selectionConfirmation) return; const request = selectionConfirmation; setSelectionConfirmation(null); void perform(`decision-selection-${request.decisionId}`, () => changeDecisionSelection(request.decisionId, request.optionId, true)) }}>Select option anyway</Button></Modal.Footer>
      </Modal>
    </section>
  )
}
