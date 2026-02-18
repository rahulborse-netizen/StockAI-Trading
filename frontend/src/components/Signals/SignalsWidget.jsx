import React from 'react'
import { Card, CardContent, Typography, List, ListItem, Chip } from '@mui/material'
import { useSelector } from 'react-redux'

export const SignalsWidget = () => {
  const signals = useSelector(state => state.signals.signals)

  const signalList = Object.entries(signals).slice(0, 5)

  const getSignalColor = (signal) => {
    switch (signal?.toUpperCase()) {
      case 'BUY':
        return 'success'
      case 'SELL':
        return 'error'
      default:
        return 'default'
    }
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Recent Signals
        </Typography>
        {signalList.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No signals available
          </Typography>
        ) : (
          <List>
            {signalList.map(([ticker, signalData]) => (
              <ListItem key={ticker} sx={{ px: 0 }}>
                <Typography variant="body2" sx={{ flexGrow: 1 }}>
                  {ticker}
                </Typography>
                <Chip
                  label={signalData?.signal || 'HOLD'}
                  color={getSignalColor(signalData?.signal)}
                  size="small"
                />
              </ListItem>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  )
}
