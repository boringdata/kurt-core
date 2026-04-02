import { useState, useEffect, useCallback, createContext, useContext } from 'react'

const THEME_STORAGE_KEY = 'kurt-web-theme'

// Get initial theme from localStorage or system preference
const getInitialTheme = () => {
  // Check localStorage first
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === 'dark' || stored === 'light') {
      return stored
    }
  } catch {
    // Ignore localStorage errors
  }

  // Fall back to system preference
  if (typeof window !== 'undefined' && window.matchMedia) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }

  return 'light'
}

// Apply theme to document
const applyTheme = (theme) => {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', theme)
  }
}

// Persist theme to localStorage
const persistTheme = (theme) => {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    // Ignore localStorage errors
  }
}

// Theme context for app-wide access
const ThemeContext = createContext(null)

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(getInitialTheme)

  // Apply theme on mount and when it changes
  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  // Enable smooth theme transitions after initial render
  useEffect(() => {
    // Small delay to ensure initial render is complete without transitions
    const timer = setTimeout(() => {
      document.documentElement.classList.add('theme-transition')
    }, 100)
    return () => clearTimeout(timer)
  }, [])

  // Listen for system preference changes
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const handleChange = (e) => {
      // Only auto-switch if user hasn't explicitly set a preference
      const stored = localStorage.getItem(THEME_STORAGE_KEY)
      if (!stored) {
        const newTheme = e.matches ? 'dark' : 'light'
        setTheme(newTheme)
      }
    }

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange)
      return () => mediaQuery.removeEventListener('change', handleChange)
    }

    // Legacy browsers
    mediaQuery.addListener(handleChange)
    return () => mediaQuery.removeListener(handleChange)
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark'
      persistTheme(next)
      return next
    })
  }, [])

  const setThemeExplicit = useCallback((newTheme) => {
    if (newTheme === 'dark' || newTheme === 'light') {
      setTheme(newTheme)
      persistTheme(newTheme)
    }
  }, [])

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme: setThemeExplicit }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

// Initialize theme immediately to prevent flash
// This runs before React hydration
if (typeof document !== 'undefined') {
  applyTheme(getInitialTheme())
}
