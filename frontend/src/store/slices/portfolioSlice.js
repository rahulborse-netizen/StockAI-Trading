import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import axios from 'axios'

const API_BASE = '/api'

// Async thunks
export const fetchHoldings = createAsyncThunk(
  'portfolio/fetchHoldings',
  async () => {
    const response = await axios.get(`${API_BASE}/holdings`)
    return response.data
  }
)

export const fetchPortfolioSummary = createAsyncThunk(
  'portfolio/fetchPortfolioSummary',
  async () => {
    const response = await axios.get(`${API_BASE}/portfolio/summary`)
    return response.data
  }
)

export const optimizePortfolio = createAsyncThunk(
  'portfolio/optimizePortfolio',
  async ({ method, data }) => {
    const endpoint = method === 'mpt' 
      ? `${API_BASE}/portfolio/optimize/mpt`
      : method === 'risk-parity'
      ? `${API_BASE}/portfolio/optimize/risk-parity`
      : `${API_BASE}/portfolio/optimize/black-litterman`
    const response = await axios.post(endpoint, data)
    return response.data
  }
)

const initialState = {
  holdings: [],
  positions: [],
  portfolioSummary: null,
  optimizationResult: null,
  loading: false,
  error: null,
}

const portfolioSlice = createSlice({
  name: 'portfolio',
  initialState,
  reducers: {
    updateHoldingPrice: (state, action) => {
      const { ticker, price } = action.payload
      const holding = state.holdings.find(h => h.ticker === ticker)
      if (holding) {
        holding.current_price = price
        holding.current_value = holding.quantity * price
        holding.pnl = (price - holding.average_price) * holding.quantity
        holding.pnl_pct = ((price - holding.average_price) / holding.average_price) * 100
      }
    },
    clearOptimization: (state) => {
      state.optimizationResult = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchHoldings.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchHoldings.fulfilled, (state, action) => {
        state.loading = false
        state.holdings = action.payload || []
      })
      .addCase(fetchHoldings.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message
      })
      .addCase(fetchPortfolioSummary.fulfilled, (state, action) => {
        state.portfolioSummary = action.payload
      })
      .addCase(optimizePortfolio.fulfilled, (state, action) => {
        state.optimizationResult = action.payload
      })
  },
})

export const { updateHoldingPrice, clearOptimization } = portfolioSlice.actions
export default portfolioSlice.reducer
