import { test, expect, chromium } from "@playwright/test";
import fs from "node:fs/promises";
import path from "path";

test("Milestone 1: Access G2 and solve captcha", async () => {
  const browser = await chromium.connectOverCDP("http://localhost:9222");
  const context = browser.contexts()[0]; // Use existing context
  const page = context.pages()[0]; // Use existing tab

  let currPage = 1;
  let hasNextPage = true;
  while (hasNextPage) {
    await page.goto(
      `https://www.capterra.in/directory/31123/financial-services/software`
    );

    await page.waitForLoadState("networkidle");

    const currentUrl = page.url();
    const pageTitle = await page.title();

    console.log("🌐 Current URL:", currentUrl);
    console.log("📄 Page title:", pageTitle);

    if (
      currentUrl.includes("capterra.in") &&
      !pageTitle.includes("unsual activity")
    ) {
      console.log(`Entered capterra page ${currPage}`);

      //check if the nextpage exists
      const nextButton = page.locator('a:has-text("Next")').first();
      const nextButtonExists = await nextButton.isVisible().catch(() => false);

      if (nextButtonExists) {
        hasNextPage = true;
      } else {
        hasNextPage = false;
      }

      const renderedHtml = await page.content();
      const filename = `captera-page-${currPage}.html`;
      currPage++;
      const resultdir = path.join(process.cwd(), "capterra-results");
      const filepath = path.join(resultdir, filename);
      await fs.writeFile(filepath, renderedHtml);
    }
  }


});
