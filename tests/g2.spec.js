import { test, expect, chromium } from "@playwright/test";
import fs from "node:fs/promises";
import path from "path";
import { execFile } from "node:child_process";

test("Milestone 1: Access G2 and solve captcha", async () => {
  const browser = await chromium.connectOverCDP("http://localhost:9222");
  const context = browser.contexts()[0]; // Use existing context
  const page = context.pages()[0]; // Use existing tab

  let currPage = 1;
  let hasNextPage = true;
  while (hasNextPage) {
    await page.goto(
      `https://www.g2.com/categories/billing?order=g2_score&page=${currPage}#product-list`, {
        timeout: 120000
      }
    );

    await page.waitForLoadState("networkidle");

    const currentUrl = page.url();
    const pageTitle = await page.title();

    console.log(" Current URL:", currentUrl);
    console.log(" Page title:", pageTitle);

    if (
      currentUrl.includes("g2.com") &&
      !pageTitle.includes("unsual activity")
    ) {
      console.log(`Entered G2 page ${currPage}`);

      //check if the nextpage exists
      const nextButton = page.locator('a:has-text("Next")').first();
      const nextButtonExists = await nextButton.isVisible().catch(() => false);

      if (nextButtonExists) {
        hasNextPage = true;
      } else {
        hasNextPage = false;
      }

      const renderedHtml = await page.content();
      const filename = `g2-page-${currPage}.html`;
      currPage++;
      const resultdir = path.join(process.cwd(), "results");
      const filepath = path.join(resultdir, filename);
      await fs.writeFile(filepath, renderedHtml);
    }
  }

  //now run the python script:
  // const child1 = execFile("cd results")
  // const child2 = execFile("source venv/bin/activate")
  // const child = execFile("python enrich.py", (error, stdout, stderr) => {
  //   if (error) {
  //     console.error(`exec error: ${error}`);
  //     return;
  //   }
  //   console.log(`stdout: ${stdout}`);
  //   console.log(`stderr: ${stderr}`);
  // });




});
