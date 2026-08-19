import { useState } from 'react'
import { Alert, Badge, Button, Card, Col, Form, Row, Stack } from 'react-bootstrap'
import {
  changeDecisionSelection,
  changeMilestoneAchievement,
  createDecision,
  createMilestone,
  replaceDecision,
  replaceMilestone,
  type Decision,
  type DecisionOption,
  type Milestone,
  type RelocationPlan,
} from './api/relocationPlan'

interface Props {
  plan: RelocationPlan
  onPlanUpdated: (plan: RelocationPlan) => void
}

type MilestoneDraft = Pick<Milestone, 'title' | 'description' | 'target_earliest_date' | 'target_latest_date'>
type DecisionDraft = Pick<Decision, 'title' | 'description' | 'milestone_id' | 'options'>

const emptyMilestone = (): MilestoneDraft => ({
  title: '', description: '', target_earliest_date: null, target_latest_date: null,
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

export function formatMilestoneTiming(milestone: Pick<Milestone, 'target_earliest_date' | 'target_latest_date'>) {
  const earliest = milestone.target_earliest_date
  const latest = milestone.target_latest_date
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

export function MilestoneDecisionFoundation({ plan, onPlanUpdated }: Props) {
  const [milestoneDraft, setMilestoneDraft] = useState<MilestoneDraft | null>(null)
  const [milestoneId, setMilestoneId] = useState<string | null>(null)
  const [decisionDraft, setDecisionDraft] = useState<DecisionDraft | null>(null)
  const [decisionId, setDecisionId] = useState<string | null>(null)
  const [pendingActions, setPendingActions] = useState<Set<string>>(new Set())
  const [error, setError] = useState<string | null>(null)

  async function perform(key: string, action: () => Promise<RelocationPlan>) {
    setPendingActions((current) => new Set(current).add(key))
    setError(null)
    try { onPlanUpdated(await action()); return true }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to update the plan.'); return false }
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
    if (
      milestoneDraft.target_earliest_date
      && milestoneDraft.target_latest_date
      && milestoneDraft.target_latest_date < milestoneDraft.target_earliest_date
    ) return
    const write = { ...milestoneDraft, description: milestoneDraft.description?.trim() || null }
    const saved = await perform('save-milestone', () => milestoneId
      ? replaceMilestone(milestoneId, write)
      : createMilestone(itemId(write.title, 'milestone'), write))
    if (!saved) return
    setMilestoneDraft(null)
    setMilestoneId(null)
  }

  async function saveDecision() {
    if (!decisionDraft) return
    const write = {
      ...decisionDraft,
      description: decisionDraft.description?.trim() || null,
      options: decisionDraft.options.map((option) => ({
        ...option, title: option.title.trim(), description: option.description?.trim() || null,
      })),
    }
    const saved = await perform('save-decision', () => decisionId
      ? replaceDecision(decisionId, write)
      : createDecision(itemId(write.title, 'decision'), write))
    if (!saved) return
    setDecisionDraft(null)
    setDecisionId(null)
  }

  const invalidTargetWindow = Boolean(
    milestoneDraft?.target_earliest_date
    && milestoneDraft.target_latest_date
    && milestoneDraft.target_latest_date < milestoneDraft.target_earliest_date,
  )

  return (
    <section className="plan-foundation mb-4" aria-labelledby="plan-foundation-heading">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h4 className="h4 mb-0" id="plan-foundation-heading">Milestones and decisions</h4>
        <Stack direction="horizontal" gap={2}>
          <Button size="sm" variant="outline-primary" onClick={() => { setMilestoneId(null); setMilestoneDraft(emptyMilestone()) }}>Add milestone</Button>
          <Button size="sm" variant="outline-primary" disabled={plan.milestones.length === 0} onClick={() => { setDecisionId(null); setDecisionDraft({ title: '', description: '', milestone_id: plan.milestones[0].id, options: [newOption(), newOption()] }) }}>Add decision</Button>
        </Stack>
      </div>
      {error && <Alert variant="danger">{error}</Alert>}

      {milestoneDraft && <Card className="plan-foundation-card mb-3"><Card.Body>
        <Card.Title className="plan-foundation-title">{milestoneId ? 'Edit milestone' : 'Add milestone'}</Card.Title>
        <Form onSubmit={(event) => { event.preventDefault(); void saveMilestone() }}>
          <Row className="g-3">
            <Col xs={12}><Form.Group controlId="milestone-title"><Form.Label>Name</Form.Label><Form.Control required maxLength={200} value={milestoneDraft.title} onChange={(event) => setMilestoneDraft({ ...milestoneDraft, title: event.target.value })} /></Form.Group></Col>
            <Col xs={12}><Form.Group controlId="milestone-description"><Form.Label>Description <span className="text-muted">(optional)</span></Form.Label><Form.Control as="textarea" maxLength={2000} value={milestoneDraft.description ?? ''} onChange={(event) => setMilestoneDraft({ ...milestoneDraft, description: event.target.value })} /></Form.Group></Col>
            <Col sm={6}><Form.Group controlId="milestone-earliest"><Form.Label>Earliest target date <span className="text-muted">(optional)</span></Form.Label><Form.Control type="date" value={milestoneDraft.target_earliest_date ?? ''} onChange={(event) => setMilestoneDraft({ ...milestoneDraft, target_earliest_date: event.target.value || null })} /><Form.Text>Planning guidance; not a task start date.</Form.Text></Form.Group></Col>
            <Col sm={6}><Form.Group controlId="milestone-latest"><Form.Label>Latest target date <span className="text-muted">(optional)</span></Form.Label><Form.Control aria-describedby="milestone-latest-help" isInvalid={invalidTargetWindow} min={milestoneDraft.target_earliest_date ?? undefined} type="date" value={milestoneDraft.target_latest_date ?? ''} onChange={(event) => setMilestoneDraft({ ...milestoneDraft, target_latest_date: event.target.value || null })} /><Form.Control.Feedback type="invalid">Latest target must be on or after the earliest target.</Form.Control.Feedback><Form.Text id="milestone-latest-help">Leave blank for an open-ended “on or after” target.</Form.Text></Form.Group></Col>
          </Row>
          <Stack direction="horizontal" gap={2} className="mt-3"><Button type="submit" disabled={pendingActions.has('save-milestone') || invalidTargetWindow}>Save milestone</Button><Button variant="outline-secondary" onClick={() => setMilestoneDraft(null)}>Cancel</Button></Stack>
        </Form>
      </Card.Body></Card>}

      {decisionDraft && <Card className="plan-foundation-card mb-3"><Card.Body>
        <Card.Title className="plan-foundation-title">{decisionId ? 'Edit decision' : 'Add decision'}</Card.Title>
        <Form onSubmit={(event) => { event.preventDefault(); void saveDecision() }}>
          <Row className="g-3">
            <Col md={8}><Form.Group controlId="decision-title"><Form.Label>Decision</Form.Label><Form.Control required maxLength={200} value={decisionDraft.title} onChange={(event) => setDecisionDraft({ ...decisionDraft, title: event.target.value })} /></Form.Group></Col>
            <Col md={4}><Form.Group controlId="decision-milestone"><Form.Label>Milestone</Form.Label><Form.Select value={decisionDraft.milestone_id} onChange={(event) => setDecisionDraft({ ...decisionDraft, milestone_id: event.target.value })}>{plan.milestones.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</Form.Select></Form.Group></Col>
            <Col xs={12}><Form.Group controlId="decision-description"><Form.Label>Context <span className="text-muted">(optional)</span></Form.Label><Form.Control as="textarea" maxLength={2000} value={decisionDraft.description ?? ''} onChange={(event) => setDecisionDraft({ ...decisionDraft, description: event.target.value })} /></Form.Group></Col>
            <Col xs={12}><Form.Label>Options</Form.Label>{decisionDraft.options.map((option, index) => <div className="decision-option-row d-flex flex-wrap flex-sm-nowrap gap-2 mb-2" key={option.id}><Form.Control className="decision-option-input" aria-label={`Option ${index + 1}`} required maxLength={200} value={option.title} onChange={(event) => setDecisionDraft({ ...decisionDraft, options: decisionDraft.options.map((item, itemIndex) => itemIndex === index ? { ...item, title: event.target.value } : item) })} /><Button aria-label={`Move option ${index + 1} up`} disabled={index === 0} variant="outline-secondary" onClick={() => { const options = [...decisionDraft.options]; [options[index - 1], options[index]] = [options[index], options[index - 1]]; setDecisionDraft({ ...decisionDraft, options }) }}>↑</Button><Button aria-label={`Remove option ${index + 1}`} disabled={decisionDraft.options.length <= 2 || option.id === plan.decisions.find((item) => item.id === decisionId)?.selected_option_id} variant="outline-secondary" onClick={() => setDecisionDraft({ ...decisionDraft, options: decisionDraft.options.filter((_, itemIndex) => itemIndex !== index) })}>Remove</Button></div>)}</Col>
          </Row>
          <Button size="sm" variant="outline-secondary" onClick={() => setDecisionDraft({ ...decisionDraft, options: [...decisionDraft.options, newOption()] })}>Add option</Button>
          <Stack direction="horizontal" gap={2} className="mt-3"><Button type="submit" disabled={pendingActions.has('save-decision')}>Save decision</Button><Button variant="outline-secondary" onClick={() => setDecisionDraft(null)}>Cancel</Button></Stack>
        </Form>
      </Card.Body></Card>}

      {plan.milestones.length === 0 && !milestoneDraft && <p className="text-muted">No milestones yet.</p>}
      <Row className="g-3">{plan.milestones.map((milestone) => <Col lg={6} key={milestone.id}><Card className="plan-foundation-card h-100"><Card.Body>
        <div className="d-flex flex-wrap align-items-start justify-content-between gap-2"><Card.Title className="plan-foundation-title" as="h4">{milestone.title}</Card.Title><Badge className="align-self-start flex-shrink-0" bg={milestone.status === 'achieved' ? 'success' : 'secondary'}>{milestone.status === 'achieved' ? 'Achieved' : 'Pending'}</Badge></div>
        <p className="plan-foundation-metadata text-muted">{formatMilestoneTiming(milestone)}</p>{milestone.description && <p>{milestone.description}</p>}
        <Stack direction="horizontal" gap={2} className="flex-wrap"><Button size="sm" variant="outline-secondary" onClick={() => { setMilestoneId(milestone.id); setMilestoneDraft({ title: milestone.title, description: milestone.description, target_earliest_date: milestone.target_earliest_date, target_latest_date: milestone.target_latest_date }) }}>Edit</Button><Button size="sm" variant={milestone.status === 'achieved' ? 'outline-secondary' : 'success'} disabled={pendingActions.has(`milestone-achievement-${milestone.id}`)} onClick={() => void perform(`milestone-achievement-${milestone.id}`, () => changeMilestoneAchievement(milestone.id, milestone.status !== 'achieved'))}>{milestone.status === 'achieved' ? 'Return to pending' : 'Mark achieved'}</Button></Stack>
        {plan.decisions.filter((decision) => decision.milestone_id === milestone.id).map((decision) => <Card className="decision-card mt-3" key={decision.id}><Card.Body><div className="d-flex flex-wrap align-items-start justify-content-between gap-2"><Card.Title className="decision-title" as="h5">{decision.title}</Card.Title><Badge className="align-self-start flex-shrink-0" bg={decision.status === 'resolved' ? 'success' : 'warning'} text={decision.status === 'resolved' ? undefined : 'dark'}>{decision.status === 'resolved' ? 'Resolved' : 'Unresolved'}</Badge></div>{decision.description && <p className="plan-foundation-metadata">{decision.description}</p>}<Form.Group><Form.Label>Select an option</Form.Label><Form.Select aria-label={`Selection for ${decision.title}`} disabled={pendingActions.has(`decision-selection-${decision.id}`)} value={decision.selected_option_id ?? ''} onChange={(event) => void perform(`decision-selection-${decision.id}`, () => changeDecisionSelection(decision.id, event.target.value || null))}><option value="">Unresolved</option>{decision.options.map((option) => <option key={option.id} value={option.id}>{option.title}</option>)}</Form.Select></Form.Group><Button className="mt-2" size="sm" variant="outline-secondary" onClick={() => { setDecisionId(decision.id); setDecisionDraft({ title: decision.title, description: decision.description, milestone_id: decision.milestone_id, options: decision.options }) }}>Edit decision</Button></Card.Body></Card>)}
      </Card.Body></Card></Col>)}</Row>
    </section>
  )
}
