import React from 'react'
import { Card, CardContent, Grid, Typography, Box } from '@mui/material'
import { TrendingUp, TrendingDown } from '@mui/icons-material'

export const PortfolioSummary = ({ summary }) => {
  if (!summary) {
    return <Card><CardContent>Loading...</CardContent></Card>
  }

  const { total_value = 0, total_pnl = 0, total_pnl_pct = 0, day_pnl = 0 } = summary
  const isPositive = total_pnl >= 0

  return (
    <Card>
      <CardContent>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Total Value
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 600 }}>
                ₹{total_value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Total P&L
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {isPositive ? <TrendingUp color="success" /> : <TrendingDown color="error" />}
                <Typography
                  variant="h5"
                  sx={{ fontWeight: 600, color: isPositive ? 'success.main' : 'error.main' }}
                >
                  ₹{total_pnl.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                </Typography>
              </Box>
              <Typography variant="body2" color={isPositive ? 'success.main' : 'error.main'}>
                {total_pnl_pct.toFixed(2)}%
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Day P&L
              </Typography>
              <Typography
                variant="h5"
                sx={{
                  fontWeight: 600,
                  color: day_pnl >= 0 ? 'success.main' : 'error.main',
                }}
              >
                ₹{day_pnl.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Positions
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 600 }}>
                {summary.num_positions || 0}
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  )
}
