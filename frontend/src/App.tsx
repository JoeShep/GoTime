import { lazy, Suspense, type CSSProperties, type MouseEvent, type ReactNode } from 'react'
import { Alert, Button, Card, Container, Nav, Spinner } from 'react-bootstrap'
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router'
import { NowPage } from './NowPage'
import { PlanPage } from './PlanPage'
import { FindProvider, useFind } from './FindContext'
import { SharedFindPanel } from './SharedFindPanel'
import { returnPlanToTopEvent, savePlanPositionEvent } from './planWorkspaceEvents'
import { useMediaQuery } from './useMediaQuery'
import { mobileBottomContentGutter, mobileBottomNavigationHeight } from './mobileNavigationLayout'

export const experimentsEnabled = import.meta.env.VITE_ENABLE_EXPERIMENTS === 'true'

const ExperimentsPage = experimentsEnabled
  ? lazy(() => import('./ExperimentsPage'))
  : null

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function handleActiveDestination(event: MouseEvent<HTMLAnchorElement>, path: '/now' | '/plan') {
  event.preventDefault()
  if (path === '/plan') window.dispatchEvent(new Event(returnPlanToTopEvent))
  window.scrollTo({
    top: 0,
    left: 0,
    behavior: prefersReducedMotion() ? 'auto' : 'smooth',
  })
}

function DesktopNavigation() {
  const { editorOpen, isOpen, openFind } = useFind()

  return (
    <div className="family-navigation-wrap d-flex justify-content-end align-items-center gap-2 px-2 px-sm-0 pt-0 pt-sm-3 mb-3 mb-sm-0">
      <Nav aria-label="Primary" as="nav" className="family-navigation">
        <Nav.Link as={NavLink} end to="/now">Now</Nav.Link>
        <Nav.Link as={NavLink} to="/plan">Plan</Nav.Link>
      </Nav>
      <Button aria-controls="shared-find-panel" aria-expanded={isOpen} className="shared-find-trigger" disabled={editorOpen} onClick={openFind} type="button" variant="outline-secondary">Find</Button>
    </div>
  )
}

function MobileBottomNavigation() {
  const { editorOpen, isOpen, openFind } = useFind()
  const location = useLocation()

  function handleRouteClick(event: MouseEvent<HTMLAnchorElement>, path: '/now' | '/plan') {
    if (location.pathname === path) {
      handleActiveDestination(event, path)
    } else if (location.pathname === '/plan') {
      window.dispatchEvent(new Event(savePlanPositionEvent))
    }
  }

  return (
    <nav
      aria-label="Mobile primary"
      className="mobile-bottom-navigation"
      inert={isOpen ? true : undefined}
    >
      <NavLink className="mobile-bottom-navigation-target" end onClick={(event) => handleRouteClick(event, '/now')} to="/now">Now</NavLink>
      <NavLink className="mobile-bottom-navigation-target" onClick={(event) => handleRouteClick(event, '/plan')} to="/plan">Plan</NavLink>
      <button
        aria-controls="shared-find-panel"
        aria-expanded={isOpen}
        aria-pressed={isOpen}
        className={`mobile-bottom-navigation-target ${isOpen ? 'is-open' : ''}`}
        disabled={editorOpen}
        onClick={openFind}
        type="button"
      >Find</button>
    </nav>
  )
}

function PageFrame({ children }: { children: ReactNode }) {
  const desktop = useMediaQuery('(min-width: 576px)')
  return (
    <main
      className="app-shell pt-2 py-sm-5"
      style={{
        '--mobile-bottom-navigation-height': mobileBottomNavigationHeight,
        '--mobile-bottom-content-gutter': mobileBottomContentGutter,
      } as CSSProperties}
    >
      <Container className="app-container pt-0 py-sm-4">
        <Card className="next-step-card mx-auto border-0 shadow-sm">
          <Card.Body className="pt-2 px-0 p-sm-4 p-md-5">
            {desktop && <DesktopNavigation />}
            {children}
            <SharedFindPanel />
          </Card.Body>
        </Card>
      </Container>
      {!desktop && <MobileBottomNavigation />}
    </main>
  )
}

function NotFoundPage() {
  return (
    <PageFrame>
      <Alert className="mx-2 mx-sm-0 mt-4 mb-0 mb-sm-3" variant="light">
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
