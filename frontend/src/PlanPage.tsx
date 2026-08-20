import { RelocationPlan } from './RelocationPlan'

export function PlanPage() {
  return (
    <>
      <header className="plan-page-heading px-2 px-sm-0 pt-0 pt-sm-4 mb-3">
        <p className="section-label mb-1">Plan</p>
        <h1 className="detail-heading mb-0">Family plan</h1>
      </header>
      <RelocationPlan />
    </>
  )
}
