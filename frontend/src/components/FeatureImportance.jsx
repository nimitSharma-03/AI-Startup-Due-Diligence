import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

function FeatureImportance({ data = [] }) {
  return <section className="glass card"><div className="card-head"><div><h2>Feature importance</h2><p className="card-subtitle">What the model weighs most heavily</p></div></div><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout="vertical" margin={{ left: 8 }}><XAxis type="number" hide /><YAxis dataKey="feature" type="category" width={86} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 6, boxShadow: '0 8px 20px rgba(15, 23, 42, 0.10)' }} /><Bar dataKey="importance" radius={[0, 3, 3, 0]}>{data.map((item, index) => <Cell fill={index % 2 ? '#0d9488' : '#1e3a8a'} key={item.feature} />)}</Bar></BarChart></ResponsiveContainer></div></section>
}

export default FeatureImportance
