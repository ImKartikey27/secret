import {chromium } from "@playwright/test";
import fs from "node:fs/promises";
import path from "path";
const connectionURL = 'wss://browser.zenrows.com?apikey=149f3e78fa0a275087d6c826995aa3b2b2e94b77';

(async () => {
    const browser = await chromium.connectOverCDP(connectionURL);
    const page = await browser.newPage();
    await page.goto('https://www.crunchbase.com/discover/organization.companies/183f107d1c30c240590a1039aa3aa1b7');
    console.log(await page.title());

    // while(await page.title() === "Just a moment..."){
      
    // }
    await page.waitForTimeout(6000)

    const renderedHtml = await page.content();
    const filename = `crunchBase-1.html`;
    const resultdir = path.join(process.cwd(), "crunchbaseLoop2");
    const filepath = path.join(resultdir, filename);
    await fs.writeFile(filepath, renderedHtml);

    await browser.close();
})();