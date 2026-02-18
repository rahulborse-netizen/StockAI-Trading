/**
 * Chart utility functions for technical analysis
 */

/**
 * Calculate Simple Moving Average (SMA)
 */
export const calculateSMA = (data, period) => {
  const result = []
  for (let i = period - 1; i < data.length; i++) {
    const sum = data.slice(i - period + 1, i + 1).reduce((acc, d) => acc + d.close, 0)
    result.push({ time: data[i].time, value: sum / period })
  }
  return result
}

/**
 * Calculate Exponential Moving Average (EMA)
 */
export const calculateEMA = (data, period) => {
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

/**
 * Calculate Bollinger Bands
 */
export const calculateBollingerBands = (data, period, stdDev) => {
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

  return { upper, lower, middle: sma }
}

/**
 * Calculate Relative Strength Index (RSI)
 */
export const calculateRSI = (data, period = 14) => {
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

/**
 * Calculate MACD (Moving Average Convergence Divergence)
 */
export const calculateMACD = (data, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) => {
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

  const histogram = macdLine.map((macd, i) => ({
    time: macd.time,
    value: macd.value - (signalLine[i]?.value || 0),
  }))

  return {
    macd: macdLine,
    signal: signalLine,
    histogram,
  }
}

/**
 * Format chart data for Lightweight Charts
 */
export const formatChartData = (data) => {
  return data.map((d, index) => ({
    time: d.time || d.date || index,
    open: parseFloat(d.open),
    high: parseFloat(d.high),
    low: parseFloat(d.low),
    close: parseFloat(d.close),
    volume: parseFloat(d.volume || 0),
  }))
}

/**
 * Detect chart patterns
 */
export const detectPatterns = (data) => {
  const patterns = []

  // Add pattern detection logic here
  // This is a simplified version - full implementation would include more patterns

  return patterns
}
