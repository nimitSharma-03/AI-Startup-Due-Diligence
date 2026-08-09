import { useCallback, useEffect, useState } from 'react'
import { RefreshCw, Send } from 'lucide-react'
import Charts from '../components/Charts'
import FeatureImportance from '../components/FeatureImportance'
import Hero from '../components/Hero'
import Loading from '../components/Loading'
import PredictionCard from '../components/PredictionCard'
import RiskGauge from '../components/RiskGauge'
import UploadCard from '../components/UploadCard'
import { generateDueDiligenceReport, getDashboardData, getReportCompanies, predictStartup } from '../services/api'

function Dashboard() {
  const [data, setData] = useState(null); const [form, setForm] = useState({}); const [prediction, setPrediction] = useState(null)
  const [reportUrl, setReportUrl] = useState(null); const [reportName, setReportName] = useState('ai_startup_due_diligence_report.pdf')
  const [companies, setCompanies] = useState([]); const [selectedRow, setSelectedRow] = useState(null)
  const [loading, setLoading] = useState(true); const [predicting, setPredicting] = useState(false); const [toast, setToast] = useState(null)
  const notify = useCallback((message, type = 'success') => { setToast({ message, type }); window.setTimeout(() => setToast(null), 4500) }, [])
  const load = useCallback(async () => { setLoading(true); try { const next = await getDashboardData(); setData(next); setForm(next.modelInfo.sample_input || {}) } catch (error) { notify(error.message, 'error') } finally { setLoading(false) } }, [notify])
  useEffect(() => { void load(); return () => { if (reportUrl) URL.revokeObjectURL(reportUrl) } }, [load])
  const runSingle = async () => { setPredicting(true); try { const next = await predictStartup(form); setPrediction(next); notify('Prediction completed.') } catch (error) { notify(error.message, 'error') } finally { setPredicting(false) } }
  const loadCompanies = async (file) => { setPredicting(true); setCompanies([]); setSelectedRow(null); if (reportUrl) { URL.revokeObjectURL(reportUrl); setReportUrl(null) } try { const result = await getReportCompanies(file); setCompanies(result.companies); notify(`Choose one of ${result.companies.length} companies to generate a report.`) } catch (error) { notify(error.message, 'error') } finally { setPredicting(false) } }
  const runReport = async (file, rowIndex) => { setPredicting(true); try { if (reportUrl) URL.revokeObjectURL(reportUrl); const response = await generateDueDiligenceReport(file, rowIndex); setReportUrl(URL.createObjectURL(response.data)); const disposition = response.headers['content-disposition'] || ''; const match = disposition.match(/filename="?([^";]+)"?/); setReportName(match?.[1] || 'ai_startup_due_diligence_report.pdf'); notify('Selected-company PDF due diligence report generated.') } catch (error) { notify(error.message, 'error') } finally { setPredicting(false) } }
  const download = () => { if (!reportUrl) return; const link = document.createElement('a'); link.href = reportUrl; link.download = reportName; link.click() }
  if (loading) return <main className="page"><Loading /></main>
  return <main className="page"><Hero healthy={data?.health?.model_loaded} /><div className="dashboard-grid"><UploadCard loading={predicting} onFileSelected={loadCompanies} companies={companies} selectedRow={selectedRow} onCompanyChange={(row) => setSelectedRow(row)} onGenerate={runReport} onDownload={download} reportReady={Boolean(reportUrl)} /><PredictionCard prediction={prediction} />{reportUrl && <section className="glass card wide report-preview"><div className="card-head"><div><h2>Report preview</h2><p className="card-subtitle">AI Startup Due Diligence Report</p></div><button className="button button-secondary" onClick={download}>Download PDF</button></div><iframe title="Due diligence report preview" src={reportUrl} /></section>}<section className="glass card wide"><div className="card-head"><div><h2>Single startup prediction</h2><p className="card-subtitle">Review the model inputs or begin with a representative dataset record.</p></div><button className="button button-secondary" onClick={load}><RefreshCw size={15} /> Retry connection</button></div><div className="form-grid">{data?.modelInfo?.features?.map((feature) => <div className="field" key={feature}><label htmlFor={feature}>{feature}</label><input id={feature} value={form[feature] ?? ''} onChange={(event) => setForm({ ...form, [feature]: event.target.value })} /></div>)}</div><div className="section-space"><button className="button" disabled={predicting} onClick={runSingle}><Send size={16} /> {predicting ? 'Analyzing...' : 'Analyze startup'}</button></div></section><RiskGauge prediction={prediction} /></div><div className="charts"><FeatureImportance data={data?.modelInfo?.feature_importance} /><Charts metrics={data?.metrics} /></div>{toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}</main>
}

export default Dashboard
