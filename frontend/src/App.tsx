import { useEffect, useState } from 'react'

type HealthResponse = {
  status: string
}

function App() {
  const [backendStatus, setBackendStatus] = useState('checking')

  useEffect(() => {
    async function checkHealth() {
      try {
        const response = await fetch('/api/health')

        if (!response.ok) {
          throw new Error('Health check failed')
        }

        const health: HealthResponse = await response.json()
        setBackendStatus(health.status)
      } catch {
        setBackendStatus('unavailable')
      }
    }

    void checkHealth()
  }, [])

  return (
    <main>
      <h1>Hello, GoTime!</h1>
      <p>Backend status: {backendStatus}</p>
    </main>
  )
}

export default App
