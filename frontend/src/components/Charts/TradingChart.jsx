import React, { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts'
import { Box, Paper, Select, MenuItem, FormControl, InputLabel, ButtonGroup, Button, IconButton, Tooltip } from '@mui/material'
import { Settings as SettingsIcon, ZoomIn, ZoomOut, Fullscreen } from '@mui/icons-material'

export const TradingChart = ({ 
  data = [], 
  ticker = '',
  height = 500,
  showIndicators = true,
  showDrawingTools = true 
}) => {
  const chartContainerRef = useRef(null)
  const chartRef = useRef(null)
  const candlestickSeriesRef = useRef(null)
  const volumeSeriesRef = useRef(null)
  const [chartType, setChartType] = useState('candlestick')
  const [timeframe, setTimeframe] = useState('1D')
  const [indicators, setIndicators] = useState({
    sma: true,
    ema: false,
    bollinger: false,
    rsi: false,
    macd: false,
  })

  useEffect(() => {
    if (!chartContainerRef.current || !data.length) return

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#1e293b' },
        textColor: '#f1f5f9',
      },
      width: chartContainerRef.current.clientWidth,
      height: height,
      grid: {
        vertLines: { color: '#334155' },
        horzLines: { color: '#334155' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#334155',
      },
      timeScale: {
        borderColor: '#334155',
        timeVisible: true,
        secondsVisible: false,
      },
    })

    chartRef.current = chart

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    })

    candlestickSeriesRef.current = candlestickSeries

    // Format and set data
    const formattedData = data.map(d => ({
      time: d.time || d.date,
      open: parseFloat(d.open),
      high: parseFloat(d.high),
      low: parseFloat(d.low),
      close: parseFloat(d.close),
    }))

    candlestickSeries.setData(formattedData)

    // Add volume series
    if (data[0]?.volume) {
      const volumeSeries = chart.addHistogramSeries({
        color: '#3b82f6',
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: '',
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      })

      const volumeData = data.map(d => ({
        time: d.time || d.date,
        value: parseFloat(d.volume || 0),
        color: parseFloat(d.close) >= parseFloat(d.open) ? '#10b981' : '#ef4444',
      }))

      volumeSeries.setData(volumeData)
      volumeSeriesRef.current = volumeSeries
    }

    // Add indicators
    if (showIndicators) {
      addIndicators(chart, formattedData, indicators)
    }

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [data, height, showIndicators, indicators])

  const addIndicators = (chart, data, indicatorSettings) => {
    // SMA
    if (indicatorSettings.sma) {
      const sma20 = calculateSMA(data, 20)
      const smaSeries = chart.addLineSeries({
        color: '#3b82f6',
        lineWidth: 2,
        title: 'SMA 20',
      })
      smaSeries.setData(sma20)
    }

    // EMA
    if (indicatorSettings.ema) {
      const ema12 = calculateEMA(data, 12)
      const emaSeries = chart.addLineSeries({
        color: '#f59e0b',
        lineWidth: 2,
        title: 'EMA 12',
      })
      emaSeries.setData(ema12)
    }

    // Bollinger Bands
    if (indicatorSettings.bollinger) {
      const bb = calculateBollingerBands(data, 20, 2)
      const upperSeries = chart.addLineSeries({
        color: '#8b5cf6',
        lineWidth: 1,
        title: 'BB Upper',
      })
      const lowerSeries = chart.addLineSeries({
        color: '#8b5cf6',
        lineWidth: 1,
        title: 'BB Lower',
      })
      upperSeries.setData(bb.upper)
      lowerSeries.setData(bb.lower)
    }

    // RSI (as separate pane)
    if (indicatorSettings.rsi) {
      const rsi = calculateRSI(data, 14)
      const rsiSeries = chart.addLineSeries({
        color: '#ec4899',
        lineWidth: 2,
        priceScaleId: 'rsi',
        title: 'RSI',
      })
      chart.priceScale('rsi').applyOptions({
        scaleMargins: {
          top: 0.7,
          bottom: 0,
        },
      })
      rsiSeries.setData(rsi)
    }

    // MACD (as separate pane)
    if (indicatorSettings.macd) {
      const macd = calculateMACD(data, 12, 26, 9)
      const macdSeries = chart.addLineSeries({
        color: '#3b82f6',
        lineWidth: 2,
        priceScaleId: 'macd',
        title: 'MACD',
      })
      const signalSeries = chart.addLineSeries({
        color: '#f59e0b',
        lineWidth: 1,
        priceScaleId: 'macd',
        title: 'Signal',
      })
      chart.priceScale('macd').applyOptions({
        scaleMargins: {
          top: 0.7,
          bottom: 0,
        },
      })
      macdSeries.setData(macd.macd)
      signalSeries.setData(macd.signal)
    }
  }

  // Technical indicator calculations
  const calculateSMA = (data, period) => {
    const result = []
    for (let i = period - 1; i < data.length; i++) {
      const sum = data.slice(i - period + 1, i + 1).reduce((acc, d) => acc + d.close, 0)
      result.push({ time: data[i].time, value: sum / period })
    }
    return result
  }

  const calculateEMA = (data, period) => {
    const result = []
    const multiplier = 2 / (period + 1)
    let ema = data[0].close

    result.push({ time: data[0].time, value: ema })

    for (let i = 1; i < data.length; i++) {
      ema = (data[i].close - ema) * multiplier + ema
      result.push({ time: data[i].time, value: ema })
    }
    return result
  }

  const calculateBollingerBands = (data, period, stdDev) => {
    const sma = calculateSMA(data, period)
    const upper = []
    const lower = []

    for (let i = period - 1; i < data.length; i++) {
      const slice = data.slice(i - period + 1, i + 1)
      const mean = slice.reduce((acc, d) => acc + d.close, 0) / period
      const variance = slice.reduce((acc, d) => acc + Math.pow(d.close - mean, 2), 0) / period
      const std = Math.sqrt(variance)
      const smaValue = sma[i - period + 1]?.value || mean

      upper.push({ time: data[i].time, value: smaValue + stdDev * std })
      lower.push({ time: data[i].time, value: smaValue - stdDev * std })
    }

    return { upper, lower }
  }

  const calculateRSI = (data, period) => {
    const result = []
    const gains = []
    const losses = []

    for (let i = 1; i < data.length; i++) {
      const change = data[i].close - data[i - 1].close
      gains.push(change > 0 ? change : 0)
      losses.push(change < 0 ? Math.abs(change) : 0)

      if (i >= period) {
        const avgGain = gains.slice(-period).reduce((a, b) => a + b, 0) / period
        const avgLoss = losses.slice(-period).reduce((a, b) => a + b, 0) / period
        const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
        const rsi = 100 - (100 / (1 + rs))
        result.push({ time: data[i].time, value: rsi })
      }
    }

    return result
  }

  const calculateMACD = (data, fastPeriod, slowPeriod, signalPeriod) => {
    const fastEMA = calculateEMA(data, fastPeriod)
    const slowEMA = calculateEMA(data, slowPeriod)
    const macdLine = []

    for (let i = 0; i < fastEMA.length; i++) {
      if (slowEMA[i]) {
        macdLine.push({
          time: fastEMA[i].time,
          value: fastEMA[i].value - slowEMA[i].value,
        })
      }
    }

    const signalLine = calculateEMA(
      macdLine.map(m => ({ time: m.time, close: m.value })),
      signalPeriod
    )

    return {
      macd: macdLine,
      signal: signalLine,
    }
  }

  const handleIndicatorToggle = (indicator) => {
    setIndicators(prev => ({
      ...prev,
      [indicator]: !prev[indicator],
    }))
  }

  return (
    <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
      {/* Chart Controls */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2, flexWrap: 'wrap', gap: 2 }}>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Timeframe</InputLabel>
            <Select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} label="Timeframe">
              <MenuItem value="1m">1 Minute</MenuItem>
              <MenuItem value="5m">5 Minutes</MenuItem>
              <MenuItem value="15m">15 Minutes</MenuItem>
              <MenuItem value="1H">1 Hour</MenuItem>
              <MenuItem value="1D">1 Day</MenuItem>
              <MenuItem value="1W">1 Week</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Chart Type</InputLabel>
            <Select value={chartType} onChange={(e) => setChartType(e.target.value)} label="Chart Type">
              <MenuItem value="candlestick">Candlestick</MenuItem>
              <MenuItem value="line">Line</MenuItem>
              <MenuItem value="area">Area</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          {showIndicators && (
            <ButtonGroup size="small" variant="outlined">
              <Button onClick={() => handleIndicatorToggle('sma')} color={indicators.sma ? 'primary' : 'inherit'}>
                SMA
              </Button>
              <Button onClick={() => handleIndicatorToggle('ema')} color={indicators.ema ? 'primary' : 'inherit'}>
                EMA
              </Button>
              <Button onClick={() => handleIndicatorToggle('bollinger')} color={indicators.bollinger ? 'primary' : 'inherit'}>
                BB
              </Button>
              <Button onClick={() => handleIndicatorToggle('rsi')} color={indicators.rsi ? 'primary' : 'inherit'}>
                RSI
              </Button>
              <Button onClick={() => handleIndicatorToggle('macd')} color={indicators.macd ? 'primary' : 'inherit'}>
                MACD
              </Button>
            </ButtonGroup>
          )}

          <Tooltip title="Zoom In">
            <IconButton size="small">
              <ZoomIn />
            </IconButton>
          </Tooltip>
          <Tooltip title="Zoom Out">
            <IconButton size="small">
              <ZoomOut />
            </IconButton>
          </Tooltip>
          <Tooltip title="Fullscreen">
            <IconButton size="small">
              <Fullscreen />
            </IconButton>
          </Tooltip>
          <Tooltip title="Settings">
            <IconButton size="small">
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Chart Container */}
      <Box
        ref={chartContainerRef}
        sx={{
          width: '100%',
          height: height,
          position: 'relative',
        }}
      />
    </Paper>
  )
}
