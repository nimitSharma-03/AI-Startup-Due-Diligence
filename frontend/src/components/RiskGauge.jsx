function RiskGauge({ prediction }) {
  const value = prediction?.confidence ?? 0
  const color = prediction?.risk_level === 'High' ? '#dc2626' : prediction?.risk_level === 'Medium' ? '#d97706' : '#0d9488'

  return <section className="glass card"><div className="card-head"><div><h2>Confidence meter</h2><p className="card-subtitle">Probability of the selected outcome</p></div></div><div style={{ display: 'grid', placeItems: 'center', minHeight: 180 }}><div style={{ width: 142, aspectRatio: '1', borderRadius: '50%', display: 'grid', placeItems: 'center', background: `conic-gradient(${color} ${value * 3.6}deg, #e2e8f0 0)`, border: '1px solid #e2e8f0' }}><div style={{ width: 112, aspectRatio: '1', borderRadius: '50%', display: 'grid', placeItems: 'center', background: '#ffffff', textAlign: 'center' }}><strong>{value.toFixed(0)}%</strong><small className="muted">confidence</small></div></div></div></section>
}

export default RiskGauge
