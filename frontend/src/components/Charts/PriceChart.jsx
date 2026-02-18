import React, { useEffect, useState } from 'react'
import { Typography, Paper } from '@mui/material'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'
import { useSelector } from 'react-redux'
import axios from 'axios'

export const PriceChart = ({ ticker }) => {
  const [data, setData] = useState([])
  const portfolioSummary = useSelector(state => state.portfolio.portfolioSummary)

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (ticker) {
          // Fetch historical data for specific ticker
          const response = await axios.get(`/api/historical/${encodeURIComponent(ticker)}`, {
            params: { days: 30 },
          })
          if (response.data?.data) {
            const formatted = response.data.data.map(d => ({
              date: d.date || d.time,
              value: parseFloat(d.close),
            }))
            setData(formatted)
          }
        } else {
          // Use portfolio value history if available
          const response = await axios.get('/api/portfolio/history', {
            params: { days: 30 },
          })
          if (response.data?.history) {
            const formatted = response.data.history.map(h => ({
              date: h.date,
              value: parseFloat(h.total_value || 0),
            }))
            setData(formatted)
          } else {
            // Fallback mock data
            setData([
              { date: '2024-01-01', value: portfolioSummary?.total_value || 100000 },
              { date: '2024-01-02', value: (portfolioSummary?.total_value || 100000) * 1.02 },
              { date: '2024-01-03', value: (portfolioSummary?.total_value || 100000) * 1.015 },
              { date: '2024-01-04', value: (portfolioSummary?.total_value || 100000) * 1.03 },
              { date: '2024-01-05', value: (portfolioSummary?.total_value || 100000) * 1.045 },
            ])
          }
        }
      } catch (error) {
        console.error('Error fetching chart data:', error)
        // Fallback mock data
        setData([
          { date: '2024-01-01', value: portfolioSummary?.total_value || 100000 },
          { date: '2024-01-02', value: (portfolioSummary?.total_value || 100000) * 1.02 },
          { date: '2024-01-03', value: (portfolioSummary?.total_value || 100000) * 1.015 },
          { date: '2024-01-04', value: (portfolioSummary?.total_value || 100000) * 1.03 },
          { date: '2024-01-05', value: (portfolioSummary?.total_value || 100000) * 1.045 },
        ])
      }
    }

    fetchData()
  }, [ticker, portfolioSummary])

  if (!data.length) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography>Loading chart data...</Typography>
      </Paper>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="date" stroke="#cbd5e1" />
        <YAxis stroke="#cbd5e1" />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            color: '#f1f5f9',
          }}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke="#3b82f6"
          fillOpacity={1}
          fill="url(#colorValue)"
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
