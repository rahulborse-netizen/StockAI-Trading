import React, { useEffect } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Chip,
} from '@mui/material'
import { useDispatch, useSelector } from 'react-redux'
import { fetchHoldings } from '../../store/slices/portfolioSlice'

export const HoldingsTable = () => {
  const dispatch = useDispatch()
  const holdings = useSelector(state => state.portfolio.holdings)
  const loading = useSelector(state => state.portfolio.loading)

  useEffect(() => {
    dispatch(fetchHoldings())
  }, [dispatch])

  if (loading) {
    return <Typography>Loading holdings...</Typography>
  }

  if (!holdings || holdings.length === 0) {
    return <Typography color="text.secondary">No holdings found</Typography>
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Symbol</TableCell>
            <TableCell align="right">Quantity</TableCell>
            <TableCell align="right">Avg Price</TableCell>
            <TableCell align="right">Current Price</TableCell>
            <TableCell align="right">P&L</TableCell>
            <TableCell align="right">P&L %</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {holdings.map((holding) => {
            const pnl = holding.pnl || 0
            const pnlPct = holding.pnl_pct || 0
            const isPositive = pnl >= 0

            return (
              <TableRow key={holding.ticker || holding.symbol}>
                <TableCell>{holding.ticker || holding.symbol}</TableCell>
                <TableCell align="right">{holding.quantity}</TableCell>
                <TableCell align="right">
                  ₹{holding.average_price?.toFixed(2) || '0.00'}
                </TableCell>
                <TableCell align="right">
                  ₹{holding.current_price?.toFixed(2) || '0.00'}
                </TableCell>
                <TableCell align="right">
                  <Chip
                    label={`₹${pnl.toFixed(2)}`}
                    color={isPositive ? 'success' : 'error'}
                    size="small"
                  />
                </TableCell>
                <TableCell align="right">
                  <Typography color={isPositive ? 'success.main' : 'error.main'}>
                    {pnlPct.toFixed(2)}%
                  </Typography>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </TableContainer>
  )
}
