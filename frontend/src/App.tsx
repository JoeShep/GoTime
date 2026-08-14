import { useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Container,
  Form,
  InputGroup,
  ListGroup,
  Row,
  Spinner,
} from 'react-bootstrap'
import {
  fetchPrimaryRecommendation,
  LIKELY_WORKPLACE_AREA_MAX_LENGTH,
  type CommuteTravelMode,
  type Recommendation,
  type WorkArrangement,
} from './api/recommendations'
import { MovingServiceQuestionExperiment } from './MovingServiceQuestionExperiment'
import { RelocationPlan } from './RelocationPlan'

const workArrangementLabels: Record<WorkArrangement, string> = {
  remote: 'Remote',
  hybrid: 'Hybrid',
  on_site: 'On-site',
  flexible: 'Flexible',
}

const commuteTravelModeLabels: Record<CommuteTravelMode, string> = {
  drive: 'Drive',
  public_transit: 'Public transit',
  either: 'Either driving or public transit',
}

function isWorkArrangement(value: string): value is WorkArrangement {
  return value in workArrangementLabels
}

function requiresCommuteLimit(workArrangement: WorkArrangement | null): boolean {
  return workArrangement === 'hybrid' || workArrangement === 'on_site'
}

function isCommuteTravelMode(value: string): value is CommuteTravelMode {
  return value in commuteTravelModeLabels
}

