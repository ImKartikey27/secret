// extract_urls.js
import XLSX from "xlsx";

const filePath = "/Users/kartikeysangal/Desktop/WebDev/Freelance/playwright/crunchBase-Results/crunchbase_orgs.xlsx"


const wb = XLSX.readFile(filePath);
const ws = wb.Sheets[wb.SheetNames[0]];
const rows = XLSX.utils.sheet_to_json(ws, { defval: "" });


const urls = rows
  .filter(r => r["Name"]?.toLowerCase() !== "crunchbase")
  .map(r => r["URL"])

  const size = urls.length



import { test, expect, chromium } from "@playwright/test";
import fs from "node:fs/promises";
import path from "path";

test("Access crunchbase and solve captcha", async () => {

    const browser = await chromium.connectOverCDP("http://localhost:9222");
    const context = browser.contexts()[0]
    const page = context.pages()[0]

    for(let i = 0 ; i < size ; i++){

        await page.goto(`${urls[i]}`,{
          waitForLoadState: "networkidle"
        });

        const delay = Math.floor(Math.random() * (6000 - 3000 + 1)) + 3000;
        await page.waitForTimeout(delay);


        const currentUrl = page.url();
        const pageTitle = await page.title();

        console.log(" Current URL:", currentUrl);
        console.log(" Page title:", pageTitle);

        if (currentUrl.includes("crunchbase.com") && pageTitle !=="Just a moment...") {
        console.log(`Entered crunchBase page`);

        const renderedHtml = await page.content();
        const filename = `crunchBase-${i}.html`;
        const resultdir = path.join(process.cwd(), "crunchbaseLoop2");
        const filepath = path.join(resultdir, filename);
        await fs.writeFile(filepath, renderedHtml);

        await page.mouse.move(500, 400, { steps: 20 });

    }
        if(pageTitle === "Just a moment..."){
          //captcha cloudflare
          console.log("Captcha Cloudflare detected")
          await page.waitForTimeout(3000)
          const renderedHtml = await page.content();
          const filename = `crunchBase-${i}.html`;
          const resultdir = path.join(process.cwd(), "crunchbaseLoop2");
          const filepath = path.join(resultdir, filename);
          await fs.writeFile(filepath, renderedHtml);

        }
      

    }

    
});