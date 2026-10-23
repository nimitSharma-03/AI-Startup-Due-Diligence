import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatPct, OUTCOME_COLORS, OUTCOMES } from '../lib/format'

const AXIS = { fill: '#64748b', fontSize: 11 }
const GRID = '#e2e8f0'
const TOOLTIP = {
  contentStyle: { borderRadius: 8, border: '1px solid #e2e8f0', boxShadow: '0 8px 24px rgba(15,23,42,.08)', fontSize: 12 },
  cursor: { fill: 'rgba(148,163,184,.12)' },
}

/** Horizontal bars for a ranked categorical distribution (single series). */
export function DistributionBars({ data, color = '#2a78d6', height, valueLabel = 'Startups', colorFor }) {
  if (!data?.length) return <p className="py-8 text-center text-sm text-slate-500">No data available.</p>
  const chartHeight = height || Math.max(140, data.length * 30 + 20)
  return (
    <div style={{ height: chartHeight }} role="img" aria-label={`${valueLabel} by category`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 4, right: 36, top: 4, bottom: 4 }} barCategoryGap={6}>
          <CartesianGrid horizontal={false} stroke={GRID} />
          <XAxis type="number" tick={AXIS} axisLine={false} tickLine={false} allowDecimals={false} />
          <YAxis type="category" dataKey="name" width={118} tick={AXIS} axisLine={false} tickLine={false} interval={0} />
          <Tooltip {...TOOLTIP} formatter={(value) => [value, valueLabel]} />
          <Bar
            dataKey="count"
            radius={[0, 4, 4, 0]}
            label={{ position: 'right', fill: '#334155', fontSize: 11 }}
            shape={(props) => <rect {...props} fill={colorFor ? colorFor(props.payload) : color} rx={3} />}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function OutcomeBars({ data }) {
  return <DistributionBars data={data} colorFor={(row) => OUTCOME_COLORS[row.name] || '#94a3b8'} height={130} />
}

/** Stacked recorded status by batch year. */
export function YearStatusChart({ data }) {
  if (!data?.length) return <p className="py-8 text-center text-sm text-slate-500">No year data available.</p>
  const series = OUTCOMES.filter((label) => data.some((row) => row[label]))
  const unlabelled = data.some((row) => row.Unlabelled)
  return (
    <div className="h-72" role="img" aria-label="Startups by batch year and recorded status">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ left: -12, right: 8, top: 8 }}>
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey="year" tick={AXIS} axisLine={{ stroke: '#cbd5e1' }} tickLine={false} />
          <YAxis tick={AXIS} axisLine={false} tickLine={false} allowDecimals={false} />
          <Tooltip {...TOOLTIP} />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
          {series.map((label) => (
            <Bar key={label} dataKey={label} stackId="a" fill={OUTCOME_COLORS[label]} stroke="#fff" strokeWidth={1} isAnimationActive={false} />
          ))}
          {unlabelled && <Bar dataKey="Unlabelled" stackId="a" fill="#94a3b8" stroke="#fff" strokeWidth={1} isAnimationActive={false} />}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Probability per class with the historical base rate as a tick. */
export function ProbabilityBars({ probabilities, priors }) {
  return (
    <div className="space-y-3">
      {OUTCOMES.map((label) => {
        const value = probabilities?.[label] ?? 0
        const prior = priors?.[label]
        return (
          <div key={label}>
            <div className="mb-1 flex items-baseline justify-between text-sm">
              <span className="flex items-center gap-2 font-medium text-slate-700">
                <span className="size-2.5 rounded-full" style={{ background: OUTCOME_COLORS[label] }} aria-hidden />
                {label}
              </span>
              <span className="num font-semibold text-navy-900">
                {formatPct(value)}
                {prior !== undefined && <span className="ml-2 text-xs font-normal text-slate-500">base {formatPct(prior)}</span>}
              </span>
            </div>
            <div className="relative h-2.5 rounded-full bg-slate-100" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)} aria-label={`${label} probability`}>
              <div className="h-full rounded-full" style={{ width: `${value * 100}%`, background: OUTCOME_COLORS[label] }} />
              {prior !== undefined && (
                <div className="absolute -top-1 h-4.5 w-0.5 rounded bg-navy-900" style={{ left: `calc(${prior * 100}% - 1px)` }} title={`Base rate ${formatPct(prior)}`} />
              )}
            </div>
          </div>
        )
      })}
      <p className="text-xs text-slate-500">Dark tick = share of each outcome in the training data (base rate).</p>
    </div>
  )
}

