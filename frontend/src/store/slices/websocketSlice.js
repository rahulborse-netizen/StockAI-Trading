import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  connected: false,
  prices: {}, // ticker -> price data
  connectionStatus: 'disconnected',
  error: null,
}

const websocketSlice = createSlice({
  name: 'websocket',
  initialState,
  reducers: {
    setConnected: (state, action) => {
      state.connected = action.payload
      state.connectionStatus = action.payload ? 'connected' : 'disconnected'
    },
    updatePrice: (state, action) => {
      const { ticker, price, data } = action.payload
      state.prices[ticker] = {
        price,
        ...data,
        lastUpdated: new Date().toISOString(),
      }
    },
    setError: (state, action) => {
      state.error = action.payload
      state.connectionStatus = 'error'
    },
    clearPrices: (state) => {
      state.prices = {}
    },
  },
})

export const { setConnected, updatePrice, setError, clearPrices } = websocketSlice.actions
export default websocketSlice.reducer
