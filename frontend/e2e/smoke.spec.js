import { expect, test } from '@playwright/test'

test('核心页面可导航且没有横向溢出', async ({ page }) => {
  for (const path of ['/overview/', '/scenario-data/', '/digital-twin/', '/agent-review/', '/knowledge-base/']) {
    await page.goto(path)
    await expect(page.locator('#app')).toBeVisible()
    await expect(page.locator('main')).toBeVisible()
    const horizontalPageScroll = await page.evaluate(() => {
      window.scrollTo({ left: 10_000, top: 0 })
      return window.scrollX
    })
    // The mobile navigation intentionally scrolls inside its own container;
    // the document itself must never drift horizontally.
    expect(horizontalPageScroll, path).toBe(0)
  }
})

test('三维场景明确展示模型或可解释降级状态', async ({ page }) => {
  await page.goto('/digital-twin/')
  const canvas = page.locator('canvas').first()
  const fallback = page.getByText(/模型|场景|资产|WebGL/).first()
  await expect(canvas.or(fallback)).toBeVisible({ timeout: 20_000 })
})

test('键盘焦点可见且页面具有唯一主标题', async ({ page }) => {
  await page.goto('/overview/')
  await expect(page.locator('h1')).toHaveCount(1)
  await page.keyboard.press('Tab')
  const focused = page.locator(':focus')
  await expect(focused).toBeVisible()
})
