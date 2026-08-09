import { FileUp, Download, FileText, CheckCircle2 } from 'lucide-react'
import { useState } from 'react'

function UploadCard({ onFileSelected, onGenerate, onDownload, loading, reportReady, companies = [], selectedRow, onCompanyChange }) {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [companySearch, setCompanySearch] = useState('')
  const pick = async (selected) => {
    if (!selected || !/\.(csv|xlsx|xls)$/i.test(selected.name)) return
    setFile(selected)
    await onFileSelected(selected)
  }

  return <section className="glass card report-upload">
    <div className="card-head"><div><h2>Generate diligence report</h2><p className="card-subtitle">Upload a spreadsheet, choose one company, then generate its PDF.</p></div><FileText size={20} /></div>
    <div className={`upload-zone ${dragging ? 'dragging' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); void pick(event.dataTransfer.files[0]) }}>
      <label htmlFor="startup-upload"><FileUp size={26} /><strong>{file ? file.name : 'Drop a startup spreadsheet here'}</strong><span className="muted">CSV, XLSX, XLS · smart column matching · PDF only</span></label>
      <input id="startup-upload" type="file" accept=".csv,.xlsx,.xls" onChange={(event) => { void pick(event.target.files[0]) }} />
    </div>
    {companies.length > 0 && <div className="field section-space"><label htmlFor="company-search">Company to analyze</label><input id="company-search" value={companySearch} placeholder="Search companies…" onChange={(event) => setCompanySearch(event.target.value)} /><select id="company-select" aria-label="Select company" value={selectedRow ?? ''} onChange={(event) => onCompanyChange(event.target.value)}><option value="" disabled>Select a company</option>{companies.filter((company) => company.label.toLowerCase().includes(companySearch.toLowerCase())).map((company) => <option value={company.row_index} key={company.row_index}>{company.label}</option>)}</select></div>}
    <div className="section-space" style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}><button className="button" disabled={!file || selectedRow === null || selectedRow === undefined || loading} onClick={() => onGenerate(file, selectedRow)}>{loading ? <><span className="button-spinner" /> Building report...</> : 'Generate PDF report'}</button>{reportReady && <button className="button button-secondary" onClick={onDownload}><Download size={16} /> Download PDF</button>}</div>
    {reportReady && <p className="report-success section-space"><CheckCircle2 size={17} /> Your institution-style report is ready.</p>}
  </section>
}

export default UploadCard
