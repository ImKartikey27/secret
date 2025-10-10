// extract_urls.js
import XLSX from "xlsx";

const filePath =
  "/Users/kartikeysangal/Desktop/WebDev/Freelance/playwright/crunchBase-Results/crunchbase_orgs.xlsx";

const wb = XLSX.readFile(filePath);
const ws = wb.Sheets[wb.SheetNames[0]];
const rows = XLSX.utils.sheet_to_json(ws, { defval: "" });

const urls = rows
  .filter((r) => r["Name"]?.toLowerCase() !== "crunchbase")
  .map((r) => r["URL"]);

const size = urls.length;

import { test, expect, chromium } from "@playwright/test";
import fs from "node:fs/promises";
import path from "path";

test("Access crunchbase and solve captcha", async () => {
  const browser = await chromium.connectOverCDP("http://localhost:9222");
  const context = browser.contexts()[0];
  const page = context.pages()[0];

  for (let i = 0; i < size; i++) {
    await page.goto(`${urls[i]}`, {
      waitForLoadState: "networkidle",
    });

    const delay = Math.floor(Math.random() * (6000 - 3000 + 1)) + 3000;
    await page.waitForTimeout(delay);

    const currentUrl = page.url();
    const pageTitle = await page.title();

    console.log(" Current URL:", currentUrl);
    console.log(" Page title:", pageTitle);

    if (
      currentUrl.includes("crunchbase.com") &&
      pageTitle !== "Just a moment..."
    ) {
      console.log(`Entered crunchBase page`);

      //start scraping specific data and keep it into variables

      const CompanyName = await page.textContent("span.entity-name");
      const overview = await page.textContent("span.expanded-only-content");
      const date_founded = await page.textContent(
        "span.component--field-formatter.field-type-date_precision"
      );

      const sel =
        "field-formatter.hide-external-link-icon link-formatter a.component--field-formatter.accent";
      await page.mouse.move(500, 400, { steps: 20 });
      const href = await page.getAttribute(sel, "href");

      const locations = await page.$$eval(
        'a.accent[title][href*="/search/organizations/field/organization/location_identifiers/"]',
        (as) =>
          [
            ...new Set(
              as.map((a) => a.getAttribute("title")?.trim()).filter(Boolean)
            ),
          ].slice(0, 3)
      );

      const headcount = await page.textContent(
        'a.field-type-enum[href*="num_employees_enum"]'
      );

      const linkedinUrl = await page.getAttribute(
        'a[title="View on LinkedIn"]',
        "href"
      );

      // const founders = await page.$$eval('a.accent[href^="/person/"]', (as) =>
      //   as
      //     .filter((a) => a.classList.contains("accent"))
      //     .map((a) => (a.textContent ?? "").trim())
      // );

      // console.log(founders);

      const emails = await page.$$eval("field-formatter span", (spans) => {
        const re = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;
        return spans
          .map((s) => (s.textContent || "").trim())
          .filter((t) => re.test(t));
      });

      const description1 =
        (await page.textContent("span.description.has-overflow p")) ?? "";
      const description2 =
        (await page.textContent("span.overflow-description p")) ?? "";
      const description = description1 + " " + description2;
      console.log(description);

      const company_object = {
        Name: CompanyName ?? "",
        Overview: overview ?? "",
        Date_Founded: date_founded ?? "",
        Locations: locations ?? "",
        Headcount: headcount ?? "",
        LinkedIn_URL: linkedinUrl ?? "",
        companyUrl: href ?? "",
        Email: emails[0] ?? "",
        Description: description,
      };

      const resultdir = path.join(process.cwd(), "output.excel")
      const file = path.join(resultdir,"companies.jsonl")
      await fs.mkdir(resultdir,{recursive: true})
      const line = JSON.stringify(company_object) + "\n"
      await fs.appendFile(file,line,"utf-8")


      await page.mouse.move(500, 400, { steps: 20 });
    }
    if (pageTitle === "Just a moment...") {
      //captcha cloudflare
      console.log("Captcha Cloudflare detected");
      await page.waitForTimeout(3000);
      const renderedHtml = await page.content();
      const filename = `crunchBase-${i}.html`;
      const resultdir = path.join(process.cwd(), "crunchbaseLoop2");
      const filepath = path.join(resultdir, filename);
      await fs.writeFile(filepath, renderedHtml);
    }
  }
});
