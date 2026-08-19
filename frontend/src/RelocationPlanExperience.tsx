import { useState } from 'react'
import { NextTaskRecommendation } from './NextTaskRecommendation'
import { RelocationPlan } from './RelocationPlan'

export function RelocationPlanExperience() {
  const [recommendationRevision, setRecommendationRevision] = useState(0)

  return (
    <>
      <NextTaskRecommendation refreshKey={recommendationRevision} />
      <RelocationPlan
        onPlanChanged={() => setRecommendationRevision((revision) => revision + 1)}
      />
    </>
  )
}
