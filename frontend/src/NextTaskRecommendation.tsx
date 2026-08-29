import { useEffect, useState } from 'react'
import { Alert, Badge, Button, ListGroup, Spinner } from 'react-bootstrap'
import {
  fetchRelocationTaskRecommendation,
  viewerLocalEvaluationDate,
  type RecommendationItem,
  type RecommendationSignal,
  type RelocationTaskRecommendation,
} from './api/relocationPlan'

const label = (value: string) => value.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase())

const redundantReason = (reason: string) =>
  /^Its user priority is .+\.$/.test(reason)
  || reason === 'It is actionable and has no later start-date restriction.'

const redundantWhyNow = (whyNow: string) =>
  whyNow === 'It advances preparation for an unresolved decision.'
  || whyNow === 'This unresolved decision is ready for your review.'
  || whyNow === 'It is available to work on now.'
  || whyNow === 'It is available to work on now and has no incomplete prerequisites.'

export function visibleRecommendationReasons(
  item: RecommendationItem,
  relationshipContextVisible: boolean,
): string[] {
  const decisionTitles = new Set((item.signals ?? [])
    .filter((signal) => signal.kind !== 'ready_to_decide')
    .map((signal) => signal.decision_title))
  return item.why.filter((reason) => {
    if (redundantReason(reason)) return false
    if (!relationshipContextVisible) return true
    return ![...decisionTitles].some((title) => reason === `Helps prepare ${title}.`)
  })
}

function DecisionContextButton({ signal, onViewDecision }: { signal: RecommendationSignal; onViewDecision?: (decisionId: string) => void }) {
  if (!onViewDecision) return <>{signal.decision_title}</>
  return <Button className="p-0 align-baseline" onClick={(event) => { event.stopPropagation(); onViewDecision(signal.decision_id) }} variant="link">{signal.decision_title}</Button>
}

function ParentContextButton({ signal, onViewTask }: { signal: RecommendationSignal; onViewTask?: (taskId: string) => void }) {
  if (!signal.parent_task_id || !signal.parent_task_title || !onViewTask) return <>{signal.parent_task_title}</>
  return <Button aria-label={`View parent task ${signal.parent_task_title}`} className="p-0 align-baseline" onClick={(event) => { event.stopPropagation(); onViewTask(signal.parent_task_id!) }} variant="link">{signal.parent_task_title}</Button>
}

function SignalContext({ signals, onViewDecision, onViewTask }: { signals: RecommendationSignal[]; onViewDecision?: (decisionId: string) => void; onViewTask?: (taskId: string) => void }) {
  if (signals.length === 0) return null
  if (signals.length > 1) {
    return (
      <details className="recommendation-context mt-2">
        <summary>Helps prepare {signals.length} decisions</summary>
        <ul className="mb-0 mt-2">
          {signals.map((signal) => <li key={signal.decision_id}><DecisionContextButton onViewDecision={onViewDecision} signal={signal} /></li>)}
        </ul>
      </details>
    )
  }
  const signal = signals[0]
  if (signal.kind === 'inherited_decision_preparation') {
    return <div className="mt-2"><div><strong>Part of:</strong> <ParentContextButton onViewTask={onViewTask} signal={signal} /></div><div><strong>Helps prepare:</strong> <DecisionContextButton onViewDecision={onViewDecision} signal={signal} /></div></div>
  }
  if (signal.kind === 'unblocks_decision_preparation') {
    return <div className="mt-2"><div><strong>Unblocks:</strong> {signal.blocked_task_title}</div><div><strong>Helps prepare:</strong> <DecisionContextButton onViewDecision={onViewDecision} signal={signal} /></div></div>
  }
  if (signal.kind === 'direct_decision_preparation') {
    return <p className="mt-2 mb-0"><strong>Helps prepare:</strong> <DecisionContextButton onViewDecision={onViewDecision} signal={signal} /></p>
  }
  return null
}

