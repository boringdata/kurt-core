import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'

// Suppress known xterm.js renderer race condition errors during layout transitions
// These occur when the terminal is destroyed while renderer is still initializing
const originalError = console.error
console.error = (...args) => {
  const msg = args[0]
  if (typeof msg === 'string' && msg.includes('_renderer.value is undefined')) {
    return // Suppress this specific xterm error
  }
  originalError.apply(console, args)
}

// Also catch unhandled errors for xterm renderer issues
window.addEventListener('error', (event) => {
  if (event.message?.includes('_renderer.value is undefined')) {
    event.preventDefault()
    return false
  }
})

createRoot(document.getElementById('root')).render(<App />)
