import { expect, test } from '@playwright/test'

test('mobile navigation works without horizontal scrolling', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Portfolio intelligence dashboard' })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
  expect(overflow).toBe(false)

  await page.getByRole('button', { name: 'Open navigation' }).click()
  await page.getByRole('dialog', { name: 'Navigation' }).getByRole('link', { name: 'Predict' }).click()
  await expect(page.getByRole('heading', { name: 'Score a startup' })).toBeVisible()
  await expect(page.getByRole('dialog')).toHaveCount(0)

  await page.goto('/startups/3')
  await expect(page.getByRole('heading', { name: 'Zencoder', level: 1 })).toBeVisible()
  const detailOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
  expect(detailOverflow).toBe(false)
})
