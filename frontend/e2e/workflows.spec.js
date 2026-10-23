import { expect, test } from '@playwright/test'
import { downloadReport, trackErrors } from './helpers'

test('API health endpoint responds from the same origin', async ({ request }) => {
  const response = await request.get('/api/health')
  expect(response.ok()).toBeTruthy()
  const body = await response.json()
  expect(body.data.model_loaded).toBe(true)
  expect(body.data.reference_rows).toBe(617)
})

test('workflow 1: dashboard → explorer → detail → company PDF', async ({ page }) => {
  const errors = trackErrors(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Portfolio intelligence dashboard' })).toBeVisible()
  await expect(page.getByText('Startups in dataset')).toBeVisible()
  await expect(page.getByText('617', { exact: true }).first()).toBeVisible()

  await page.getByRole('link', { name: 'Explore startups' }).click()
  await expect(page.getByTestId('startup-table')).toBeVisible()
  await expect(page.getByTestId('result-count')).toContainText('617 startups')

  await page.getByTestId('explorer-search').fill('zencoder')
  await expect(page.getByTestId('result-count')).toContainText('1 startups')
  await page.getByRole('link', { name: 'Zencoder' }).click()

  await expect(page).toHaveURL(/\/startups\/3$/)
  await expect(page.getByRole('heading', { name: 'Zencoder', level: 1 })).toBeVisible()
  await expect(page.getByText('Model prediction')).toBeVisible()
  await expect(page.getByText('Influencing inputs')).toBeVisible()
  const report = await downloadReport(page, page.getByTestId('download-report').first())
  expect(report.filename).toBe('Due_Diligence_Zencoder.pdf')
  expect(errors).toEqual([])
})

test('explorer filters and sorting change the results', async ({ page }) => {
  await page.goto('/explorer')
  await expect(page.getByTestId('result-count')).toContainText('617 startups')
  await page.getByRole('button', { name: /Filters/ }).click()
  await page.getByLabel('Recorded status').selectOption('Dead')
  await expect(page.getByTestId('result-count')).toContainText('85 startups')
  await expect(page).toHaveURL(/status=Dead/)

  await page.getByRole('button', { name: 'Funding' }).click()
  const firstFunding = page.getByTestId('startup-table').locator('tbody tr').first().locator('td').nth(4)
  await expect(firstFunding).toHaveText(/^\$10\.[89]M$/)

  // Refreshing keeps filters because they live in the URL.
  await page.reload()
  await expect(page.getByTestId('result-count')).toContainText('85 startups')
})

test('three different companies produce their own reports', async ({ page }) => {
  const seen = new Set()
  for (const [id, name] of [['3', 'Zencoder'], ['50', 'Greplin'], ['200', 'Submittable']]) {
    await page.goto(`/startups/${id}`)
    await expect(page.getByRole('heading', { name, level: 1 })).toBeVisible()
    const report = await downloadReport(page, page.getByTestId('download-report').first())
    expect(report.filename).toBe(`Due_Diligence_${name}.pdf`)
    seen.add(report.filename)
  }
  expect(seen.size).toBe(3)
})

test('workflow 2: prediction form validates and returns a model result', async ({ page }) => {
  await page.goto('/predict')
  await page.getByRole('button', { name: /Run prediction/ }).click()
  await expect(page.getByText('Batch year is required.')).toBeVisible()

  await page.getByLabel(/Y Combinator batch year/).fill('2010')
  await page.getByLabel(/Total funding raised/).fill('lots')
  await page.getByRole('button', { name: /Run prediction/ }).click()
  await expect(page.getByText(/Enter an amount such as/)).toBeVisible()

  await page.getByLabel(/Total funding raised/).fill('2M')
  await page.getByLabel('Batch session').selectOption('Winter')
  await page.getByLabel('Headquarters city').fill('San Francisco')
  await page.getByLabel(/Markets/).fill('SaaS, Analytics')
  await page.getByRole('button', { name: /Run prediction/ }).click()
  const result = page.getByTestId('prediction-result')
  await expect(result).toBeVisible()
  await expect(result.getByText('Model-assigned class', { exact: true })).toBeVisible()
  await expect(result.getByText('Influencing inputs')).toBeVisible()
  await expect(result.getByText(/Model estimate: Operating/)).toBeVisible()
})

test('prediction API rejects invalid input with field errors', async ({ request }) => {
  const response = await request.post('/api/predict', { data: { year: 'abc', total_funding: -1 } })
  expect(response.status()).toBe(422)
  const body = await response.json()
  expect(Object.keys(body.error.details).sort()).toEqual(['total_funding', 'year'])
})

test('workflow 3: upload CSV → validate → preview → analyse → report', async ({ page }) => {
  const csv = [
    'Company Name,Founded Year,Session,Funding,City,Industry,Status',
    'Orbit Analytics,2012,Summer,$3M,San Francisco,"SaaS, Analytics",Operating',
    'Pebble Foods,2009,Winter,0,Boston,E-Commerce,Closed',
    'Quartz Pay,2011,Summer,900k,New York City,Finance,Acquired',
    'Broken Row,,Winter,10,Austin,SaaS,',
  ].join('\n')
  await page.goto('/upload')
  await page.getByTestId('file-input').setInputFiles({ name: 'portfolio.csv', mimeType: 'text/csv', buffer: Buffer.from(csv) })
  const report = page.getByTestId('upload-report')
  await expect(report).toBeVisible()
  await expect(report.getByText('Rows with issues')).toBeVisible()
  await expect(report.getByText(/Row 4 \(Broken Row\): year is required/)).toBeVisible()
  await expect(report.getByRole('cell', { name: 'Orbit Analytics' })).toBeVisible()

  await page.getByTestId('activate-dataset').click()
  await expect(page.getByTestId('upload-success')).toBeVisible()
  await page.getByRole('link', { name: 'Open in explorer' }).click()
  await expect(page.getByTestId('result-count')).toContainText('4 startups')

  await page.getByRole('link', { name: 'Quartz Pay' }).click()
  await expect(page.getByRole('heading', { name: 'Quartz Pay', level: 1 })).toBeVisible()
  await expect(page.getByText('Uploaded dataset · row 3')).toBeVisible()
  const pdf = await downloadReport(page, page.getByTestId('download-report').first())
  expect(pdf.filename).toBe('Due_Diligence_Quartz_Pay.pdf')

  await page.goto('/reports')
  await page.getByTestId('report-search').fill('orbit')
  await page.getByRole('option', { name: /Orbit Analytics/ }).click()
  await expect(page.getByTestId('selected-startup')).toContainText('Orbit Analytics')
  const second = await downloadReport(page, page.getByTestId('download-report'))
  expect(second.filename).toBe('Due_Diligence_Orbit_Analytics.pdf')

  // Return to the reference dataset.
  await page.getByRole('button', { name: 'Use reference dataset' }).click()
  await expect(page.getByText('Y Combinator reference dataset (2005-2014)').first()).toBeVisible()
})

test('upload rejects unsupported files', async ({ page }) => {
  await page.goto('/upload')
  await page.getByTestId('file-input').setInputFiles({ name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('hello') })
  await expect(page.getByText('Only .csv files are supported.')).toBeVisible()
})

test('workflow 4: model analytics shows real evaluation results', async ({ page }) => {
  await page.goto('/analytics')
  await expect(page.getByRole('heading', { name: /Evaluation, explainability/ })).toBeVisible()
  await expect(page.getByText('Model comparison')).toBeVisible()
  await expect(page.getByText('Random Forest, calibrated (deployed)')).toBeVisible()
  await expect(page.getByText('Confusion matrix (hold-out)')).toBeVisible()
  await expect(page.getByText('Global feature importance')).toBeVisible()
  await expect(page.getByText('Batch-year confound')).toBeVisible()
  const metrics = await (await page.request.get('/api/model/metrics')).json()
  const balanced = (metrics.data.holdout.metrics.balanced_accuracy * 100).toFixed(1)
  await expect(page.getByText(`${balanced}%`).first()).toBeVisible()
})

test('workflow 5: direct navigation and refresh on every route', async ({ page }) => {
  const errors = trackErrors(page)
  for (const [path, heading] of [
    ['/', 'Portfolio intelligence dashboard'],
    ['/explorer', 'Search and screen startups'],
    ['/startups/3', 'Zencoder'],
    ['/predict', 'Score a startup'],
    ['/upload', 'Analyse your own startup list'],
    ['/analytics', 'Evaluation, explainability and limitations'],
    ['/reports', 'Company due diligence reports'],
    ['/about', 'How the platform works'],
    ['/does-not-exist', 'Page not found'],
  ]) {
    await page.goto(path)
    await expect(page.getByRole('heading', { name: heading, level: 1 })).toBeVisible()
    await page.reload()
    await expect(page.getByRole('heading', { name: heading, level: 1 })).toBeVisible()
  }
  const missing = await page.goto('/startups/99999')
  expect(missing.status()).toBe(200)
  await expect(page.getByText('No startup with this id exists in the selected dataset.')).toBeVisible()
  expect(errors.filter((e) => !e.includes('404'))).toEqual([])
})
