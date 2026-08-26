export function ExpansionChevron({ expanded }: { expanded: boolean }) {
  return (
    <svg
      aria-hidden="true"
      className={`expansion-chevron ${expanded ? 'is-expanded' : ''}`}
      focusable="false"
      viewBox="0 0 16 16"
    >
      <path d="M5.75 3.5 10.25 8l-4.5 4.5" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.75" />
    </svg>
  )
}
