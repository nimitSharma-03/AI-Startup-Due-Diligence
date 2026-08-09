import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function Charts({ metrics, batchResult }) {
  const metricData = [
    ['Accuracy', metrics?.accuracy],
    ['Precision', metrics?.precision],
    ['Recall', metrics?.recall],
    ['F1', metrics?.f1],
    ['ROC-AUC', metrics?.roc_auc],
  ]
    .filter(([, value]) => typeof value === 'number')
    .map(([name, value]) => ({ name, score: Number((value * 100).toFixed(1)) }))

  const distribution = (batchResult?.results || []).reduce((items, row) => {
    const prediction = row.Prediction || 'Unknown'
    items[prediction] = (items[prediction] || 0) + 1
    return items
  }, {})
  const predictionData = Object.entries(distribution).map(([name, count]) => ({
    name,
    count,
  }))

  return (
    <>
      <section className="glass card">
        <div className="card-head">
          <div>
            <h2>Model metrics</h2>
            <p className="card-subtitle">Held-out evaluation performance</p>
          </div>
        </div>
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={metricData}>
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={{ stroke: '#cbd5e1' }} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 6, boxShadow: '0 8px 20px rgba(15, 23, 42, 0.10)' }}
                formatter={(value) => `${value}%`}
              />
              <Bar dataKey="score" fill="#1e3a8a" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
      <section className="glass card">
        <div className="card-head">
          <div>
            <h2>Prediction distribution</h2>
            <p className="card-subtitle">Available after a batch portfolio score</p>
          </div>
        </div>
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={predictionData}>
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={{ stroke: '#cbd5e1' }} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 6, boxShadow: '0 8px 20px rgba(15, 23, 42, 0.10)' }} />
              <Bar dataKey="count" fill="#0d9488" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </>
  )
}

export default Charts
