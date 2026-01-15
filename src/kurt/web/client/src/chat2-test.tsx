import React from 'react'
import { createRoot } from 'react-dom/client'
import { Chat2 } from './components/chat-2'

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Chat2 />
  </React.StrictMode>
)