function App() {
  const [draftWorkArrangement, setDraftWorkArrangement] = useState<WorkArrangement | ''>('')
  const [submittedWorkArrangement, setSubmittedWorkArrangement] =
    useState<WorkArrangement | null>(null)
  const [draftCommuteMinutes, setDraftCommuteMinutes] = useState('')
  const [submittedCommuteMinutes, setSubmittedCommuteMinutes] =
    useState<number | null>(null)
  const [draftWorkplaceArea, setDraftWorkplaceArea] = useState('')
  const [submittedWorkplaceArea, setSubmittedWorkplaceArea] =
    useState<string | null>(null)
  const [draftTravelMode, setDraftTravelMode] = useState<CommuteTravelMode | ''>('')
  const [submittedTravelMode, setSubmittedTravelMode] =
    useState<CommuteTravelMode | null>(null)
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    let isCurrentRequest = true

    setRecommendation(null)
    setError(null)
    setIsLoading(true)

    fetchPrimaryRecommendation(
      submittedWorkArrangement ?? undefined,
      submittedCommuteMinutes ?? undefined,
      submittedWorkplaceArea ?? undefined,
      submittedTravelMode ?? undefined,
      controller.signal,
    )
      .then((nextRecommendation) => {
        if (isCurrentRequest) {
          setRecommendation(nextRecommendation)
        }
      })
      .catch((requestError: unknown) => {
        if (isCurrentRequest) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Unable to load the recommendation.',
          )
        }
      })
      .finally(() => {
        if (isCurrentRequest) {
          setIsLoading(false)
        }
      })

    return () => {
      isCurrentRequest = false
      controller.abort()
    }
  }, [
    submittedCommuteMinutes,
    submittedTravelMode,
    submittedWorkArrangement,
    submittedWorkplaceArea,
  ])

  const commuteDraftIsValid = /^[1-9]\d*$/.test(draftCommuteMinutes)
  const trimmedWorkplaceArea = draftWorkplaceArea.trim()
  const workplaceAreaDraftIsValid =
    trimmedWorkplaceArea.length > 0 &&
    trimmedWorkplaceArea.length <= LIKELY_WORKPLACE_AREA_MAX_LENGTH

  return (
    <main className="app-shell py-5">
      <Container className="py-4">
        <Card className="next-step-card mx-auto border-0 shadow-sm">
          <Card.Body className="p-4 p-md-5">
            <header className="border-bottom pb-5">
              <p className="eyebrow mb-2">GoTime</p>
              <h1 className="page-title mb-0" id="page-title">
                What should I do next?
              </h1>
            </header>

            <section className="pt-5" aria-labelledby="goal-heading">
              <p className="section-label mb-2" id="goal-heading">
                Today's goal
              </p>
              <p className="goal-name mb-0">Relocate to Northern California</p>
            </section>

            <RelocationPlan />

            {isLoading && (
              <div className="loading-state mt-5 py-5 text-center" role="status">
                <Spinner animation="border" className="mb-3" />
                <p className="mb-0">Loading recommendation…</p>
              </div>
            )}

            {error && (
              <Alert className="mt-5 mb-0" variant="danger">
                <Alert.Heading as="h2">Recommendation unavailable</Alert.Heading>
                <p className="mb-0">{error}</p>
              </Alert>
            )}

            {recommendation && (
              <>
                {submittedWorkArrangement && (
                  <Alert className="state-update mt-5 mb-0" variant="success">
                    <p className="mb-0">
                      Work arrangement recorded: {workArrangementLabels[submittedWorkArrangement]}.
                    </p>
                    {submittedCommuteMinutes && (
                      <p className="mb-0">
                        Maximum workable one-way commute recorded: {submittedCommuteMinutes}{' '}
                        minutes.
                      </p>
                    )}
                    {submittedWorkplaceArea && (
                      <p className="mb-0">
                        Likely workplace area recorded: {submittedWorkplaceArea}.
                      </p>
                    )}
                    {submittedTravelMode && (
                      <p className="mb-0">
                        Intended commute mode recorded:{' '}
                        {commuteTravelModeLabels[submittedTravelMode]}.
                      </p>
                    )}
                  </Alert>
                )}

                <section
                  className="next-step mt-5 p-4 rounded-4"
                  aria-labelledby="next-step-heading"
                >
                  <p className="section-label mb-2" id="next-step-heading">
                    Primary recommendation
                  </p>
                  <h2 className="step-name mb-0">{recommendation.what}</h2>
                  {!submittedWorkArrangement && (
                    <Form
                      className="recommendation-action mt-4 pt-4"
                      onSubmit={(event) => {
                        event.preventDefault()
                        if (draftWorkArrangement) {
                          setSubmittedWorkArrangement(draftWorkArrangement)
                        }
                      }}
                    >
                      <Form.Label htmlFor="work-arrangement">
                        What kind of work arrangement would make the move workable for your spouse?
                      </Form.Label>
                      <Form.Select
                        className="mb-3"
                        id="work-arrangement"
                        value={draftWorkArrangement}
                        onChange={(event) => {
                          if (
                            event.target.value === '' ||
                            isWorkArrangement(event.target.value)
                          ) {
                            setDraftWorkArrangement(event.target.value)
                          }
                        }}
                      >
                        <option value="">Select a work arrangement</option>
                        <option value="remote">Remote</option>
                        <option value="hybrid">Hybrid</option>
                        <option value="on_site">On-site</option>
                        <option value="flexible">Flexible</option>
                      </Form.Select>
                      <Button
                        disabled={!draftWorkArrangement}
                        type="submit"
                        variant="outline-success"
                      >
                        Use this requirement
                      </Button>
                    </Form>
                  )}
                  {requiresCommuteLimit(submittedWorkArrangement) &&
                    submittedCommuteMinutes === null && (
                      <Form
                        className="recommendation-action mt-4 pt-4"
                        onSubmit={(event) => {
                          event.preventDefault()
                          if (commuteDraftIsValid) {
                            setSubmittedCommuteMinutes(Number(draftCommuteMinutes))
                          }
                        }}
                      >
                        <Form.Label htmlFor="commute-limit">
                          What is the longest one-way commute that would still make the
                          move workable?
                        </Form.Label>
                        <InputGroup className="mb-3">
                          <Form.Control
                            id="commute-limit"
                            inputMode="numeric"
                            min="1"
                            onChange={(event) => {
                              setDraftCommuteMinutes(event.target.value)
                            }}
                            step="1"
                            type="number"
                            value={draftCommuteMinutes}
                          />
                          <InputGroup.Text>minutes</InputGroup.Text>
                        </InputGroup>
                        <Button
                          disabled={!commuteDraftIsValid}
                          type="submit"
                          variant="outline-success"
                        >
                          Use this commute limit
                        </Button>
                      </Form>
                    )}
                  {requiresCommuteLimit(submittedWorkArrangement) &&
                    submittedCommuteMinutes !== null &&
                    submittedWorkplaceArea === null && (
                      <Form
                        className="recommendation-action mt-4 pt-4"
                        onSubmit={(event) => {
                          event.preventDefault()
                          if (workplaceAreaDraftIsValid) {
                            setSubmittedWorkplaceArea(trimmedWorkplaceArea)
                          }
                        }}
                      >
                        <Form.Label htmlFor="likely-workplace-area">
                          What area is your spouse most likely to work in?
                        </Form.Label>
                        <Form.Control
                          className="mb-3"
                          id="likely-workplace-area"
                          maxLength={LIKELY_WORKPLACE_AREA_MAX_LENGTH}
                          onChange={(event) => {
                            setDraftWorkplaceArea(event.target.value)
                          }}
                          placeholder="San Jose or the surrounding area"
                          type="text"
                          value={draftWorkplaceArea}
                        />
                        <Button
                          disabled={!workplaceAreaDraftIsValid}
                          type="submit"
                          variant="outline-success"
                        >
                          Use this workplace area
                        </Button>
                      </Form>
                    )}
                  {submittedWorkplaceArea !== null &&
                    submittedTravelMode === null && (
                      <Form
                        className="recommendation-action mt-4 pt-4"
                        onSubmit={(event) => {
                          event.preventDefault()
                          if (draftTravelMode) {
                            setSubmittedTravelMode(draftTravelMode)
                          }
                        }}
                      >
                        <Form.Label htmlFor="commute-travel-mode">
                          How would your spouse most likely commute?
                        </Form.Label>
                        <Form.Select
                          className="mb-3"
                          id="commute-travel-mode"
                          onChange={(event) => {
                            if (
                              event.target.value === '' ||
                              isCommuteTravelMode(event.target.value)
                            ) {
                              setDraftTravelMode(event.target.value)
                            }
                          }}
                          value={draftTravelMode}
                        >
                          <option value="">Select a travel mode</option>
                          <option value="drive">Drive</option>
                          <option value="public_transit">Public transit</option>
                          <option value="either">
                            Either driving or public transit
                          </option>
                        </Form.Select>
                        <Button
                          disabled={!draftTravelMode}
                          type="submit"
                          variant="outline-success"
                        >
                          Use this travel mode
                        </Button>
                      </Form>
                    )}
                </section>

                <MovingServiceQuestionExperiment />

                <section className="pt-5" aria-labelledby="why-heading">
                  <h2 className="detail-heading mb-3" id="why-heading">
                    Why this is recommended
                  </h2>
                  <ListGroup as="ul" className="detail-list" variant="flush">
                    {recommendation.why.map((reason) => (
                      <ListGroup.Item as="li" className="px-0 py-2" key={reason}>
                        {reason}
                      </ListGroup.Item>
                    ))}
                  </ListGroup>
                </section>

                <section className="why-now mt-4 p-4 rounded-4" aria-labelledby="why-now-heading">
                  <h2 className="detail-heading mb-2" id="why-now-heading">
                    Why it matters now
                  </h2>
                  <p className="mb-0">{recommendation.why_now}</p>
                </section>

                <Row className="g-4 pt-5">
                  <Col md={6}>
                    <section aria-labelledby="dependencies-heading">
                      <h2 className="detail-heading mb-3" id="dependencies-heading">
                        Relevant dependencies
                      </h2>
                      <ListGroup as="ul" className="detail-list" variant="flush">
                        {recommendation.relevant_dependencies.map((dependency) => (
                          <ListGroup.Item as="li" className="px-0 py-2" key={dependency}>
                            {dependency}
                          </ListGroup.Item>
                        ))}
                      </ListGroup>
                    </section>
                  </Col>
                  <Col md={6}>
                    <section aria-labelledby="blocked-heading">
                      <h2 className="detail-heading mb-3" id="blocked-heading">
                        Blocked downstream work
                      </h2>
                      <ListGroup as="ul" className="detail-list" variant="flush">
                        {recommendation.blocked_downstream_work.map((item) => (
                          <ListGroup.Item as="li" className="px-0 py-2" key={item}>
                            {item}
                          </ListGroup.Item>
                        ))}
                      </ListGroup>
                    </section>
                  </Col>
                </Row>

                <section className="assumptions pt-5" aria-labelledby="assumptions-heading">
                  <h2 className="detail-heading mb-3" id="assumptions-heading">
                    Related employment assumption
                  </h2>
                  {recommendation.related_assumptions.map((assumption) => (
                    <Card className="assumption-card border-0" key={assumption.id}>
                      <Card.Body className="p-4">
                        <Badge bg="warning" text="dark" className="mb-3">
                          {assumption.status}
                        </Badge>
                        <p className="assumption-description mb-3">{assumption.description}</p>
                        <p className="section-label mb-1">How it can be validated</p>
                        <p className="mb-0">{assumption.validation_method}</p>
                      </Card.Body>
                    </Card>
                  ))}
                </section>
              </>
            )}
          </Card.Body>
        </Card>
      </Container>
    </main>
  )
}

export default App
