import { lazy, Suspense, type ReactNode } from 'react'
import { Alert, Card, Container, Nav, Spinner } from 'react-bootstrap'
import { Navigate, NavLink, Route, Routes } from 'react-router'
import { NowPage } from './NowPage'
import { PlanPage } from './PlanPage'

export const experimentsEnabled = import.meta.env.VITE_ENABLE_EXPERIMENTS === 'true'

const ExperimentsPage = experimentsEnabled
  ? lazy(() => import('./ExperimentsPage'))
  : null

function FamilyNavigation() {
  return (
    <div className="family-navigation-wrap d-flex justify-content-end px-2 px-sm-0 pt-3">
      <Nav aria-label="Primary" as="nav" className="family-navigation">
        <Nav.Link as={NavLink} end to="/now">Now</Nav.Link>
        <Nav.Link as={NavLink} to="/plan">Plan</Nav.Link>
      </Nav>
    </div>
  )
}

function PageFrame({ children }: { children: ReactNode }) {
  return (
    <main className="app-shell py-5">
      <Container className="app-container py-4">
        <Card className="next-step-card mx-auto border-0 shadow-sm">
          <Card.Body className="py-4 px-0 p-sm-4 p-md-5">
            <FamilyNavigation />
            {children}
          </Card.Body>
        </Card>
      </Container>
    </main>
  )
}

function NotFoundPage() {
  return (
    <PageFrame>
      <Alert className="mx-2 mx-sm-0 mt-4" variant="light">
        <Alert.Heading as="h1">Page not found</Alert.Heading>
        <p className="mb-0">This GoTime page is not available.</p>
      </Alert>
    </PageFrame>
  )
}

function App() {
  return (
    <Routes>
      <Route element={<Navigate replace to="/now" />} path="/" />
      <Route element={<PageFrame><NowPage /></PageFrame>} path="/now" />
      <Route element={<PageFrame><PlanPage /></PageFrame>} path="/plan" />
      {ExperimentsPage && (
        <Route
          element={(
            <Suspense fallback={<div role="status"><Spinner size="sm" /> Loading experiments…</div>}>
              <ExperimentsPage />
            </Suspense>
          )}
          path="/experiments"
        />
      )}
      <Route element={<NotFoundPage />} path="*" />
    </Routes>
  )
}

export default App
