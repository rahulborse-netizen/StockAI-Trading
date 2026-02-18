import React, { useEffect, useState } from 'react'
import { Box, Chip, Typography, Paper } from '@mui/material'
import { TrendingUp, TrendingDown, ShowChart } from '@mui/icons-material'

export const PatternRecognition = ({ data = [] }) => {
  const [patterns, setPatterns] = useState([])

  useEffect(() => {
    if (data.length < 20) return

    const detectedPatterns = detectPatterns(data)
    setPatterns(detectedPatterns)
  }, [data])

  const detectPatterns = (candles) => {
    const patterns = []

    // Head and Shoulders
    if (detectHeadAndShoulders(candles)) {
      patterns.push({
        type: 'Head and Shoulders',
        signal: 'BEARISH',
        confidence: 0.75,
        position: candles.length - 5,
      })
    }

    // Double Top/Bottom
    const doubleTop = detectDoubleTop(candles)
    if (doubleTop) {
      patterns.push({
        type: 'Double Top',
        signal: 'BEARISH',
        confidence: doubleTop.confidence,
        position: doubleTop.position,
      })
    }

    const doubleBottom = detectDoubleBottom(candles)
    if (doubleBottom) {
      patterns.push({
        type: 'Double Bottom',
        signal: 'BULLISH',
        confidence: doubleBottom.confidence,
        position: doubleBottom.position,
      })
    }

    // Triangle Patterns
    const ascendingTriangle = detectAscendingTriangle(candles)
    if (ascendingTriangle) {
      patterns.push({
        type: 'Ascending Triangle',
        signal: 'BULLISH',
        confidence: ascendingTriangle.confidence,
        position: ascendingTriangle.position,
      })
    }

    const descendingTriangle = detectDescendingTriangle(candles)
    if (descendingTriangle) {
      patterns.push({
        type: 'Descending Triangle',
        signal: 'BEARISH',
        confidence: descendingTriangle.confidence,
        position: descendingTriangle.position,
      })
    }

    // Support/Resistance Levels
    const supportResistance = detectSupportResistance(candles)
    patterns.push(...supportResistance)

    return patterns
  }

  const detectHeadAndShoulders = (candles) => {
    if (candles.length < 20) return false

    const recent = candles.slice(-20)
    const highs = recent.map(c => c.high)
    const maxIndex = highs.indexOf(Math.max(...highs))

    if (maxIndex < 5 || maxIndex > recent.length - 5) return false

    const leftShoulder = Math.max(...highs.slice(0, maxIndex - 2))
    const head = highs[maxIndex]
    const rightShoulder = Math.max(...highs.slice(maxIndex + 2))

    const tolerance = head * 0.02

    return (
      Math.abs(leftShoulder - rightShoulder) < tolerance &&
      head > leftShoulder + tolerance &&
      head > rightShoulder + tolerance
    )
  }

  const detectDoubleTop = (candles) => {
    if (candles.length < 30) return null

    const recent = candles.slice(-30)
    const highs = recent.map(c => c.high)
    const maxHigh = Math.max(...highs)
    const maxIndex = highs.indexOf(maxHigh)

    if (maxIndex < 10 || maxIndex > recent.length - 10) return null

    const firstTop = maxHigh
    const secondTop = Math.max(...highs.slice(maxIndex + 5))

    const tolerance = firstTop * 0.02

    if (Math.abs(firstTop - secondTop) < tolerance) {
      return {
        confidence: 0.7,
        position: recent.length - 5,
      }
    }

    return null
  }

  const detectDoubleBottom = (candles) => {
    if (candles.length < 30) return null

    const recent = candles.slice(-30)
    const lows = recent.map(c => c.low)
    const minLow = Math.min(...lows)
    const minIndex = lows.indexOf(minLow)

    if (minIndex < 10 || minIndex > recent.length - 10) return null

    const firstBottom = minLow
    const secondBottom = Math.min(...lows.slice(minIndex + 5))

    const tolerance = firstBottom * 0.02

    if (Math.abs(firstBottom - secondBottom) < tolerance) {
      return {
        confidence: 0.7,
        position: recent.length - 5,
      }
    }

    return null
  }

  const detectAscendingTriangle = (candles) => {
    if (candles.length < 20) return null

    const recent = candles.slice(-20)
    const highs = recent.map(c => c.high)
    const lows = recent.map(c => c.low)

    const resistance = Math.max(...highs)
    const supportTrend = lows.slice(-10).every((low, i) => {
      if (i === 0) return true
      return low >= lows[i - 1]
    })

    if (supportTrend && Math.abs(highs[highs.length - 1] - resistance) < resistance * 0.03) {
      return {
        confidence: 0.65,
        position: recent.length - 5,
      }
    }

    return null
  }

  const detectDescendingTriangle = (candles) => {
    if (candles.length < 20) return null

    const recent = candles.slice(-20)
    const highs = recent.map(c => c.high)
    const lows = recent.map(c => c.low)

    const support = Math.min(...lows)
    const resistanceTrend = highs.slice(-10).every((high, i) => {
      if (i === 0) return true
      return high <= highs[i - 1]
    })

    if (resistanceTrend && Math.abs(lows[lows.length - 1] - support) < support * 0.03) {
      return {
        confidence: 0.65,
        position: recent.length - 5,
      }
    }

    return null
  }

  const detectSupportResistance = (candles) => {
    const patterns = []
    const recent = candles.slice(-50)

    // Find support levels (local minima)
    const supportLevels = []
    for (let i = 2; i < recent.length - 2; i++) {
      if (
        recent[i].low < recent[i - 1].low &&
        recent[i].low < recent[i - 2].low &&
        recent[i].low < recent[i + 1].low &&
        recent[i].low < recent[i + 2].low
      ) {
        supportLevels.push({
          price: recent[i].low,
          index: i,
        })
      }
    }

    // Find resistance levels (local maxima)
    const resistanceLevels = []
    for (let i = 2; i < recent.length - 2; i++) {
      if (
        recent[i].high > recent[i - 1].high &&
        recent[i].high > recent[i - 2].high &&
        recent[i].high > recent[i + 1].high &&
        recent[i].high > recent[i + 2].high
      ) {
        resistanceLevels.push({
          price: recent[i].high,
          index: i,
        })
      }
    }

    // Add strong support/resistance
    if (supportLevels.length > 0) {
      const strongSupport = supportLevels[supportLevels.length - 1]
      patterns.push({
        type: 'Support Level',
        signal: 'BULLISH',
        confidence: 0.6,
        position: strongSupport.index,
        price: strongSupport.price,
      })
    }

    if (resistanceLevels.length > 0) {
      const strongResistance = resistanceLevels[resistanceLevels.length - 1]
      patterns.push({
        type: 'Resistance Level',
        signal: 'BEARISH',
        confidence: 0.6,
        position: strongResistance.index,
        price: strongResistance.price,
      })
    }

    return patterns
  }

  if (patterns.length === 0) {
    return (
      <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
        <Typography variant="h6" gutterBottom>
          Pattern Recognition
        </Typography>
        <Typography variant="body2" color="text.secondary">
          No patterns detected
        </Typography>
      </Paper>
    )
  }

  return (
    <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
      <Typography variant="h6" gutterBottom>
        Pattern Recognition
      </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        {patterns.map((pattern, index) => (
          <Chip
            key={index}
            icon={
              pattern.signal === 'BULLISH' ? (
                <TrendingUp />
              ) : pattern.signal === 'BEARISH' ? (
                <TrendingDown />
              ) : (
                <ShowChart />
              )
            }
            label={`${pattern.type} (${(pattern.confidence * 100).toFixed(0)}%)`}
            color={pattern.signal === 'BULLISH' ? 'success' : pattern.signal === 'BEARISH' ? 'error' : 'default'}
            variant="outlined"
            sx={{ mb: 1 }}
          />
        ))}
      </Box>
    </Paper>
  )
}
