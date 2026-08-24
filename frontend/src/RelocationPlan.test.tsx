import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { generateTaskId, RelocationPlan } from './RelocationPlan'
import type { RelocationPlan as RelocationPlanData } from './api/relocationPlan'

const phases = [
  { id: 'decide', title: 'Decide where and how to move', position: 10 },
  { id: 'prepare', title: 'Prepare for the move', position: 20 },
  { id: 'move', title: 'Make the move', position: 30 },
  { id: 'settle', title: 'Settle in', position: 40 },
]

const plan: RelocationPlanData = {
  id: 'family-relocation-plan',
  title: 'Relocate the family to Northern California',
  phases,
  milestones: [],
  decisions: [],
  tasks: [
    {
      id: 'choose-mover',
      title: 'Choose a mover',
      description: 'Compare the final quotes.',
      phase_id: 'prepare',
      categories: ['logistics'],
      status: 'not_started',
      assignees: ['Joe', 'Sarah'],
      start_date: '2026-09-01',
      due_date: '2026-09-10',
      priority: 'high',
      dependency_task_ids: [],
      blocked: false,
    },
    {
      id: 'pay-deposit',
      title: 'Pay the mover deposit',
      description: null,
      phase_id: 'prepare',
      categories: ['financial'],
      status: 'not_started',
      assignees: ['Sarah'],
      start_date: null,
      due_date: null,
      priority: 'critical',
      dependency_task_ids: ['choose-mover'],
      blocked: true,
    },
  ],
}

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response
}

function mockPlanRequests(mutationPlan = plan) {
  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(plan))
    return Promise.resolve(response(mutationPlan))
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function beginTaskCreation() {
  fireEvent.click(await screen.findByRole('button', { name: 'Add' }))
  fireEvent.click(screen.getByRole('menuitem', { name: /Task/ }))
}

const expansionStorageKey = 'gotime:plan:family-relocation-plan:expansion'

function storeExpansionState(expandedPhaseIds: string[], expandedCompletedPhaseIds: string[] = []) {
  sessionStorage.setItem(expansionStorageKey, JSON.stringify({
    version: 1,
    expandedPhaseIds,
    expandedCompletedPhaseIds,
  }))
}

beforeEach(() => {
  storeExpansionState(phases.map((phase) => phase.id))
})

