import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, useLocation, useNavigate } from 'react-router'
import App from './App'
import { RelocationPlan } from './RelocationPlan'
import type { RelocationPlan as RelocationPlanData } from './api/relocationPlan'

const plan: RelocationPlanData = {
  id: 'scroll-plan',
  title: 'Move our family',
  phases: [{ id: 'prepare', title: 'Prepare', position: 10 }],
  tasks: [{
    id: 'pack', title: 'Pack boxes', description: null, phase_id: 'prepare', categories: [],
    status: 'not_started', assignees: [], start_date: null, due_date: null, priority: 'medium',
    dependency_task_ids: [], blocked: false,
  }],
  milestones: [],
  decisions: [],
}

function response(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body } as Response
}

function mockRequests() {
  vi.stubGlobal('fetch', vi.fn((path: string) => Promise.resolve(response(
    path === '/api/relocation-plan'
      ? plan
      : { task_id: 'pack', task_title: 'Pack boxes', phase_id: 'prepare', phase_title: 'Prepare', why: ['Actionable'] },
  ))))
}

function setLayout(scrollHeight: number, innerHeight: number) {
  Object.defineProperty(document.documentElement, 'scrollHeight', { configurable: true, value: scrollHeight })
  Object.defineProperty(window, 'innerHeight', { configurable: true, value: innerHeight })
}

function mockViewportScroll(initialY = 0) {
  let y = initialY
  Object.defineProperty(window, 'scrollY', { configurable: true, get: () => y })
  const scrollTo = vi.fn((options: ScrollToOptions) => { y = Number(options.top ?? 0) })
  vi.stubGlobal('scrollTo', scrollTo)
  return { scrollTo, setY: (next: number) => { y = next }, getY: () => y }
}

function HistoryControls() {
  const location = useLocation()
  const navigate = useNavigate()
  return <><output data-testid="route">{location.pathname}</output><button onClick={() => navigate(-1)}>History back</button><button onClick={() => navigate(1)}>History forward</button></>
}

afterEach(() => {
  sessionStorage.clear()
  vi.unstubAllGlobals()
})

