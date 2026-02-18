import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  theme: 'dark', // 'dark' or 'light'
  sidebarOpen: true,
  dashboardLayout: {
    widgets: [],
    positions: {},
  },
  notifications: [],
}

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleTheme: (state) => {
      state.theme = state.theme === 'dark' ? 'light' : 'dark'
    },
    setTheme: (state, action) => {
      state.theme = action.payload
    },
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen
    },
    setSidebarOpen: (state, action) => {
      state.sidebarOpen = action.payload
    },
    updateDashboardLayout: (state, action) => {
      state.dashboardLayout = { ...state.dashboardLayout, ...action.payload }
    },
    addNotification: (state, action) => {
      state.notifications.push({
        id: Date.now(),
        ...action.payload,
        timestamp: new Date().toISOString(),
      })
    },
    removeNotification: (state, action) => {
      state.notifications = state.notifications.filter(n => n.id !== action.payload)
    },
  },
})

export const {
  toggleTheme,
  setTheme,
  toggleSidebar,
  setSidebarOpen,
  updateDashboardLayout,
  addNotification,
  removeNotification,
} = uiSlice.actions
export default uiSlice.reducer
