import { Card, Container, ListGroup } from 'react-bootstrap'

const upcomingSteps = ['Schedule movers', 'Sort garage']

function App() {
  return (
    <main className="app-shell d-flex align-items-center py-5">
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
              <p className="section-label mb-2" id="goal-heading">Today's goal</p>
              <p className="goal-name mb-0">Move to California</p>
            </section>

            <section className="next-step mt-5 p-4 rounded-4" aria-labelledby="next-step-heading">
              <p className="section-label mb-2" id="next-step-heading">Next step</p>
              <p className="step-name d-flex align-items-center gap-3 mb-0">
                <span className="next-step-checkbox flex-shrink-0" aria-hidden="true" />
                Contact Realtor
              </p>
            </section>

            <section className="pt-5" aria-labelledby="upcoming-heading">
              <p className="section-label mb-2" id="upcoming-heading">Upcoming</p>
              <ListGroup as="ul" className="upcoming-list" variant="flush">
                {upcomingSteps.map((step) => (
                  <ListGroup.Item as="li" className="border-0 px-0 py-2" key={step}>
                    {step}
                  </ListGroup.Item>
                ))}
              </ListGroup>
            </section>
          </Card.Body>
        </Card>
      </Container>
    </main>
  )
}

export default App
