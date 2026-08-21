import { createContext, type ReactNode, useContext, useMemo, useState } from 'react'

export interface FindTarget {
  taskId: string
}

interface FindContextValue {
  isOpen: boolean
  openFind: () => void
  closeFind: () => void
  target: FindTarget | null
  selectTarget: (target: FindTarget) => void
  consumeTarget: () => void
}

const FindContext = createContext<FindContextValue>({
  isOpen: false,
  openFind: () => undefined,
  closeFind: () => undefined,
  target: null,
  selectTarget: () => undefined,
  consumeTarget: () => undefined,
})

export function FindProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  const [target, setTarget] = useState<FindTarget | null>(null)
  const value = useMemo<FindContextValue>(() => ({
    isOpen,
    openFind: () => setIsOpen(true),
    closeFind: () => setIsOpen(false),
    target,
    selectTarget: (next) => {
      setTarget(next)
      setIsOpen(false)
    },
    consumeTarget: () => setTarget(null),
  }), [isOpen, target])

  return <FindContext.Provider value={value}>{children}</FindContext.Provider>
}

export function useFind() {
  return useContext(FindContext)
}
