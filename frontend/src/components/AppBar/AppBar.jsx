import React from 'react'
import {
  AppBar as MuiAppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Chip,
  Tooltip,
} from '@mui/material'
import {
  Menu as MenuIcon,
  Notifications as NotificationsIcon,
  Settings as SettingsIcon,
  Brightness4 as Brightness4Icon,
  Brightness7 as Brightness7Icon,
} from '@mui/icons-material'
import { useDispatch, useSelector } from 'react-redux'
import { toggleSidebar, toggleTheme } from '../../store/slices/uiSlice'
import { useNavigate } from 'react-router-dom'

export const AppBar = () => {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const theme = useSelector(state => state.ui.theme)
  const websocketConnected = useSelector(state => state.websocket.connected)

  return (
    <MuiAppBar
      position="fixed"
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
        bgcolor: 'background.paper',
        borderBottom: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Toolbar>
        <IconButton
          edge="start"
          color="inherit"
          onClick={() => dispatch(toggleSidebar())}
          sx={{ mr: 2 }}
        >
          <MenuIcon />
        </IconButton>

        <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
          <Typography variant="h6" component="div" sx={{ fontWeight: 700, mr: 2 }}>
            StockAI Trading
          </Typography>
          <Chip
            label={websocketConnected ? 'Connected' : 'Disconnected'}
            color={websocketConnected ? 'success' : 'default'}
            size="small"
            sx={{ mr: 1 }}
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Notifications">
            <IconButton color="inherit">
              <NotificationsIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Toggle Theme">
            <IconButton color="inherit" onClick={() => dispatch(toggleTheme())}>
              {theme === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Settings">
            <IconButton color="inherit" onClick={() => navigate('/settings')}>
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>
    </MuiAppBar>
  )
}
