import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout/Layout'
import { Dashboard } from './pages/Dashboard/Dashboard'
import { TradingSignals } from './pages/TradingSignals/TradingSignals'
import { Portfolio } from './pages/Portfolio/Portfolio'
import { Orders } from './pages/Orders/Orders'
import { Analytics } from './pages/Analytics/Analytics'
import { Settings } from './pages/Settings/Settings'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/signals" element={<TradingSignals />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  )
}

export default App
