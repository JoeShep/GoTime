import { createContext, type ReactNode, useContext, useMemo, useState } from 'react'

export interface FindTarget {
  taskId: string
  source?: 'find' | 'recommendation'
}

interface FindContextValue {
  isOpen: boolean
  openFind: () => void
  closeFind: () => void
  editorOpen: boolean
  setEditorOpen: (open: boolean) => void
  target: FindTarget | null
  selectTarget: (target: FindTarget) => void
  consumeTarget: () => void
}

const FindContext = createContext<FindContextValue>({
  isOpen: false,
  openFind: () => undefined,
  closeFind: () => undefined,
  editorOpen: false,
  setEditorOpen: () => undefined,
  target: null,
  selectTarget: () => undefined,
  consumeTarget: () => undefined,
})

export function FindProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  const [editorOpen, setEditorOpen] = useState(false)
  const [target, setTarget] = useState<FindTarget | null>(null)
  const value = useMemo<FindContextValue>(() => ({
    isOpen,
    openFind: () => {
      if (!editorOpen) setIsOpen(true)
    },
    closeFind: () => setIsOpen(false),
    editorOpen,
    setEditorOpen,
    target,
    selectTarget: (next) => {
      setTarget(next)
      setIsOpen(false)
    },
    consumeTarget: () => setTarget(null),
  }), [editorOpen, isOpen, target])

  return <FindContext.Provider value={value}>{children}</FindContext.Provider>
}

export function useFind() {
  return useContext(FindContext)
}
