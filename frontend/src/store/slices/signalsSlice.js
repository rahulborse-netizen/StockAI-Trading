import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import axios from 'axios'

const API_BASE = '/api'

export const fetchSignals = createAsyncThunk(
  'signals/fetchSignals',
  async ({ tickers }) => {
    const response = await axios.post(`${API_BASE}/signals/batch`, { tickers })
    return response.data
  }
)

export const fetchSignal = createAsyncThunk(
  'signals/fetchSignal',
  async ({ ticker }) => {
    const response = await axios.get(`${API_BASE}/signals/${encodeURIComponent(ticker)}`)
    return response.data
  }
)

const initialState = {
  signals: {},
  loading: false,
  error: null,
  lastUpdated: null,
}

const signalsSlice = createSlice({
  name: 'signals',
  initialState,
  reducers: {
    updateSignal: (state, action) => {
      const { ticker, signal } = action.payload
      state.signals[ticker] = signal
      state.lastUpdated = new Date().toISOString()
    },
    clearSignals: (state) => {
      state.signals = {}
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchSignals.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchSignals.fulfilled, (state, action) => {
        state.loading = false
        state.signals = action.payload.signals || {}
        state.lastUpdated = new Date().toISOString()
      })
      .addCase(fetchSignals.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message
      })
      .addCase(fetchSignal.fulfilled, (state, action) => {
        const ticker = action.meta.arg.ticker
        state.signals[ticker] = action.payload
        state.lastUpdated = new Date().toISOString()
      })
  },
})

export const { updateSignal, clearSignals } = signalsSlice.actions
export default signalsSlice.reducer
