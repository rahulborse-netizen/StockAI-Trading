import React from 'react'
import { Typography } from '@mui/material'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

// Placeholder data - in production, this would come from Redux store
const mockData = [
  { date: '2024-01-01', value: 100000 },
  { date: '2024-01-02', value: 102000 },
  { date: '2024-01-03', value: 101500 },
  { date: '2024-01-04', value: 103000 },
  { date: '2024-01-05', value: 104500 },
]

export const PriceChart = () => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={mockData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  )
}
