import React, { useState } from 'react'
import { Box, ButtonGroup, Button, Tooltip } from '@mui/material'
import {
  ShowChart as TrendLineIcon,
  Timeline as FibonacciIcon,
  HorizontalRule as HorizontalLineIcon,
  VerticalAlignCenter as VerticalLineIcon,
  Rectangle as RectangleIcon,
  Highlight as HighlightIcon,
} from '@mui/icons-material'

export const DrawingTools = ({ onToolSelect, activeTool }) => {
  const tools = [
    { id: 'trendline', icon: <TrendLineIcon />, label: 'Trend Line' },
    { id: 'fibonacci', icon: <FibonacciIcon />, label: 'Fibonacci Retracement' },
    { id: 'horizontal', icon: <HorizontalLineIcon />, label: 'Horizontal Line' },
    { id: 'vertical', icon: <VerticalLineIcon />, label: 'Vertical Line' },
    { id: 'rectangle', icon: <RectangleIcon />, label: 'Rectangle' },
    { id: 'highlight', icon: <HighlightIcon />, label: 'Highlight' },
  ]

  return (
    <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
      <ButtonGroup variant="outlined" size="small">
        {tools.map((tool) => (
          <Tooltip key={tool.id} title={tool.label}>
            <Button
              onClick={() => onToolSelect(tool.id)}
              variant={activeTool === tool.id ? 'contained' : 'outlined'}
              color={activeTool === tool.id ? 'primary' : 'inherit'}
            >
              {tool.icon}
            </Button>
          </Tooltip>
        ))}
      </ButtonGroup>
    </Box>
  )
}
