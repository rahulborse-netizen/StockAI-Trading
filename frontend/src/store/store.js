import { configureStore } from '@reduxjs/toolkit'
import portfolioReducer from './slices/portfolioSlice'
import signalsReducer from './slices/signalsSlice'
import ordersReducer from './slices/ordersSlice'
import websocketReducer from './slices/websocketSlice'
import uiReducer from './slices/uiSlice'

export const store = configureStore({
  reducer: {
    portfolio: portfolioReducer,
    signals: signalsReducer,
    orders: ordersReducer,
    websocket: websocketReducer,
    ui: uiReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['websocket/updatePrice'],
      },
    }),
})
