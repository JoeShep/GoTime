import { type KeyboardEvent, useEffect, useMemo, useRef, useState } from 'react'
import { Alert, Badge, Button, Form, ListGroup, Offcanvas, Spinner } from 'react-bootstrap'
import { useLocation, useNavigate } from 'react-router'
import { fetchRelocationPlan, type RelocationPlan, type TaskStatus } from './api/relocationPlan'
import { useFind } from './FindContext'

const statusLabels: Record<TaskStatus, string> = {
  not_started: 'Not started',
  in_progress: 'In progress',
  completed: 'Completed',
}

export function SharedFindPanel() {
  const { closeFind, isOpen, selectTarget } = useFind()
  const navigate = useNavigate()
  const location = useLocation()
  const [plan, setPlan] = useState<RelocationPlan | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const selectingRef = useRef(false)
  const pendingTaskIdRef = useRef<string | null>(null)

  useEffect(() => {
    if (!isOpen) return
    const controller = new AbortController()
    setPlan(null)
    selectingRef.current = false
    setError(null)
    setQuery('')
    setActiveIndex(-1)
    setLoading(true)
    fetchRelocationPlan(controller.signal)
      .then(setPlan)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Unable to load tasks.')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [isOpen])

  const normalizedQuery = query.trim().toLocaleLowerCase()
  const results = useMemo(() => normalizedQuery
    ? (plan?.tasks ?? []).filter((task) => task.title.toLocaleLowerCase().includes(normalizedQuery))
    : [], [normalizedQuery, plan])
  const phaseTitles = useMemo(() => new Map(plan?.phases.map((phase) => [phase.id, phase.title]) ?? []), [plan])

  function choose(taskId: string) {
    selectingRef.current = true
    pendingTaskIdRef.current = taskId
    closeFind()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && results.length > 0) {
      event.preventDefault()
      setActiveIndex((current) => {
        if (current < 0) return event.key === 'ArrowDown' ? 0 : results.length - 1
        return event.key === 'ArrowDown'
          ? (current + 1) % results.length
          : (current - 1 + results.length) % results.length
      })
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      const selected = results[activeIndex]
      if (selected) {
        event.preventDefault()
        choose(selected.id)
      }
    }
  }

  return (
    <Offcanvas
      aria-labelledby="shared-find-title"
      className="shared-find-panel"
      id="shared-find-panel"
      onEntered={() => inputRef.current?.focus()}
      onExited={() => {
        const taskId = pendingTaskIdRef.current
        pendingTaskIdRef.current = null
        if (!taskId) return
        selectTarget({ taskId })
        if (location.pathname !== '/plan') navigate('/plan')
      }}
      onHide={closeFind}
      placement="end"
      restoreFocus={!selectingRef.current}
      show={isOpen}
    >
      <Offcanvas.Header closeButton>
        <Offcanvas.Title id="shared-find-title">Find a task</Offcanvas.Title>
      </Offcanvas.Header>
      <Offcanvas.Body>
        <Form.Group controlId="shared-find-input">
          <Form.Label className="visually-hidden">Search task titles</Form.Label>
          <Form.Control
            aria-activedescendant={activeIndex >= 0 ? `shared-find-result-${results[activeIndex]?.id}` : undefined}
            aria-controls="shared-find-results"
            aria-expanded={normalizedQuery.length > 0}
            autoComplete="off"
            onChange={(event) => {
              setQuery(event.target.value)
              setActiveIndex(-1)
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search task titles"
            ref={inputRef}
            role="combobox"
            type="search"
            value={query}
          />
        </Form.Group>

        {loading && <div className="loading-state py-4" role="status"><Spinner size="sm" /> Loading tasks…</div>}
        {error && <Alert className="mt-3" variant="danger">{error}</Alert>}
        {!loading && !error && plan && !normalizedQuery && (
          <p className="text-muted mt-3 mb-0">Type a task title to search the complete plan.</p>
        )}
        {!loading && !error && normalizedQuery && results.length === 0 && (
          <p className="text-muted mt-3 mb-0" role="status">No matching tasks.</p>
        )}
        {!loading && !error && results.length > 0 && (
          <ListGroup className="mt-3" id="shared-find-results" role="listbox">
            {results.map((task, index) => (
              <ListGroup.Item
                action
                active={activeIndex === index}
                aria-selected={activeIndex === index}
                as="button"
                id={`shared-find-result-${task.id}`}
                key={task.id}
                onClick={() => choose(task.id)}
                role="option"
                type="button"
              >
                <strong className="d-block">{task.title}</strong>
                <span className="d-flex flex-wrap align-items-center gap-2 mt-1">
                  <small>{phaseTitles.get(task.phase_id) ?? task.phase_id}</small>
                  <Badge bg={task.status === 'completed' ? 'secondary' : 'light'} text={task.status === 'completed' ? undefined : 'dark'}>
                    {statusLabels[task.status]}
                  </Badge>
                </span>
              </ListGroup.Item>
            ))}
          </ListGroup>
        )}
        <Button className="mt-3" onClick={closeFind} type="button" variant="outline-secondary">Close</Button>
      </Offcanvas.Body>
    </Offcanvas>
  )
}
