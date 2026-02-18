import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import axios from 'axios'

const API_BASE = '/api'

export const fetchOrders = createAsyncThunk(
  'orders/fetchOrders',
  async () => {
    const response = await axios.get(`${API_BASE}/upstox/orders`)
    return response.data
  }
)

export const placeOrder = createAsyncThunk(
  'orders/placeOrder',
  async (orderData) => {
    const response = await axios.post(`${API_BASE}/upstox/place_order`, orderData)
    return response.data
  }
)

export const cancelOrder = createAsyncThunk(
  'orders/cancelOrder',
  async (orderId) => {
    const response = await axios.post(`${API_BASE}/orders/${orderId}/cancel`)
    return response.data
  }
)

const initialState = {
  orders: [],
  conditionalOrders: [],
  loading: false,
  error: null,
}

const ordersSlice = createSlice({
  name: 'orders',
  initialState,
  reducers: {
    addOrder: (state, action) => {
      state.orders.push(action.payload)
    },
    updateOrder: (state, action) => {
      const { orderId, updates } = action.payload
      const index = state.orders.findIndex(o => o.order_id === orderId)
      if (index !== -1) {
        state.orders[index] = { ...state.orders[index], ...updates }
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchOrders.fulfilled, (state, action) => {
        state.orders = action.payload.orders || []
      })
      .addCase(placeOrder.fulfilled, (state, action) => {
        if (action.payload.order) {
          state.orders.push(action.payload.order)
        }
      })
      .addCase(cancelOrder.fulfilled, (state, action) => {
        const orderId = action.meta.arg
        state.orders = state.orders.filter(o => o.order_id !== orderId)
      })
  },
})

export default ordersSlice.reducer
