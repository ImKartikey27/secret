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

  async function textOrEmpty(page, selector) {
    const el = await page.$(selector);
    if (!el) return "";
    const t = await el.textContent();
    return (t ?? "").trim();
  }

  for (let i = 353; i < size; i++) {
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
      const date_founded = await textOrEmpty(page, "span.component--field-formatter.field-type-date_precision")

      //scrape company domains
      const sel =
        "field-formatter.hide-external-link-icon link-formatter a.component--field-formatter.accent";
      await page.mouse.move(500, 400, { steps: 20 });
      let href = "";
      const el1 = await page.$(sel);
      if (el1) href = (await el1.getAttribute("href")) ?? "";

      //scrape company locations
      const locations = await page.$$eval(
        'a.accent[title][href*="/search/organizations/field/organization/location_identifiers/"]',
        (as) =>
          [
            ...new Set(
              as.map((a) => a.getAttribute("title")?.trim()).filter(Boolean)
            ),
          ].slice(0, 3)
      );

      //scrape company headcount
      let headcount = "";
      const el3 = await page.$('a.field-type-enum[href*="num_employees_enum"]');
      if (el3) headcount = (await el3.textContent())?.trim() ?? "";

      //scrape linkedin url
      let linkedinUrl = "";
      const el = await page.$('a[title="View on LinkedIn"]');
      if (el) {
        linkedinUrl = (await el.getAttribute("href")) ?? "";
      }

      // const founders = await page.$$eval('a.accent[href^="/person/"]', (as) =>
      //   as
      //     .filter((a) => a.classList.contains("accent"))
      //     .map((a) => (a.textContent ?? "").trim())
      // );

      // console.log(founders);

      //scrape emails
      const emails = await page.$$eval("field-formatter span", (spans) => {
        const re = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;
        return spans
          .map((s) => (s.textContent || "").trim())
          .filter((t) => re.test(t));
      });

      //scrape description (added two different selectors)

      const description1 =
        (await textOrEmpty(page, "span.description.has-overflow p")) ||
        (await textOrEmpty(page, "span.description")); // fallback

      const description2 = await textOrEmpty(
        page,
        "span.overflow-description p"
      );

      const description = description1 + " " + description2;

      //create company object
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

      const resultdir = path.join(process.cwd(), "output.excel");
      const file = path.join(resultdir, "companies.jsonl");
      await fs.mkdir(resultdir, { recursive: true });
      const line = JSON.stringify(company_object) + "\n";
      await fs.appendFile(file, line, "utf-8");

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