afterEach(() => {
  sessionStorage.clear()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('persistent relocation plan', () => {
  it('starts a new tab session with collapsed accessible phase headers and current counts', async () => {
    sessionStorage.clear()
    mockPlanRequests()
    render(<RelocationPlan />)

    const prepare = await screen.findByRole('button', {
      name: /Prepare for the move 2 remaining · 0 completed/,
    })
    expect(prepare.tagName).toBe('BUTTON')
    expect(prepare).toHaveAttribute('aria-expanded', 'false')
    expect(prepare).toHaveAttribute('aria-controls', 'phase-body-prepare')
    expect(screen.queryByRole('article', { name: 'Choose a mover' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Decide where and how to move 0 remaining · 0 completed/ })).toBeVisible()
  })

  it('expands multiple phases independently without changing the page position', async () => {
    sessionStorage.clear()
    const scrollTo = vi.fn()
    vi.stubGlobal('scrollTo', scrollTo)
    const planWithDecideTask = {
      ...plan,
      tasks: [{ ...plan.tasks[0], id: 'choose-region', title: 'Choose a region', phase_id: 'decide' }, ...plan.tasks],
    }
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response(planWithDecideTask))))
    render(<RelocationPlan />)

    const decide = await screen.findByRole('button', { name: /Decide where and how to move 1 remaining/ })
    const prepare = screen.getByRole('button', { name: /Prepare for the move 2 remaining/ })
    decide.focus()
    fireEvent.keyDown(decide, { key: 'Enter' })
    fireEvent.keyDown(prepare, { key: ' ' })

    expect(decide).toHaveAttribute('aria-expanded', 'true')
    expect(prepare).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('article', { name: 'Choose a region' })).toBeVisible()
    expect(screen.getByRole('article', { name: 'Choose a mover' })).toBeVisible()
    expect(scrollTo).not.toHaveBeenCalled()
  })

  it('expands and collapses all visible phases with mobile-safe compact controls', async () => {
    sessionStorage.clear()
    mockPlanRequests()
    const { container } = render(<RelocationPlan />)
    await screen.findByRole('button', { name: /Prepare for the move/ })

    const controls = screen.getByLabelText('Phase display controls')
    expect(controls).toHaveClass('d-flex', 'flex-wrap', 'gap-2')
    expect(screen.getByRole('button', { name: 'Expand all' })).toHaveClass('phase-display-control', 'btn-sm')
    fireEvent.click(screen.getByRole('button', { name: 'Expand all' }))
    expect(container.querySelectorAll('.phase-toggle[aria-expanded="true"]')).toHaveLength(4)

    fireEvent.click(screen.getByRole('button', { name: 'Collapse all' }))
    expect(container.querySelectorAll('.phase-toggle[aria-expanded="false"]')).toHaveLength(4)
    expect(screen.queryByRole('article', { name: 'Choose a mover' })).not.toBeInTheDocument()
  })

  it('restores valid session state and ignores malformed or stale phase identifiers', async () => {
    storeExpansionState(['prepare', 'removed-phase'], ['prepare', 'removed-phase'])
    const completedPlan = {
      ...plan,
      tasks: plan.tasks.map((task) => task.id === 'choose-mover' ? { ...task, status: 'completed' } : task),
    } as RelocationPlanData
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response(completedPlan))))
    const first = render(<RelocationPlan />)
    const prepare = await screen.findByRole('button', { name: /Prepare for the move/ })
    expect(prepare).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: 'Completed (1)' })).toHaveAttribute('aria-expanded', 'true')
    await waitFor(() => expect(JSON.parse(sessionStorage.getItem(expansionStorageKey) ?? '{}')).toEqual({
      version: 1,
      expandedPhaseIds: ['prepare'],
      expandedCompletedPhaseIds: ['prepare'],
    }))
    first.unmount()

    sessionStorage.setItem(expansionStorageKey, '{bad json')
    render(<RelocationPlan />)
    expect(await screen.findByRole('button', { name: /Prepare for the move/ })).toHaveAttribute('aria-expanded', 'false')
  })

  it('opens filtered phases, shows filtered counts, and restores the one pre-filter snapshot', async () => {
    sessionStorage.clear()
    mockPlanRequests()
    render(<RelocationPlan />)
    const prepare = await screen.findByRole('button', { name: /Prepare for the move 2 remaining/ })
    fireEvent.click(prepare)

    fireEvent.click(screen.getByRole('button', { name: 'Filter by categories' }))
    fireEvent.click(screen.getByLabelText('Logistics'))
    expect(screen.getByRole('button', { name: /Prepare for the move 1 remaining · 0 completed/ })).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(screen.getByRole('button', { name: /Prepare for the move/ }))
    expect(screen.getByRole('button', { name: /Prepare for the move/ })).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(screen.getByLabelText('Financial'))
    expect(screen.getByRole('button', { name: /Prepare for the move 2 remaining/ })).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(screen.getByLabelText('Logistics'))
    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }))
    expect(screen.getByRole('button', { name: /Prepare for the move 2 remaining/ })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: /Decide where and how to move/ })).toHaveAttribute('aria-expanded', 'false')
  })

  it('shows the current phase and category vocabulary', async () => {
    mockPlanRequests()
    render(<RelocationPlan />)

    expect(await screen.findByRole('heading', { name: 'Make the move' })).toBeVisible()
    expect(screen.queryByText('Complete the move')).not.toBeInTheDocument()

    await beginTaskCreation()
    const category = screen.getByLabelText('Categories (optional)')
    expect(category).toHaveTextContent('Select categories')
    fireEvent.click(category)
    expect(screen.queryByLabelText('Administrative')).not.toBeInTheDocument()
    expect(['Employment', 'Family', 'Financial', 'Healthcare', 'Housing', 'Logistics'].map(
      (label) => screen.getByLabelText(label).nextSibling?.textContent,
    )).toEqual(['Employment', 'Family', 'Financial', 'Healthcare', 'Housing', 'Logistics'])
  })

  it('keeps the category editor open, shows selections, and clears them', async () => {
    mockPlanRequests()
    render(<RelocationPlan />)
    await beginTaskCreation()
    const categories = screen.getByLabelText('Categories (optional)')

    fireEvent.click(categories)
    fireEvent.click(screen.getByLabelText('Housing'))
    fireEvent.click(screen.getByLabelText('Employment'))

    expect(screen.getByLabelText('Housing')).toBeVisible()
    expect(screen.getByLabelText('Employment')).toBeVisible()
    expect(categories).toHaveTextContent('Employment, Housing')
    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }))
    expect(categories).toHaveTextContent('Select categories')
    expect(screen.queryByRole('button', { name: 'Clear all' })).not.toBeInTheDocument()
  })

  it('dismisses the category editor on outside click and Escape', async () => {
    mockPlanRequests()
    render(<RelocationPlan />)
    await beginTaskCreation()
    const trigger = screen.getByLabelText('Categories (optional)')

    fireEvent.click(trigger)
    fireEvent.click(screen.getByLabelText('Housing'))
    const menu = screen.getByLabelText('Employment').closest('.dropdown-menu')!
    expect(menu).toHaveClass('show')
    fireEvent.click(document.body)
    await waitFor(() => expect(trigger).toHaveAttribute('aria-expanded', 'false'))
    expect(menu).not.toHaveClass('show')

    fireEvent.click(trigger)
    const employment = screen.getByLabelText('Employment')
    expect(menu).toHaveClass('show')
    fireEvent.keyDown(employment, { key: 'Escape' })
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(menu).not.toHaveClass('show')
    expect(trigger).toHaveFocus()
  })

  it('preserves every existing category while editing in configured order', async () => {
    const multiCategoryPlan: RelocationPlanData = {
      ...plan,
      tasks: [
        { ...plan.tasks[0], categories: ['logistics', 'employment', 'housing'] },
        plan.tasks[1],
      ],
    }
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan' && !init?.method) {
        return Promise.resolve(response(multiCategoryPlan))
      }
      return Promise.resolve(response(multiCategoryPlan))
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<RelocationPlan />)
    const heading = await screen.findByRole('heading', { name: 'Choose a mover' })
    fireEvent.click(within(heading.closest('article')!).getByRole('button', { name: 'Edit' }))

    const categories = screen.getByLabelText('Categories (optional)')
    expect(categories).toHaveTextContent('Employment, Housing, Logistics')
    fireEvent.click(categories)
    expect(screen.getByLabelText('Employment')).toBeChecked()
    expect(screen.getByLabelText('Housing')).toBeChecked()
    expect(screen.getByLabelText('Logistics')).toBeChecked()
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual(
      expect.objectContaining({ categories: ['employment', 'housing', 'logistics'] }),
    )
  })

  it('filters categories with OR behavior, hides empty phases, and clears filters', async () => {
    const filterPlan: RelocationPlanData = {
      ...plan,
      tasks: [
        { ...plan.tasks[0], categories: ['logistics', 'housing'] },
        { ...plan.tasks[1], categories: ['financial'], status: 'completed', blocked: false },
        { ...plan.tasks[0], id: 'uncategorized-task', title: 'Uncategorized task', phase_id: 'settle', categories: [] },
      ],
    }
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response(filterPlan))))
    render(<RelocationPlan />)
    const filter = await screen.findByRole('button', { name: 'Filter by categories' })

    fireEvent.click(filter)
    fireEvent.click(screen.getByLabelText('Housing'))
    expect(filter).toHaveTextContent('Categories (1)')
    expect(screen.getByRole('heading', { name: 'Choose a mover' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Settle in' })).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Find a task' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Uncategorized'))
    expect(filter).toHaveTextContent('Categories (2)')
    expect(screen.getByRole('heading', { name: 'Choose a mover' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Uncategorized task' })).toBeVisible()
    expect(screen.getByText('Uncategorized', { selector: '.text-muted' })).toBeVisible()
    expect(screen.getAllByRole('heading', { name: 'Choose a mover' })).toHaveLength(1)

    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }))
    expect(filter).toHaveTextContent(/^Categories$/)
    expect(screen.getByRole('heading', { name: 'Prepare for the move' })).toBeVisible()
  })

  it('filters completed counts and shows one empty state when nothing matches', async () => {
    const completedPlan: RelocationPlanData = {
      ...plan,
      tasks: [
        { ...plan.tasks[0], categories: ['housing'], status: 'completed' },
        { ...plan.tasks[1], categories: ['financial'], status: 'completed', blocked: false },
      ],
    }
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response(completedPlan))))
    render(<RelocationPlan />)
    const filter = await screen.findByRole('button', { name: 'Filter by categories' })
    fireEvent.click(filter)
    fireEvent.click(screen.getByLabelText('Housing'))

    expect(screen.getByRole('button', { name: 'Completed (1)' })).toBeVisible()
    fireEvent.click(screen.getByLabelText('Housing'))
    fireEvent.click(screen.getByLabelText('Healthcare'))
    expect(screen.getByText('No tasks match the selected categories.')).toBeVisible()
    expect(screen.queryByRole('button', { name: /Completed \(/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Prepare for the move' })).not.toBeInTheDocument()
  })

  it('keeps filter interactions open and dismisses the filter outside or with Escape', async () => {
    mockPlanRequests()
    render(<RelocationPlan />)
    const trigger = await screen.findByRole('button', { name: 'Filter by categories' })

    fireEvent.click(trigger)
    fireEvent.click(screen.getByLabelText('Logistics'))
    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }))
    const menu = screen.getByLabelText('Employment').closest('.dropdown-menu')!
    expect(menu).toHaveClass('show')
    fireEvent.click(document.body)
    await waitFor(() => expect(trigger).toHaveAttribute('aria-expanded', 'false'))
    expect(menu).not.toHaveClass('show')

    fireEvent.click(trigger)
    expect(menu).toHaveClass('show')
    fireEvent.keyDown(screen.getByLabelText('Employment'), { key: 'Escape' })
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(menu).not.toHaveClass('show')
    expect(trigger).toHaveFocus()
  })

  it('keeps mobile density hooks separate from unchanged pill styling', async () => {
    mockPlanRequests()
    render(<RelocationPlan />)
    const heading = await screen.findByRole('heading', { name: 'Choose a mover' })
    const task = heading.closest('article')!

    expect(task).toHaveClass('task-item', 'p-2', 'p-sm-3')
    expect(task.querySelector('.task-card-layout')).toHaveClass('gap-2', 'gap-sm-3')
    expect(task.querySelector('.task-heading-row')).toHaveClass('gap-1', 'gap-sm-2', 'mb-1')
    expect(task.querySelector('.task-metadata')).toHaveClass('gap-1', 'gap-sm-2', 'mb-2')
    expect(task.closest('.task-list')).toHaveClass('gap-1', 'gap-sm-3')
    expect(task.closest('.phase-card')?.querySelector('.card-body')).toHaveClass(
      'px-1',
      'py-2',
      'p-sm-3',
    )
    expect(within(task).getByText('High')).toHaveClass('badge', 'bg-light', 'text-dark')
    expect(within(task).getByText('Logistics')).toHaveClass('badge', 'bg-light', 'text-dark')
  })

  it('keeps category filtering aligned after removing the inline finder', async () => {
    mockPlanRequests()
    render(<RelocationPlan />)

    const filter = await screen.findByRole('button', { name: 'Filter by categories' })
    const group = filter.closest('.task-discovery')!
    expect(group).toHaveClass('px-2', 'px-sm-0', 'mb-3')
    expect(group.closest('.relocation-plan')?.querySelector('.plan-heading'))
      .toHaveClass('px-2', 'px-sm-0')
    expect(filter).toBeVisible()
    expect(screen.queryByRole('combobox', { name: 'Find a task' })).not.toBeInTheDocument()
    expect(group.closest('.relocation-plan')).toBeInTheDocument()
  })

  it('shows a loading state while retrieving the plan', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => undefined)))
    render(<RelocationPlan />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading relocation plan')
  })

  it('disables Add in add mode and restores it after Cancel', async () => {
    mockPlanRequests()
    render(<RelocationPlan />)
    const add = await screen.findByRole('button', { name: 'Add' })
    expect(screen.queryByRole('combobox', { name: 'Find a task' })).not.toBeInTheDocument()

    await beginTaskCreation()

    expect(add).toBeDisabled()
    expect(screen.queryByRole('combobox', { name: 'Find a task' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create task' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Save changes' })).not.toBeInTheDocument()
    const actionArea = screen.getByRole('button', { name: 'Create task' })
      .closest<HTMLElement>('.task-editor-actions')
    expect(actionArea).toHaveClass('sticky-top', 'flex-wrap')
    expect(within(actionArea!).getAllByRole('button')).toHaveLength(2)
    expect(within(actionArea!).getByRole('button', { name: 'Cancel' })).toHaveAttribute('type', 'button')

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(screen.queryByRole('heading', { name: 'Add task' })).not.toBeInTheDocument()
    await waitFor(() => expect(add).not.toBeDisabled())
    expect(screen.queryByRole('combobox', { name: 'Find a task' })).not.toBeInTheDocument()
  })

  it('disables Add in edit mode and uses Save changes only', async () => {
    mockPlanRequests()
    render(<RelocationPlan />)
    const taskHeading = await screen.findByRole('heading', { name: 'Choose a mover' })

    fireEvent.click(within(taskHeading.closest('article')!).getByRole('button', { name: 'Edit' }))

    expect(screen.getByRole('button', { name: 'Add' })).toBeDisabled()
    expect(screen.queryByRole('combobox', { name: 'Find a task' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Create task' })).not.toBeInTheDocument()
  })

  it('disables the editor actions and sends one request while creating', async () => {
    const pendingCreate = new Promise<Response>(() => undefined)
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(plan))
      return pendingCreate
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<RelocationPlan />)
    await beginTaskCreation()
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Pack books' } })

    fireEvent.click(screen.getByRole('button', { name: 'Create task' }))

    const pendingButton = await screen.findByRole('button', { name: 'Creating…' })
    expect(pendingButton).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    fireEvent.click(pendingButton)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('disables the editor actions and sends one request while saving changes', async () => {
    const pendingReplacement = new Promise<Response>(() => undefined)
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(plan))
      return pendingReplacement
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<RelocationPlan />)
    const taskHeading = await screen.findByRole('heading', { name: 'Choose a mover' })
    fireEvent.click(within(taskHeading.closest('article')!).getByRole('button', { name: 'Edit' }))

    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    const pendingButton = await screen.findByRole('button', { name: 'Saving…' })
    expect(pendingButton).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    fireEvent.click(pendingButton)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('renders ordered phases, tasks, blocked state, and dependency context', async () => {
    mockPlanRequests()
    render(<RelocationPlan />)

    expect(await screen.findByRole('heading', { name: 'Choose a mover' })).toBeVisible()
    const phaseHeadings = [...document.querySelectorAll('.phase-title')]
    expect(phaseHeadings.map((heading) => heading.textContent)).toEqual(phases.map((phase) => phase.title))
    expect(screen.getByText('Blocked')).toBeVisible()
    expect(screen.getByText(/Depends on:/).closest('p')).toHaveTextContent('Choose a mover')
    expect(screen.getAllByText('No tasks in this phase yet.')).toHaveLength(3)
    expect(screen.queryByRole('combobox', { name: 'Find a task' })).not.toBeInTheDocument()
  })

  it('adds a task with selected dependencies', async () => {
    const fetchMock = mockPlanRequests()
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })

    await beginTaskCreation()
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Pack the kitchen' } })
    fireEvent.change(screen.getByLabelText(/^Assignees/), { target: { value: 'Joe, Sarah' } })
    fireEvent.click(screen.getByLabelText('Choose a mover (Not started)'))
    fireEvent.click(screen.getByRole('button', { name: 'Create task' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(screen.queryByText('Task added.')).not.toBeInTheDocument()
    expect(screen.queryByText(/Category filter cleared/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add' })).toBeVisible()
    expect(screen.queryByRole('combobox', { name: 'Find a task' })).not.toBeInTheDocument()
    const [, init] = fetchMock.mock.calls[1]
    expect(fetchMock.mock.calls[1][0]).toBe('/api/relocation-plan/tasks')
    expect(JSON.parse(String(init?.body))).toEqual(expect.objectContaining({
      title: 'Pack the kitchen',
      categories: [],
      assignees: ['Joe', 'Sarah'],
      dependency_task_ids: ['choose-mover'],
      description: null,
      start_date: null,
      due_date: null,
    }))
  })

  it('uses no person-name placeholder and creates an unassigned task', async () => {
    const fetchMock = mockPlanRequests()
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })

    await beginTaskCreation()
    const assignees = screen.getByLabelText('Assignees (optional)')
    expect(assignees).not.toBeRequired()
    expect(assignees).toHaveAttribute('placeholder', 'Separate names with commas')
    expect(assignees).not.toHaveAttribute('placeholder', expect.stringMatching(/Joe|Sarah/i))
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Make a shared decision' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create task' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual(
      expect.objectContaining({ assignees: [] }),
    )
  })

  it('creates a valid bounded ID without changing a 200-character title', async () => {
    const longTitle = 'A'.repeat(200)
    const fetchMock = mockPlanRequests()
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })

    await beginTaskCreation()
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: longTitle } })
    fireEvent.change(screen.getByLabelText(/^Assignees/), { target: { value: 'Joe' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create task' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    const body = JSON.parse(String(fetchMock.mock.calls[1][1]?.body)) as {
      id: string
      title: string
    }
    expect(body.title).toBe(longTitle)
    expect(body.id).toMatch(/^[a-z0-9][a-z0-9-]*$/)
    expect(body.id.length).toBeLessThanOrEqual(64)
  })

  it('generates distinct valid IDs for repeated identical titles', () => {
    const first = generateTaskId('Pack the kitchen')
    const second = generateTaskId('Pack the kitchen')

    expect(first).not.toBe(second)
    for (const id of [first, second]) {
      expect(id).toMatch(/^[a-z0-9][a-z0-9-]*$/)
      expect(id.length).toBeLessThanOrEqual(64)
      expect(id).toMatch(/^pack-the-kitchen-/)
    }
  })

  it('edits with a complete replacement without losing untouched fields', async () => {
    const fetchMock = mockPlanRequests()
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })

    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0])
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Choose the mover' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(screen.getByRole('button', { name: 'Add' })).toBeVisible()
    expect(screen.queryByRole('combobox', { name: 'Find a task' })).not.toBeInTheDocument()
    const [path, init] = fetchMock.mock.calls[1]
    expect(path).toBe('/api/relocation-plan/tasks/choose-mover')
    expect(JSON.parse(String(init?.body))).toEqual({
      title: 'Choose the mover',
      description: 'Compare the final quotes.',
      phase_id: 'prepare',
      categories: ['logistics'],
      status: 'not_started',
      assignees: ['Joe', 'Sarah'],
      start_date: '2026-09-01',
      due_date: '2026-09-10',
      priority: 'high',
      dependency_task_ids: [],
    })
  })

  it('intentionally clears nullable fields with explicit null values', async () => {
    const fetchMock = mockPlanRequests()
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })

    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0])
    fireEvent.change(screen.getByLabelText('Description (optional)'), { target: { value: '' } })
    fireEvent.change(screen.getByLabelText('Start date (optional)'), { target: { value: '' } })
    fireEvent.change(screen.getByLabelText('Due date (optional)'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual(
      expect.objectContaining({
        description: null,
        start_date: null,
        due_date: null,
      }),
    )
  })

  it('changes task status through the narrow status endpoint', async () => {
    const completedPlan: RelocationPlanData = {
      ...plan,
      tasks: plan.tasks.map((task) => task.id === 'choose-mover'
        ? { ...task, status: 'completed' }
        : task),
    }
    const fetchMock = mockPlanRequests(completedPlan)
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })
    const prepare = screen.getByRole('button', { name: /Prepare for the move 2 remaining · 0 completed/ })

    fireEvent.change(screen.getByLabelText('Status for Choose a mover'), { target: { value: 'completed' } })

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(fetchMock.mock.calls[1][0]).toBe('/api/relocation-plan/tasks/choose-mover/status')
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({ status: 'completed' })
    expect(screen.getByRole('button', { name: /Prepare for the move 1 remaining · 1 completed/ })).toBe(prepare)
    expect(prepare).toHaveAttribute('aria-expanded', 'true')
  })

  it('visibly unblocks a dependent from the returned status-update plan', async () => {
    const completedPlan: RelocationPlanData = {
      ...plan,
      tasks: plan.tasks.map((task) =>
        task.id === 'choose-mover'
          ? { ...task, status: 'completed' }
          : { ...task, blocked: false },
      ),
    }
    mockPlanRequests(completedPlan)
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })
    expect(screen.getByText('Blocked')).toBeVisible()

    fireEvent.change(screen.getByLabelText('Status for Choose a mover'), {
      target: { value: 'completed' },
    })

    expect(await screen.findByText('Status updated for Choose a mover.')).toBeVisible()
    expect(screen.queryByText('Blocked')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Completed (1)' }))
    expect(screen.getByLabelText('Status for Choose a mover')).toHaveValue('completed')
  })

  it('does not offer the edited task as its own dependency', async () => {
    mockPlanRequests()
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })
    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0])

    expect(screen.queryByLabelText('Choose a mover (Not started)')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Pay the mover deposit (Not started)')).toBeVisible()
  })

  it('excludes completed tasks from new dependency choices', async () => {
    const completedPlan: RelocationPlanData = {
      ...plan,
      tasks: plan.tasks.map((task) =>
        task.id === 'choose-mover' ? { ...task, status: 'completed' } : task,
      ),
    }
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response(completedPlan))))
    render(<RelocationPlan />)
    await screen.findByRole('button', { name: 'Completed (1)' })

    await beginTaskCreation()

    expect(screen.queryByLabelText('Choose a mover (Completed)')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Pay the mover deposit (Not started)')).toBeVisible()
  })

  it('keeps an existing completed dependency visible, searchable, and removable', async () => {
    const completedPlan: RelocationPlanData = {
      ...plan,
      tasks: plan.tasks.map((task) =>
        task.id === 'choose-mover'
          ? { ...task, status: 'completed' }
          : { ...task, blocked: false },
      ),
    }
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan' && !init?.method) {
        return Promise.resolve(response(completedPlan))
      }
      return Promise.resolve(response(completedPlan))
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<RelocationPlan />)
    const dependentHeading = await screen.findByRole('heading', { name: 'Pay the mover deposit' })

    fireEvent.click(within(dependentHeading.closest('article')!).getByRole('button', { name: 'Edit' }))
    const completedDependency = screen.getByLabelText('Choose a mover (Completed)')
    expect(completedDependency).toBeChecked()

    fireEvent.change(screen.getByLabelText('Search dependencies'), { target: { value: 'missing' } })
    expect(screen.queryByLabelText('Choose a mover (Completed)')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Search dependencies'), { target: { value: 'choose' } })
    expect(screen.getByLabelText('Choose a mover (Completed)')).toBeChecked()

    fireEvent.click(screen.getByLabelText('Choose a mover (Completed)'))
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual(
      expect.objectContaining({ dependency_task_ids: [] }),
    )
  })

  it('separates completed tasks in a collapsed per-phase section and reopens them', async () => {
    const completedPlan: RelocationPlanData = {
      ...plan,
      tasks: plan.tasks.map((task) =>
        task.id === 'choose-mover'
          ? { ...task, status: 'completed' }
          : { ...task, blocked: false },
      ),
    }
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan' && !init?.method) {
        return Promise.resolve(response(completedPlan))
      }
      return Promise.resolve(response(plan))
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Pay the mover deposit' })

    const completedToggle = screen.getByRole('button', { name: 'Completed (1)' })
    expect(completedToggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('heading', { name: 'Pay the mover deposit' })).toBeVisible()

    fireEvent.click(completedToggle)
    expect(completedToggle).toHaveAttribute('aria-expanded', 'true')
    const completedTask = screen.getByRole('heading', { name: 'Choose a mover' }).closest('article')!
    expect(completedTask).toBeVisible()
    expect(completedTask.closest('.task-list')).toHaveClass('gap-1', 'gap-sm-3')
    expect(completedTask.closest('.completed-task-list-body')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Status for Choose a mover'), {
      target: { value: 'not_started' },
    })

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(screen.queryByRole('button', { name: 'Completed (1)' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Choose a mover' })).toBeVisible()
  })

  it('scrolls the editor into view and focuses its title when Edit is clicked', async () => {
    const scrollIntoView = vi.fn()
    Object.defineProperty(Element.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
    })
    mockPlanRequests()
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })

    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0])

    await waitFor(() => expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' }))
    expect(screen.getByLabelText('Title')).toHaveFocus()
    delete (Element.prototype as { scrollIntoView?: unknown }).scrollIntoView
  })

  it('groups and filters dependencies without losing hidden selections', async () => {
    const planWithAnotherPhaseTask: RelocationPlanData = {
      ...plan,
      tasks: [
        {
          ...plan.tasks[0],
          id: 'choose-region',
          title: 'Choose a region',
          phase_id: 'decide',
        },
        ...plan.tasks,
      ],
    }
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response(planWithAnotherPhaseTask))))
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Pay the mover deposit' })
    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[2])

    const decideGroup = screen.getByRole('group', { name: 'Decide where and how to move' })
    const prepareGroup = screen.getByRole('group', { name: 'Prepare for the move' })
    expect(within(decideGroup).getByLabelText('Choose a region (Not started)')).toBeVisible()
    expect(within(prepareGroup).getByLabelText('Choose a mover (Not started)')).toBeChecked()
    expect(screen.queryByLabelText('Pay the mover deposit (Not started)')).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Search dependencies'), { target: { value: 'region' } })
    fireEvent.click(screen.getByLabelText('Choose a region (Not started)'))
    expect(screen.queryByLabelText('Choose a mover (Not started)')).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Search dependencies'), { target: { value: 'mover' } })
    expect(screen.getByLabelText('Choose a mover (Not started)')).toBeChecked()
    fireEvent.change(screen.getByLabelText('Search dependencies'), { target: { value: '' } })
    expect(screen.getByLabelText('Choose a region (Not started)')).toBeChecked()
  })

  it('adds and removes dependencies while editing an existing task', async () => {
    const planWithAnotherTask: RelocationPlanData = {
      ...plan,
      tasks: [
        {
          ...plan.tasks[0],
          id: 'choose-region',
          title: 'Choose a region',
          phase_id: 'decide',
        },
        ...plan.tasks,
      ],
    }
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(planWithAnotherTask))
      return Promise.resolve(response(planWithAnotherTask))
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Pay the mover deposit' })
    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[2])

    fireEvent.click(screen.getByLabelText('Choose a mover (Not started)'))
    fireEvent.click(screen.getByLabelText('Choose a region (Not started)'))
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual(
      expect.objectContaining({ dependency_task_ids: ['choose-region'] }),
    )
  })

  it('shows backend validation details without discarding the editor', async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path === '/api/relocation-plan' && !init?.method) return Promise.resolve(response(plan))
      return Promise.resolve(response({ detail: 'Task dependencies cannot contain a cycle.' }, 422))
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<RelocationPlan />)
    await screen.findByRole('heading', { name: 'Choose a mover' })

    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0])
    fireEvent.click(screen.getByLabelText('Pay the mover deposit (Not started)'))
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(await screen.findByText('Task dependencies cannot contain a cycle.')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Edit task' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Add' })).toBeDisabled()
    expect(screen.queryByRole('combobox', { name: 'Find a task' })).not.toBeInTheDocument()
  })

  it('shows a network error when the plan cannot be loaded', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('The server is unavailable.')))
    render(<RelocationPlan />)

    expect(await screen.findByText('The server is unavailable.')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Add' })).not.toBeInTheDocument()
  })
})
