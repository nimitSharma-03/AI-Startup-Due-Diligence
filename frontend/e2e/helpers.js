import { expect } from '@playwright/test'
import fs from 'node:fs'

/** Click a report button, save the download and return its text-level facts. */
export async function downloadReport(page, button) {
  const [download] = await Promise.all([page.waitForEvent('download'), button.click()])
  const path = await download.path()
  const bytes = fs.readFileSync(path)
  expect(bytes.subarray(0, 5).toString()).toBe('%PDF-')
  expect(bytes.length).toBeGreaterThan(50_000)
  return { filename: download.suggestedFilename(), size: bytes.length }
}

export function trackErrors(page) {
  const errors = []
  page.on('pageerror', (error) => errors.push(String(error)))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
  return errors
}
