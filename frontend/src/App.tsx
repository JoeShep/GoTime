import { useEffect, useState } from 'react'
import { Alert, Badge, Button, Card, Col, Container, ListGroup, Row, Spinner } from 'react-bootstrap'
import {
  fetchPrimaryRecommendation,
  type EmploymentRequirementsState,
  type Recommendation,
} from './api/recommendations'

function App() {
  const [employmentRequirements, setEmploymentRequirements] =
    useState<EmploymentRequirementsState>('unclear')
  const [hasConfirmedEmploymentRequirements, setHasConfirmedEmploymentRequirements] =
    useState(false)
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    let isCurrentRequest = true

    setRecommendation(null)
    setError(null)
    setIsLoading(true)

    fetchPrimaryRecommendation(employmentRequirements, controller.signal)
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
  }, [employmentRequirements])

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
                {hasConfirmedEmploymentRequirements && (
                  <Alert className="state-update mt-5 mb-0" variant="success">
                    Employment requirements marked as clarified.
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
                  {!hasConfirmedEmploymentRequirements && (
                    <div className="recommendation-action mt-4 pt-4">
                      <p className="mb-3">Have you clarified what employment would need to provide?</p>
                      <Button
                        variant="outline-success"
                        onClick={() => {
                          setHasConfirmedEmploymentRequirements(true)
                          setEmploymentRequirements('clarified')
                        }}
                      >
                        Yes, we’ve clarified the requirements
                      </Button>
                    </div>
                  )}
                </section>

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
