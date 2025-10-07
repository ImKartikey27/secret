import { test, expect, chromium } from "@playwright/test";
import fs from "node:fs/promises";
import path from "path";

test("Access clay and solve captcha", async () => {

    const browser = await chromium.connectOverCDP("http://localhost:9222");
    const context = browser.contexts()[0]; // Use existing context
    const page = context.pages()[0]; // Use existing tab

    await page.goto(
      `https://app.clay.com/workspaces/803882/workbooks/wb_0t3pm5djuzg2tRAM6jv/tables/t_0t3pm5fAET3iuCQiCjo/views/gv_0t3pm5fNZvNMJrDAdDc`,{
        waitUntil: "networkidle"
      }
    );
//https://www.crunchbase.com/discover/organization.companies/field/hubs/org_num/fintech-companies


    const currentUrl = page.url();
    const pageTitle = await page.title();

    console.log(" Current URL:", currentUrl);
    console.log(" Page title:", pageTitle);

    if (
      currentUrl.includes("app.clay.com") &&
      !pageTitle.includes("unsual activity")
    ) {
      console.log(`Entered clay page`);

      const renderedHtml = await page.content();
      const filename = `clay-Loop-1.html`;
      const resultdir = path.join(process.cwd(), "crunchBase-Results");
      const filepath = path.join(resultdir, filename);
      await fs.writeFile(filepath, renderedHtml);
    } 
});