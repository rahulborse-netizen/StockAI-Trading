import React, { useState, useEffect } from 'react'
import { Box, Grid, Paper, Typography } from '@mui/material'
import { TradingChart } from './TradingChart'
import { DrawingTools } from './DrawingTools'
import { PatternRecognition } from './PatternRecognition'
import { useDispatch, useSelector } from 'react-redux'
import axios from 'axios'

export const AdvancedChartContainer = ({ ticker }) => {
  const dispatch = useDispatch()
  const [chartData, setChartData] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeDrawingTool, setActiveDrawingTool] = useState(null)

  useEffect(() => {
    if (!ticker) return

    const fetchChartData = async () => {
      try {
        setLoading(true)
        // Fetch historical data for the ticker
        const response = await axios.get(`/api/historical/${encodeURIComponent(ticker)}`, {
          params: {
            days: 100,
          },
        })

        if (response.data && response.data.data) {
          const formatted = response.data.data.map((d, index) => ({
            time: d.date || d.time || index,
            open: parseFloat(d.open),
            high: parseFloat(d.high),
            low: parseFloat(d.low),
            close: parseFloat(d.close),
            volume: parseFloat(d.volume || 0),
          }))
          setChartData(formatted)
        }
      } catch (error) {
        console.error('Error fetching chart data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchChartData()
  }, [ticker])

  const handleDrawingToolSelect = (tool) => {
    setActiveDrawingTool(tool === activeDrawingTool ? null : tool)
  }

  if (loading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography>Loading chart data...</Typography>
      </Paper>
    )
  }

  return (
    <Box>
      <Grid container spacing={2}>
        {/* Main Chart */}
        <Grid item xs={12} md={9}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              {ticker} - Advanced Chart
            </Typography>
            <DrawingTools
              onToolSelect={handleDrawingToolSelect}
              activeTool={activeDrawingTool}
            />
            <TradingChart
              data={chartData}
              ticker={ticker}
              height={600}
              showIndicators={true}
              showDrawingTools={true}
            />
          </Paper>
        </Grid>

        {/* Pattern Recognition Panel */}
        <Grid item xs={12} md={3}>
          <PatternRecognition data={chartData} />
        </Grid>
      </Grid>
    </Box>
  )
}
