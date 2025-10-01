import { test, expect } from '@playwright/test';

test('load url', async ({ page }) => {
  
  await page.goto('https://www.g2.com/categories/accounting?order=g2_score#product-list', {waitUntil:'networkidle'});
  await page.pause()
  await page.getByText('Seller Details').click();
});