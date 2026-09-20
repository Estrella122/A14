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

test('左侧导航在桌面固定且移动端保持顶部导航', async ({ page }) => {
  await page.goto('/overview/')
  const sidebar = page.locator('.app-sidebar')
  await expect(sidebar).toBeVisible()
  const viewportWidth = page.viewportSize()?.width ?? 1280
  if (viewportWidth > 720) {
    await expect(sidebar).toHaveCSS('position', 'fixed')
    const before = await sidebar.boundingBox()
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    const after = await sidebar.boundingBox()
    expect(after?.y).toBe(before?.y)
  } else {
    await expect(sidebar).toHaveCSS('position', 'sticky')
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

test('缺少资产的跨场景任务不会覆盖当前项目模型与拓扑', async ({ page }) => {
  // The selected run is reloaded by ID after the initial latest-run response.
  await page.route('**/api/pipeline/runs/{latest,run-cross-scene}/', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ok: true, data: {
      run_id: 'run-cross-scene', original_name: 'Steel_industry_data.csv', status: 'completed',
      runtime_trace: { final_scene: 'steel_industry_energy', scene_status: 'confirmed' },
      stages: [], results: { standardization: { scenario: { scenario_id: 'steel_industry_energy', display_name: '钢铁工业能源监测' } } },
    } }),
  }))
  await page.goto('/overview/')
  await expect(page.getByRole('img', { name: '钢铁高炉数字孪生设备示意图' })).toBeVisible()
  await expect(page.getByText('项目拓扑回退')).toBeVisible()
  await expect(page.getByText('当前数据与项目拓扑不同，已停止绑定跨场景测点。')).toBeVisible()

  await page.goto('/digital-twin/')
  await expect(page.getByText('项目模型回退').first()).toBeVisible()
  await expect(page.getByText('BF—01')).toBeVisible()
})
