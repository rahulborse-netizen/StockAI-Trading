import React from 'react'
import { Snackbar, Alert } from '@mui/material'
import { useSelector, useDispatch } from 'react-redux'
import { removeNotification } from '../../store/slices/uiSlice'

export const NotificationContainer = () => {
  const dispatch = useDispatch()
  const notifications = useSelector(state => state.ui.notifications)

  const handleClose = (id) => {
    dispatch(removeNotification({ payload: id }))
  }

  return (
    <>
      {notifications.map((notification) => (
        <Snackbar
          key={notification.id}
          open={true}
          autoHideDuration={6000}
          onClose={() => handleClose(notification.id)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <Alert
            onClose={() => handleClose(notification.id)}
            severity={notification.severity || 'info'}
            sx={{ width: '100%' }}
          >
            {notification.message}
          </Alert>
        </Snackbar>
      ))}
    </>
  )
}
