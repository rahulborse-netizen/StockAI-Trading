import React, { useEffect } from 'react'
import { Grid, Card, CardContent, Typography, Box } from '@mui/material'
import { useDispatch, useSelector } from 'react-redux'
import { fetchPortfolioSummary } from '../../store/slices/portfolioSlice'
import { PortfolioSummary } from '../../components/Portfolio/PortfolioSummary'
import { HoldingsTable } from '../../components/Portfolio/HoldingsTable'
import { SignalsWidget } from '../../components/Signals/SignalsWidget'
import { PriceChart } from '../../components/Charts/PriceChart'

export const Dashboard = () => {
  const dispatch = useDispatch()
  const portfolioSummary = useSelector(state => state.portfolio.portfolioSummary)

  useEffect(() => {
    dispatch(fetchPortfolioSummary())
  }, [dispatch])

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Portfolio Summary */}
        <Grid item xs={12}>
          <PortfolioSummary summary={portfolioSummary} />
        </Grid>

        {/* Holdings Table */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Holdings
              </Typography>
              <HoldingsTable />
            </CardContent>
          </Card>
        </Grid>

        {/* Signals Widget */}
        <Grid item xs={12} md={4}>
          <SignalsWidget />
        </Grid>

        {/* Price Chart */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Portfolio Performance
              </Typography>
              <PriceChart />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
