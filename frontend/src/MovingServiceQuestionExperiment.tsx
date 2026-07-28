import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Card, Form, Spinner } from 'react-bootstrap'
import {
  fetchMovingServiceQuestion,
  type ExperimentFixture,
  type MovingServiceQuestionExperimentResult,
} from './api/movingServiceQuestions'

interface MovingServiceQuestionExperimentProps {
  fixture?: ExperimentFixture
}

type BooleanAnswer = 'yes' | 'no'

export function MovingServiceQuestionExperiment({
  fixture = 'storage_unknown',
}: MovingServiceQuestionExperimentProps) {
  const [result, setResult] =
    useState<MovingServiceQuestionExperimentResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDismissed, setIsDismissed] = useState(false)
  const [showGrounding, setShowGrounding] = useState(false)
  const [showAnswer, setShowAnswer] = useState(false)
  const [draftAnswer, setDraftAnswer] = useState<BooleanAnswer | ''>('')
  const [locallyConfirmedAnswer, setLocallyConfirmedAnswer] =
    useState<BooleanAnswer | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  const requestIdRef = useRef(0)

  useEffect(() => {
    controllerRef.current?.abort()
    requestIdRef.current += 1
    setResult(null)
    setError(null)
    setIsLoading(false)
    setIsDismissed(false)
    setShowGrounding(false)
    setShowAnswer(false)
    setDraftAnswer('')
    setLocallyConfirmedAnswer(null)

    return () => {
      controllerRef.current?.abort()
    }
  }, [fixture])

  const requestSuggestion = () => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    controllerRef.current = controller

    setResult(null)
    setError(null)
    setIsDismissed(false)
    setShowGrounding(false)
    setShowAnswer(false)
    setDraftAnswer('')
    setLocallyConfirmedAnswer(null)
    setIsLoading(true)

    fetchMovingServiceQuestion(fixture, controller.signal)
      .then((nextResult) => {
        if (requestIdRef.current === requestId) {
          setResult(nextResult)
        }
      })
      .catch((requestError: unknown) => {
        if (
          requestIdRef.current === requestId &&
          !controller.signal.aborted
        ) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Unable to load the experimental suggestion.',
          )
        }
      })
      .finally(() => {
        if (requestIdRef.current === requestId) {
          setIsLoading(false)
        }
      })
  }

  const suggestion = result?.suggestion
  const sourceLabel =
    result?.source === 'deterministic_fallback'
      ? 'Suggested from GoTime’s planning guide'
      : 'Experimental suggestion'

  return (
    <section
      className="moving-service-experiment mt-4"
      aria-labelledby="moving-service-experiment-heading"
    >
      <div className="d-flex align-items-start justify-content-between gap-3">
        <div>
          <p className="section-label mb-1">Optional experiment</p>
          <h2
            className="detail-heading mb-2"
            id="moving-service-experiment-heading"
          >
            Something else worth clarifying
          </h2>
          <p className="text-body-secondary mb-0">
            Try a bounded question suggestion from GoTime’s moving-service
            experiment.
          </p>
        </div>
        {!isLoading && !suggestion && !result && (
          <Button
            onClick={requestSuggestion}
            type="button"
            variant="outline-success"
          >
            Get a suggested question
          </Button>
        )}
      </div>

      {isLoading && (
        <div className="loading-state mt-3" role="status">
          <Spinner animation="border" className="me-2" size="sm" />
          Loading experimental suggestion…
        </div>
      )}

      {error && (
        <Alert className="mt-3 mb-0" variant="warning">
          <Alert.Heading as="h3">Suggestion unavailable</Alert.Heading>
          <p className="mb-3">{error}</p>
          <Button
            onClick={requestSuggestion}
            type="button"
            variant="outline-dark"
          >
            Try again
          </Button>
        </Alert>
      )}

      {result && !suggestion && (
        <p className="text-body-secondary mt-3 mb-0">
          {result.no_question_reason}
        </p>
      )}

      {suggestion && !isDismissed && (
        <Card className="experiment-suggestion mt-3 border-0">
          <Card.Body className="p-4">
            <p className="section-label mb-2">{sourceLabel}</p>
            <h3 className="experiment-question mb-3">
              {suggestion.question}
            </h3>
            <p>{suggestion.why_it_matters}</p>

            {showGrounding && (
              <div className="experiment-grounding mb-3 p-3 rounded-3">
                <p className="fw-semibold mb-2">Why GoTime is asking</p>
                {suggestion.grounding_details.length > 0 ? (
                  suggestion.grounding_details.map((detail) => (
                    <p className="mb-0" key={detail}>
                      {detail}
                    </p>
                  ))
                ) : (
                  <p className="mb-0">
                    This question comes from GoTime’s deterministic planning
                    guide.
                  </p>
                )}
              </div>
            )}

            {showAnswer && suggestion.answer_type === 'boolean' && (
              <Form
                className="experiment-answer mb-3"
                onSubmit={(event) => {
                  event.preventDefault()
                  if (draftAnswer) {
                    setLocallyConfirmedAnswer(draftAnswer)
                  }
                }}
              >
                <fieldset>
                  <legend className="fs-6 fw-semibold">
                    Your answer for this demonstration
                  </legend>
                  <Form.Check
                    checked={draftAnswer === 'yes'}
                    id="moving-service-answer-yes"
                    label="Yes"
                    name="moving-service-answer"
                    onChange={() => setDraftAnswer('yes')}
                    type="radio"
                  />
                  <Form.Check
                    checked={draftAnswer === 'no'}
                    id="moving-service-answer-no"
                    label="No"
                    name="moving-service-answer"
                    onChange={() => setDraftAnswer('no')}
                    type="radio"
                  />
                </fieldset>
                <Button
                  className="mt-3"
                  disabled={!draftAnswer}
                  type="submit"
                  variant="outline-success"
                >
                  Confirm for this demonstration
                </Button>
              </Form>
            )}

            {locallyConfirmedAnswer && (
              <Alert className="mb-3" variant="info">
                Answer confirmed locally for this experiment. Trusted GoTime
                state was not changed.
              </Alert>
            )}

            <div className="d-flex flex-wrap gap-2">
              <Button
                onClick={() => setShowAnswer(true)}
                type="button"
                variant="success"
              >
                Answer this
              </Button>
              <Button
                onClick={() => setIsDismissed(true)}
                type="button"
                variant="outline-secondary"
              >
                Not relevant
              </Button>
              <Button
                aria-expanded={showGrounding}
                onClick={() => setShowGrounding((isShown) => !isShown)}
                type="button"
                variant="link"
              >
                Why are you asking?
              </Button>
            </div>
          </Card.Body>
        </Card>
      )}

      {suggestion && isDismissed && (
        <p className="text-body-secondary mt-3 mb-0">
          Suggestion dismissed. No GoTime state was changed.
        </p>
      )}
    </section>
  )
}
