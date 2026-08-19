import { useEffect, useState } from 'react'
import { Alert, Badge, ListGroup, Spinner } from 'react-bootstrap'
import {
  fetchRelocationTaskRecommendation,
  type RelocationTaskRecommendation,
} from './api/relocationPlan'
import { RelocationPlan } from './RelocationPlan'

function NextTaskRecommendation({ refreshKey }: { refreshKey: number }) {
  const [recommendation, setRecommendation] =
    useState<RelocationTaskRecommendation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    let isCurrentRequest = true
    setLoading(true)
    setError(null)
    fetchRelocationTaskRecommendation(controller.signal)
      .then((nextRecommendation) => {
        if (isCurrentRequest) setRecommendation(nextRecommendation)
      })
      .catch((requestError: unknown) => {
        if (isCurrentRequest) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Unable to load the next-task recommendation.',
          )
        }
      })
      .finally(() => {
        if (isCurrentRequest) setLoading(false)
      })
    return () => {
      isCurrentRequest = false
      controller.abort()
    }
  }, [refreshKey])

  return (
    <section
      className="next-step primary-recommendation mx-2 mx-sm-0 mt-5 p-4 rounded-4"
      aria-labelledby="stored-next-task-heading"
    >
      <p className="section-label mb-2">Primary recommendation</p>
      {loading && (
        <div role="status">
          <Spinner animation="border" size="sm" /> Loading next task…
        </div>
      )}
      {error && <Alert variant="danger">{error}</Alert>}
      {!loading && !error && recommendation?.status === 'no_actionable_task' && (
        <>
          <h2 className="step-name" id="stored-next-task-heading">
            No task is actionable right now
          </h2>
          <p>{recommendation.why_now}</p>
          <p className="mb-0 text-muted">{recommendation.why.join(' ')}</p>
        </>
      )}
      {!loading && !error && recommendation?.status === 'recommended' && (
        <>
          <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
            <h2 className="step-name mb-0" id="stored-next-task-heading">
              {recommendation.task_title}
            </h2>
            <Badge bg="light" text="dark">{recommendation.phase_title}</Badge>
          </div>
          <ListGroup as="ul" className="detail-list mb-3" variant="flush">
            {recommendation.why.map((reason) => (
              <ListGroup.Item as="li" className="px-0 py-1" key={reason}>
                {reason}
              </ListGroup.Item>
            ))}
          </ListGroup>
          <p className="mb-0"><strong>Why now:</strong> {recommendation.why_now}</p>
        </>
      )}
    </section>
  )
}

export function RelocationPlanExperience() {
  const [recommendationRevision, setRecommendationRevision] = useState(0)

  return (
    <>
      <NextTaskRecommendation refreshKey={recommendationRevision} />
      <RelocationPlan
        onPlanChanged={() => setRecommendationRevision((revision) => revision + 1)}
      />
    </>
  )
}
