import React from 'react'
import { Typography, Box, Card, CardContent, Switch, FormControlLabel } from '@mui/material'
import { useDispatch, useSelector } from 'react-redux'
import { toggleTheme } from '../../store/slices/uiSlice'

export const Settings = () => {
  const dispatch = useDispatch()
  const theme = useSelector(state => state.ui.theme)

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <FormControlLabel
            control={
              <Switch
                checked={theme === 'dark'}
                onChange={() => dispatch(toggleTheme())}
              />
            }
            label="Dark Mode"
          />
        </CardContent>
      </Card>
    </Box>
  )
}
