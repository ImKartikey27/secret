import { test, expect, chromium } from "@playwright/test";
import fs from "node:fs/promises";
import path from "path";

test("Access crunchbase and solve captcha", async () => {

    const browser = await chromium.connectOverCDP("http://localhost:9222");
    const context = browser.contexts()[0]; // Use existing context
    const page = context.pages()[0]; // Use existing tab

    await page.goto(
      `https://www.crunchbase.com/discover/organization.companies/e63a21b6dccf161a5eda1ea87e261d7c`,{
        waitUntil: "networkidle"
      }
    );
    let pageNumber = 1;
    while(true){

        const currentUrl = page.url()
        const pageTitle = await page.title()

        if(currentUrl.includes("crunchbase.com") && !pageTitle.includes("Just a moment...") && !pageTitle.includes("unsual activity")){

            console.log(`Entered crunchBase page ${pageNumber}`);
            

            const renderedHtml = await page.content()
            const filename = `crunchbase-${pageNumber}.html`
            const resultdir = path.join(process.cwd(), "crunchBase-Results")
            const filepath = path.join(resultdir, filename)
            await fs.writeFile(filepath, renderedHtml)

            console.log("Deplay after scraping");
            

            const delay = Math.floor(Math.random() * (15000 - 5000 + 1)) + 5000;
            await page.waitForTimeout(delay);


            //find next page and click it 
            const href = await page.locator('a.page-button-next').first().getAttribute('href');
            if(!href){
                console.log("No next page");
                break;
            }
            else{
                pageNumber++;
                await page.mouse.move(Math.random() * 1000, Math.random() * 800,{steps: 20});
                await page.goto(`https://www.crunchbase.com${href}`,{
                    waitUntil: "networkidle",
                    timeout: 120000
                })
                console.log("Deplay after page load");
                
                const postLoadDelay = Math.floor(Math.random() * (15000 - 5000 + 1)) + 5000;
                await page.mouse.move(Math.random() * 1000, Math.random() * 800,{steps: 20});
                await page.waitForTimeout(postLoadDelay);

            }
        }
    }
});