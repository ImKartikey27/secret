import { test, expect, chromium } from "@playwright/test";
import fs from "node:fs/promises";
import path from "path";

// Disable TLS rejection for proxy
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

test("Access crunchbase with proxy", async () => {

    // BrightData proxy configuration
    const proxy = {
        server: 'http://brd.superproxy.io:33335',
        username: 'brd-customer-hl_b9c52348-zone-residential_proxy1',
        password: '7if4nliavs1c'
    };

    // Launch new browser with proxy (don't use existing CDP connection)
    const browser = await chromium.launch({
        headless: false, // Keep visible for debugging
        proxy: proxy,
        args: [
            '--disable-blink-features=AutomationControlled',
            '--disable-features=VizDisplayCompositor',
        ]
    });

    const context = await browser.newContext({
        // Add realistic browser headers
        userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        viewport: { width: 1920, height: 1080 },
        locale: 'en-US',
        timezoneId: 'America/New_York',
        extraHTTPHeaders: {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    });

    const page = await context.newPage();


    await page.goto(
        `https://www.crunchbase.com/discover/organization.companies/183f107d1c30c240590a1039aa3aa1b7?pageId=10_a_825e8fa7-b362-4067-8da0-b6435ce67086`,
        { waitUntil: "networkidle", timeout: 120000 }
    );

    let pageNumber = 1;
    const resultdir = path.join(process.cwd(), "crunchBase-Results");


    while(true){
        const currentUrl = page.url();
        const pageTitle = await page.title();

        // Check for rate limiting or blocking
        if(pageTitle.includes("Error 1015") || pageTitle.includes("rate limited")) {
            console.log("Rate limited detected. Waiting longer...");
            await page.waitForTimeout(300000); // Wait 5 minutes
            await page.reload({ waitUntil: 'networkidle' });
            continue;
        }

        if(currentUrl.includes("crunchbase.com") && 
           !pageTitle.includes("Just a moment...") && 
           !pageTitle.includes("unusual activity")){

            console.log(`Scraping page ${pageNumber}...`);

            const renderedHtml = await page.content();
            const filename = `crunchbase-${pageNumber}.html`;
            const filepath = path.join(resultdir, filename);
            await fs.writeFile(filepath, renderedHtml);

            // Much longer realistic delays (30-120 seconds)
            const delay = Math.floor(Math.random() * (120000 - 30000 + 1)) + 30000;
            await page.waitForTimeout(delay);

            // Find next page link
            const nextLink = page.locator('a.page-button-next').first();
            const href = await nextLink.getAttribute('href');
            
            if(!href){
                console.log("No next page found. Scraping complete.");
                break;
            }
            else{
                pageNumber++;
                console.log(`Navigating to page ${pageNumber}...`);
                
                // Add some human-like behavior before navigating
                await page.mouse.move(Math.random() * 1000, Math.random() * 800);
                await page.waitForTimeout(2000);
                
                await page.goto(`https://www.crunchbase.com${href}`, {
                    waitUntil: "networkidle",
                    timeout: 120000
                });

                // Additional delay after page load
                const postLoadDelay = Math.floor(Math.random() * (15000 - 5000 + 1)) + 5000;
                await page.waitForTimeout(postLoadDelay);
            }
        } else {
            console.log("Page blocked or loading. Waiting...");
            await page.waitForTimeout(30000); // Wait 30 seconds
        }
    }

    await browser.close();
});