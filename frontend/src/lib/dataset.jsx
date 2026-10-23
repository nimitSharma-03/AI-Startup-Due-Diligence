import { createContext, useCallback, useContext, useMemo, useState } from 'react'

const STORAGE_KEY = 'diligence.dataset'
const REFERENCE = { id: 'reference', name: 'Y Combinator reference dataset (2005-2014)', kind: 'reference' }
const DatasetContext = createContext(null)

function readStored() {
  try {
    const stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY))
    return stored?.id ? stored : REFERENCE
  } catch {
    return REFERENCE
  }
}

export function DatasetProvider({ children }) {
  const [dataset, setDatasetState] = useState(readStored)

  const setDataset = useCallback((next) => {
    const value = next ? { id: next.id, name: next.name, kind: next.kind } : REFERENCE
    setDatasetState(value)
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value))
    } catch {
      // Storage can be unavailable (private mode); the in-memory state still works.
    }
  }, [])

  const resetToReference = useCallback(() => setDataset(null), [setDataset])
  const value = useMemo(() => ({ dataset, setDataset, resetToReference, isReference: dataset.id === 'reference' }), [dataset, setDataset, resetToReference])
  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useDataset() {
  const context = useContext(DatasetContext)
  if (!context) throw new Error('useDataset must be used inside DatasetProvider')
  return context
}