function RecommendationCard({
  item,
  position,
  onViewDecision,
  onViewTask,
}: {
  item: RecommendationItem
  position: 'primary' | 'upcoming'
  onViewDecision?: (decisionId: string) => void
  onViewTask?: (taskId: string) => void
}) {
  const isDecision = item.candidate_type === 'decision'
  const headingId = `${position}-recommendation-${item.decision_id ?? item.task_id ?? 'item'}`
  const meaningfulReasons = visibleRecommendationReasons(item, !isDecision && (item.signals?.length ?? 0) > 0)
  return (
    <article
      aria-labelledby={headingId}
      className={`${position === 'primary' ? 'primary-recommendation' : 'upcoming-recommendation border rounded-3'} mx-2 mx-sm-0 ${position === 'primary' ? 'mt-5 p-4 rounded-4' : 'p-3'}`}
    >
      <p className="section-label mb-2">{position === 'primary' ? 'Primary recommendation' : 'Upcoming'}</p>
      {isDecision ? (
        <>
          <h2 className="step-name mb-1" id={headingId}>Make a decision</h2>
          <p className="h5 mb-3">{item.decision_title}</p>
          <p>{meaningfulReasons[0] ?? 'All currently tracked preparation work is complete.'}</p>
          {item.decision_id && onViewDecision && <Button className="recommendation-task-link mt-3" onClick={() => onViewDecision(item.decision_id!)}>Review decision</Button>}
        </>
      ) : (
        <>
          <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
            <h2 className="step-name mb-0" id={headingId}>{item.task_title}</h2>
            {item.phase_title && <Badge bg="light" text="dark">{item.phase_title}</Badge>}
          </div>
          {item.task_metadata && (
            <p className="small text-muted mb-2">
              {label(item.task_metadata.status)} · {label(item.task_metadata.priority)} priority
              {item.task_metadata.assignees.length > 0 ? ` · ${item.task_metadata.assignees.join(', ')}` : ' · Unassigned'}
              {item.task_metadata.categories.length > 0 ? ` · ${item.task_metadata.categories.map(label).join(', ')}` : ''}
              {item.task_metadata.due_date ? ` · Due ${item.task_metadata.due_date}` : ''}
            </p>
          )}
          {meaningfulReasons.length > 0 && <ListGroup as="ul" className="detail-list mb-3" variant="flush">
            {meaningfulReasons.map((reason) => <ListGroup.Item as="li" className="px-0 py-1" key={reason}>{reason}</ListGroup.Item>)}
          </ListGroup>}
          <SignalContext onViewDecision={onViewDecision} onViewTask={onViewTask} signals={item.signals ?? []} />
          {item.why_now && !redundantWhyNow(item.why_now) && (item.signals?.length ?? 0) === 0 && <p className="mt-2 mb-0"><strong>Why now:</strong> {item.why_now}</p>}
          {item.task_id && onViewTask && <Button className="recommendation-task-link mt-3" onClick={() => onViewTask(item.task_id!)}>View task</Button>}
        </>
      )}
    </article>
  )
}

export function NextTaskRecommendation({
  onViewDecision,
  onViewTask,
  refreshKey,
}: {
  onViewDecision?: (decisionId: string) => void
  onViewTask?: (taskId: string) => void
  refreshKey: number
}) {
  const [recommendation, setRecommendation] = useState<RelocationTaskRecommendation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [evaluationDate, setEvaluationDate] = useState(viewerLocalEvaluationDate)

  useEffect(() => {
    const refreshDate = () => {
      const nextDate = viewerLocalEvaluationDate()
      setEvaluationDate((current) => current === nextDate ? current : nextDate)
    }
    const now = new Date()
    const nextMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1)
    const timer = window.setTimeout(refreshDate, nextMidnight.getTime() - now.getTime() + 100)
    const onVisibilityChange = () => { if (!document.hidden) refreshDate() }
    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => { window.clearTimeout(timer); document.removeEventListener('visibilitychange', onVisibilityChange) }
  }, [evaluationDate])

  useEffect(() => {
    const controller = new AbortController()
    let current = true
    setLoading(true)
    setError(null)
    fetchRelocationTaskRecommendation(controller.signal, evaluationDate)
      .then((next) => { if (current) setRecommendation(next) })
      .catch((reason: unknown) => { if (current) setError(reason instanceof Error ? reason.message : 'Unable to load the next recommendation.') })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false; controller.abort() }
  }, [evaluationDate, refreshKey])

  const primary: RecommendationItem | null = recommendation?.status === 'recommended' ? {
    candidate_type: recommendation.candidate_type ?? 'task',
    task_id: recommendation.task_id, task_title: recommendation.task_title,
    decision_id: recommendation.decision_id, decision_title: recommendation.decision_title,
    phase_id: recommendation.phase_id, phase_title: recommendation.phase_title,
    why: recommendation.why, why_now: recommendation.why_now,
    directly_unblocks_task_ids: recommendation.directly_unblocks_task_ids,
    signals: recommendation.signals, task_metadata: recommendation.task_metadata,
    ranking_factors: recommendation.ranking_factors,
  } : null

  return (
    <section className="next-step" aria-label="Recommendations">
      {loading && <div className="mx-2 mx-sm-0 mt-5" role="status"><Spinner animation="border" size="sm" /> Loading next task…</div>}
      {error && <Alert className="mx-2 mx-sm-0 mt-5" variant="danger">{error}</Alert>}
      {!loading && !error && recommendation?.status === 'no_actionable_task' && (
        <div className="primary-recommendation mx-2 mx-sm-0 mt-5 p-4 rounded-4">
          <p className="section-label mb-2">Primary recommendation</p>
          <h2 className="step-name">No task is actionable right now</h2>
          <p>{recommendation.why_now}</p><p className="mb-0 text-muted">{recommendation.why.join(' ')}</p>
        </div>
      )}
      {!loading && !error && primary && <RecommendationCard item={primary} onViewDecision={onViewDecision} onViewTask={onViewTask} position="primary" />}
      {!loading && !error && (recommendation?.upcoming?.length ?? 0) > 0 && (
        <div className="upcoming-recommendations mx-2 mx-sm-0 mt-4 d-grid gap-3" aria-label="Upcoming recommendations">
          {recommendation!.upcoming!.map((item) => <RecommendationCard item={item} key={`${item.candidate_type}-${item.decision_id ?? item.task_id}`} onViewDecision={onViewDecision} onViewTask={onViewTask} position="upcoming" />)}
        </div>
      )}
    </section>
  )
}
