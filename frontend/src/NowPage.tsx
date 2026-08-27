import { useEffect, useLayoutEffect, useState } from 'react'
import { Alert, Spinner } from 'react-bootstrap'
import { useNavigate } from 'react-router'
import { NextTaskRecommendation } from './NextTaskRecommendation'
import { fetchRelocationPlan } from './api/relocationPlan'
import { useFind } from './FindContext'

export function NowPage() {
  const navigate = useNavigate()
  const { selectTarget } = useFind()
  const [planTitle, setPlanTitle] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    fetchRelocationPlan(controller.signal)
      .then((plan) => setPlanTitle(plan.title))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Unable to load the plan.')
        }
      })
    return () => controller.abort()
  }, [])

  return (
    <>
      <div className="page-intro px-2 px-sm-0">
        <header className="border-bottom pb-5">
          <p className="eyebrow mb-2">GoTime</p>
          <h1 className="page-title mb-0">What should I do next?</h1>
        </header>
        <section className="pt-5" aria-labelledby="goal-heading">
          <p className="section-label mb-2" id="goal-heading">Our goal</p>
          {error && <Alert variant="danger">{error}</Alert>}
          {!error && !planTitle && <div role="status"><Spinner size="sm" /> Loading goal…</div>}
          {planTitle && <p className="goal-name mb-0">{planTitle}</p>}
        </section>
      </div>
      <NextTaskRecommendation
        onViewDecision={(decisionId) => {
          selectTarget({ decisionId, source: 'recommendation' })
          navigate('/plan')
        }}
        onViewTask={(taskId) => {
          selectTarget({ taskId, source: 'recommendation' })
          navigate('/plan')
        }}
        refreshKey={0}
      />
    </>
  )
}