describe('Plan scroll restoration', () => {
  it('restores valid session state after expansion state and clamps out-of-range positions', async () => {
    mockRequests()
    setLayout(1400, 400)
    sessionStorage.setItem('gotime:plan:scroll-plan:expansion', JSON.stringify({
      version: 1, expandedPhaseIds: ['prepare'], expandedCompletedPhaseIds: [],
    }))
    sessionStorage.setItem('gotime:plan:scroll-plan:scroll', JSON.stringify({ version: 1, y: 5000 }))
    const scrollTo = vi.fn()
    vi.stubGlobal('scrollTo', scrollTo)

    render(<RelocationPlan />)

    expect(await screen.findByRole('article', { name: 'Pack boxes' })).toBeVisible()
    expect(scrollTo).toHaveBeenCalledWith({ top: 1000, left: 0, behavior: 'auto' })
  })

  it.each([
    ['malformed', '{'],
    ['stale', JSON.stringify({ version: 0, y: 200 })],
    ['negative', JSON.stringify({ version: 1, y: -20 })],
  ])('ignores %s scroll state', async (_name, stored) => {
    mockRequests()
    setLayout(1400, 400)
    sessionStorage.setItem('gotime:plan:scroll-plan:scroll', stored)
    const scrollTo = vi.fn()
    vi.stubGlobal('scrollTo', scrollTo)

    render(<RelocationPlan />)
    await screen.findByRole('button', { name: /Prepare/ })
    expect(scrollTo).not.toHaveBeenCalled()
  })

  it('bounds session writes to one animation frame and flushes on unmount', async () => {
    mockRequests()
    const frames: FrameRequestCallback[] = []
    const requestAnimationFrame = vi.fn((callback: FrameRequestCallback) => {
      frames.push(callback)
      return frames.length
    })
    vi.stubGlobal('requestAnimationFrame', requestAnimationFrame)
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 240 })
    const { unmount } = render(<RelocationPlan />)
    await screen.findByRole('button', { name: /Prepare/ })

    fireEvent.scroll(window)
    fireEvent.scroll(window)
    fireEvent.scroll(window)
    expect(requestAnimationFrame).toHaveBeenCalledTimes(1)
    act(() => frames[0](0))
    expect(JSON.parse(sessionStorage.getItem('gotime:plan:scroll-plan:scroll')!)).toEqual({ version: 1, y: 240 })
    unmount()
    expect(JSON.parse(sessionStorage.getItem('gotime:plan:scroll-plan:scroll')!)).toEqual({ version: 1, y: 240 })
  })

  it('preserves Plan position across Now navigation while Now opens at the top', async () => {
    mockRequests()
    setLayout(1400, 400)
    const viewport = mockViewportScroll()
    render(<MemoryRouter initialEntries={['/plan']}><App /><HistoryControls /></MemoryRouter>)
    await screen.findByRole('button', { name: /Prepare/ })
    viewport.setY(360)
    fireEvent.scroll(window)
    await waitFor(() => expect(sessionStorage.getItem('gotime:plan:scroll-plan:scroll')).toContain('360'))

    fireEvent.click(screen.getByRole('link', { name: 'Now' }))
    expect(await screen.findByText('What should I do next?')).toBeVisible()
    expect(viewport.scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: 'auto' })
    expect(viewport.getY()).toBe(0)
    expect(sessionStorage.getItem('gotime:plan:scroll-plan:scroll')).toContain('360')
    fireEvent.click(screen.getByRole('link', { name: 'Plan' }))
    await waitFor(() => expect(viewport.scrollTo).toHaveBeenCalledWith({ top: 360, left: 0, behavior: 'auto' }))
    expect(viewport.getY()).toBe(360)
  })

  it('restores through browser-style Back and Forward without replaying Find state', async () => {
    mockRequests()
    setLayout(1400, 400)
    const viewport = mockViewportScroll()
    render(<MemoryRouter initialEntries={['/plan']}><App /><HistoryControls /></MemoryRouter>)
    await screen.findByRole('button', { name: /Prepare/ })
    viewport.setY(410)
    fireEvent.scroll(window)
    await waitFor(() => expect(sessionStorage.getItem('gotime:plan:scroll-plan:scroll')).toContain('410'))

    fireEvent.click(screen.getByRole('link', { name: 'Now' }))
    await screen.findByText('What should I do next?')
    fireEvent.click(screen.getByRole('button', { name: 'History back' }))
    await waitFor(() => expect(screen.getByTestId('route')).toHaveTextContent('/plan'))
    await waitFor(() => expect(viewport.getY()).toBe(410))
    expect(document.querySelector('.task-item.is-found')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'History forward' }))
    await waitFor(() => expect(screen.getByTestId('route')).toHaveTextContent('/now'))
    expect(viewport.getY()).toBe(0)
    fireEvent.click(screen.getByRole('button', { name: 'History back' }))
    await waitFor(() => expect(viewport.getY()).toBe(410))
  })

  it('lets a Find target override a saved position and saves the destination instead', async () => {
    mockRequests()
    setLayout(1400, 400)
    sessionStorage.setItem('gotime:plan:scroll-plan:scroll', JSON.stringify({ version: 1, y: 700 }))
    const viewport = mockViewportScroll()
    Object.defineProperty(Element.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(() => viewport.setY(320)),
    })
    render(<MemoryRouter initialEntries={['/now']}><App /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: 'Find' }))
    const input = await screen.findByRole('combobox', { name: 'Search task titles' })
    fireEvent.change(input, { target: { value: 'pack' } })
    fireEvent.click(screen.getByRole('option', { name: /Pack boxes/ }))

    await screen.findByRole('article', { name: 'Pack boxes' })
    expect(viewport.scrollTo).not.toHaveBeenCalledWith({ top: 700, left: 0, behavior: 'auto' })
    await waitFor(() => expect(sessionStorage.getItem('gotime:plan:scroll-plan:scroll')).toContain('320'))
    fireEvent.click(screen.getByRole('link', { name: 'Now' }))
    await screen.findByText('What should I do next?')
    fireEvent.click(screen.getByRole('link', { name: 'Plan' }))
    await waitFor(() => expect(viewport.scrollTo).toHaveBeenCalledWith({ top: 320, left: 0, behavior: 'auto' }))
    expect(screen.getByRole('article', { name: 'Pack boxes' })).not.toHaveClass('is-found')
    delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView
  })
})
