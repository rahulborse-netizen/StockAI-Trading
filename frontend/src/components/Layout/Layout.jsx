import React from 'react'
import { Box, useTheme } from '@mui/material'
import { AppBar } from '../AppBar/AppBar'
import { Sidebar } from '../Sidebar/Sidebar'
import { NotificationContainer } from '../Notifications/NotificationContainer'

export const Layout = ({ children }) => {
  const theme = useTheme()

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar />
      <Sidebar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          mt: 8, // Account for AppBar height
          ml: { xs: 0, md: '280px' }, // Account for Sidebar width
          transition: theme.transitions.create('margin', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
        }}
      >
        {children}
      </Box>
      <NotificationContainer />
    </Box>
  )
}
