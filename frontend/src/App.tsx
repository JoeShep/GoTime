import { lazy, Suspense, type ReactNode } from 'react'
import { Alert, Button, Card, Container, Nav, Spinner } from 'react-bootstrap'
import { Navigate, NavLink, Route, Routes } from 'react-router'
import { NowPage } from './NowPage'
import { PlanPage } from './PlanPage'
import { FindProvider, useFind } from './FindContext'
import { SharedFindPanel } from './SharedFindPanel'

export const experimentsEnabled = import.meta.env.VITE_ENABLE_EXPERIMENTS === 'true'

const ExperimentsPage = experimentsEnabled
  ? lazy(() => import('./ExperimentsPage'))
  : null

function FamilyNavigation() {
  const { editorOpen, openFind } = useFind()
  return (
    <div className="family-navigation-wrap d-flex justify-content-end align-items-center gap-2 px-2 px-sm-0 pt-0 pt-sm-3 mb-3 mb-sm-0">
      <Nav aria-label="Primary" as="nav" className="family-navigation">
        <Nav.Link as={NavLink} end to="/now">Now</Nav.Link>
        <Nav.Link as={NavLink} to="/plan">Plan</Nav.Link>
      </Nav>
      <Button className="shared-find-trigger" disabled={editorOpen} onClick={openFind} type="button" variant="outline-secondary">Find</Button>
    </div>
  )
}

function PageFrame({ children }: { children: ReactNode }) {
  return (
    <main className="app-shell pt-2 pb-5 py-sm-5">
      <Container className="app-container pt-0 pb-4 py-sm-4">
        <Card className="next-step-card mx-auto border-0 shadow-sm">
          <Card.Body className="pt-2 pb-4 px-0 p-sm-4 p-md-5">
            <FamilyNavigation />
            {children}
            <SharedFindPanel />
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
    <FindProvider><Routes>
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
    </Routes></FindProvider>
  )
}

export default App
