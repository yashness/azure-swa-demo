import './style.css'

interface User {
  id: number
  name: string
  email: string
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function fetchUsers(): Promise<User[]> {
  try {
    const response = await fetch(`${API_URL}/users`)
    if (!response.ok) throw new Error('Failed to fetch users')
    return await response.json()
  } catch (error) {
    console.error('Error fetching users:', error)
    return []
  }
}

async function renderApp() {
  const users = await fetchUsers()
  
  const usersList = users.length > 0 
    ? users.map(u => `<li><strong>${u.name}</strong> - ${u.email}</li>`).join('')
    : '<li>No users found or API unavailable</li>'

  document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
    <div class="container">
      <h1>🚀 Azure SWA Demo</h1>
      <p class="subtitle">Vite + Bun + FastAPI + SQLite</p>
      
      <div class="card">
        <h2>👥 Users from API</h2>
        <ul class="users-list">
          ${usersList}
        </ul>
        <button id="refresh" type="button">Refresh Users</button>
      </div>
      
      <footer>
        <p>Frontend: Azure Static Web Apps | Backend: Azure App Service</p>
      </footer>
    </div>
  `

  document.querySelector<HTMLButtonElement>('#refresh')?.addEventListener('click', renderApp)
}

renderApp()
