export function canonicalizePlanItemTitle(title: string): string {
  return title.trim().replace(/\s+/gu, ' ').toLocaleLowerCase()
}

export function hasDuplicatePlanItemTitle(
  items: ReadonlyArray<{ id: string; title: string }>,
  title: string,
  excludedId: string | null = null,
): boolean {
  const canonicalTitle = canonicalizePlanItemTitle(title)
  return items.some((item) => (
    item.id !== excludedId
    && canonicalizePlanItemTitle(item.title) === canonicalTitle
  ))
}