/** Diverging bars: how far each input moves P(outcome) versus typical values. */
export function ContributionBars({ explanation, outcome }) {
  if (!explanation?.length) return null
  const values = explanation.map((item) => item.contributions[outcome] * 100)
  const span = Math.max(1, ...values.map(Math.abs))
  return (
    <div className="space-y-2.5">
      {explanation.map((item, index) => {
        const value = values[index]
        const width = (Math.abs(value) / span) * 50
        return (
          <div key={item.field} className="grid grid-cols-[minmax(0,9rem)_1fr_3.5rem] items-center gap-3 text-sm sm:grid-cols-[minmax(0,13rem)_1fr_4rem]">
            <div className="min-w-0">
              <p className="font-medium text-slate-700">{item.label}</p>
              <p className="truncate text-xs text-slate-500" title={item.value}>
                {item.value}
              </p>
            </div>
            <div className="relative h-3 rounded bg-slate-50">
              <div className="absolute inset-y-0 left-1/2 w-px bg-slate-300" />
              <div
                className="absolute inset-y-0 rounded"
                style={{
                  width: `${width}%`,
                  left: value >= 0 ? '50%' : `${50 - width}%`,
                  background: value >= 0 ? '#0f766e' : '#d03b3b',
                }}
              />
            </div>
            <span className="num text-right text-xs font-semibold text-slate-700">
              {value >= 0 ? '+' : ''}
              {value.toFixed(1)} pts
            </span>
          </div>
        )
      })}
    </div>
  )
}

export function RocChart({ curves }) {
  if (!curves) return null
  const series = OUTCOMES.filter((label) => curves[label])
  return (
    <div className="h-72" role="img" aria-label="One-vs-rest ROC curves on the hold-out set">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart margin={{ left: -8, right: 12, top: 8, bottom: 12 }}>
          <CartesianGrid stroke={GRID} />
          <XAxis type="number" dataKey="fpr" domain={[0, 1]} tick={AXIS} tickLine={false} label={{ value: 'False positive rate', position: 'insideBottom', offset: -6, fill: '#64748b', fontSize: 11 }} />
          <YAxis type="number" dataKey="tpr" domain={[0, 1]} tick={AXIS} tickLine={false} />
          <Tooltip {...TOOLTIP} formatter={(value) => Number(value).toFixed(2)} labelFormatter={(value) => `FPR ${Number(value).toFixed(2)}`} />
          <Legend iconType="plainline" wrapperStyle={{ fontSize: 12 }} verticalAlign="top" />
          <Line data={[{ fpr: 0, tpr: 0 }, { fpr: 1, tpr: 1 }]} dataKey="tpr" stroke="#94a3b8" strokeDasharray="4 4" dot={false} name="Chance" isAnimationActive={false} />
          {series.map((label) => (
            <Line key={label} data={curves[label].points} dataKey="tpr" stroke={OUTCOME_COLORS[label]} strokeWidth={2} dot={false} name={`${label} (AUC ${curves[label].auc.toFixed(2)})`} isAnimationActive={false} type="stepAfter" />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ConfusionMatrix({ labels, matrix, caption }) {
  const max = Math.max(...matrix.flat(), 1)
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[340px] border-separate border-spacing-1 text-sm">
        <caption className="mb-2 text-left text-xs text-slate-500">{caption}</caption>
        <thead>
          <tr>
            <th className="text-left text-xs font-medium text-slate-500">Recorded ↓ / Assigned →</th>
            {labels.map((label) => (
              <th key={label} className="text-xs font-semibold text-slate-700">
                {label}
              </th>
            ))}
            <th className="text-xs font-medium text-slate-500">Recall</th>
          </tr>
        </thead>
        <tbody>
          {labels.map((actual, i) => {
            const total = matrix[i].reduce((a, b) => a + b, 0)
            return (
              <tr key={actual}>
                <th className="text-left text-xs font-semibold text-slate-700">{actual}</th>
                {matrix[i].map((value, j) => {
                  const intensity = value / max
                  return (
                    <td
                      key={labels[j]}
                      className="num rounded-md py-3 text-center font-semibold"
                      style={{
                        background: `rgba(42,120,214,${0.08 + intensity * 0.82})`,
                        color: intensity > 0.5 ? '#fff' : '#0f172a',
                        outline: i === j ? '2px solid #0b1f3a' : 'none',
                        outlineOffset: -2,
                      }}
                    >
                      {value}
                    </td>
                  )
                })}
                <td className="num text-center text-xs text-slate-600">{total ? formatPct(matrix[i][i] / total, 0) : '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export function ShareBars({ items }) {
  return (
    <div className="space-y-2.5">
      {items.map((item) => (
        <div key={item.field} className="grid grid-cols-[8.5rem_1fr_3rem] items-center gap-3 text-sm">
          <span className="truncate text-slate-700">{item.label}</span>
          <div className="h-2 rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-navy-700" style={{ width: `${item.share * 100}%` }} />
          </div>
          <span className="num text-right text-xs font-semibold text-slate-700">{formatPct(item.share, 0)}</span>
        </div>
      ))}
    </div>
  )
}

/** Bars for importance scores; handles decimals and small negative values. */
export function ImportanceBars({ items, digits = 3, color = '#256abf' }) {
  const max = Math.max(...items.map((item) => Math.abs(item.value)), 1e-9)
  return (
    <div className="space-y-2.5">
      {items.map((item) => (
        <div key={item.name} className="grid grid-cols-[minmax(0,10rem)_1fr_4rem] items-center gap-3 text-sm">
          <span className="truncate text-slate-700" title={item.name}>
            {item.name}
          </span>
          <div className="h-2.5 rounded-full bg-slate-100">
            <div className="h-full rounded-full" style={{ width: `${(Math.max(0, item.value) / max) * 100}%`, background: color }} />
          </div>
          <span className="num text-right text-xs font-semibold text-slate-700">{item.value.toFixed(digits)}</span>
        </div>
      ))}
    </div>
  )
}
