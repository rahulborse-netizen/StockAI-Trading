import React, { useState } from 'react'
import { Typography, Box, TextField, Button, Grid, Card, CardContent } from '@mui/material'
import { AdvancedChartContainer } from '../../components/Charts/AdvancedChartContainer'
import { Search as SearchIcon } from '@mui/icons-material'

export const TradingSignals = () => {
  const [ticker, setTicker] = useState('RELIANCE.NS')
  const [selectedTicker, setSelectedTicker] = useState('RELIANCE.NS')

  const handleSearch = () => {
    if (ticker.trim()) {
      setSelectedTicker(ticker.trim())
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Trading Signals & Charts
      </Typography>

      <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
        <TextField
          label="Ticker Symbol"
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="e.g., RELIANCE.NS"
          size="small"
          sx={{ minWidth: 200 }}
        />
        <Button
          variant="contained"
          startIcon={<SearchIcon />}
          onClick={handleSearch}
        >
          Load Chart
        </Button>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <AdvancedChartContainer ticker={selectedTicker} />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
