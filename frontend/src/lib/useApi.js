import { useEffect, useState } from 'react'

/**
 * Run an async loader whenever its dependencies change.
 * Returns { data, error, loading, reload }; the previous data stays visible while
 * a new request is in flight, and stale responses are ignored.
 */
export function useApi(loader, deps) {
  const [nonce, setNonce] = useState(0)
  const key = JSON.stringify([deps, nonce])
  const [state, setState] = useState({ key: null, data: null, error: null })

  useEffect(() => {
    let cancelled = false
    loader().then(
      (data) => !cancelled && setState({ key, data, error: null }),
      (error) => !cancelled && setState({ key, data: null, error }),
    )
    return () => {
      cancelled = true
    }
    // The loader is re-created every render; `key` captures its real inputs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  const loading = state.key !== key
  return {
    data: state.data,
    error: loading ? null : state.error,
    loading,
    reload: () => setNonce((n) => n + 1),
  }
}
