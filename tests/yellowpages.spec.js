import { cities } from "../test.js";

let size = cities.length;

import { test, expect, chromium } from "@playwright/test";
import Yellow from "../models/Yellow.schema.js";

test("Access clay and solve captcha", async () => {
  const browser = await chromium.connectOverCDP("http://localhost:9222");
  const context = browser.contexts()[0];
  const page = context.pages()[0];

  let i = 0;

  for ( i ; i < size; i++) {
    const url = `https://www.yellowpages.com/search?search_terms=general+contractor&geo_location_terms=${encodeURI(
      cities[i]
    )}%2C+TX`;

    await page.goto(`${url}`, {
      waitUntil: "networkidle",
    });

    //delay just after page loads
    const delay = Math.floor(Math.random() * (15000 - 5000 + 1)) + 5000;
    await page.waitForTimeout(delay);

    //random mouse moments
    await page.mouse.move(Math.random() * 1000, Math.random() * 800, {
      steps: 20,
    });

    while (true) {
      const ranked = await page.$$eval("h2.n", (heads) => {
        const base = "https://www.yellowpages.com";

        return heads
          .map((h2) => {
            const text = h2.textContent?.trim() || "";
            const m = text.match(/^(\d+)\.\s*(.*)$/); // only keep "1. Company" style
            if (!m) return null;

            const rank = Number(m[1]);
            const name = m[2];

            // find the <a class="business-name"> in the same card
            const card = h2.closest(".result");
            const a = card?.querySelector("a.business-name");

            if (!a) return null;

            // make absolute URL
            const hrefRaw = a.getAttribute("href") || "";
            const url = hrefRaw.startsWith("http")
              ? hrefRaw
              : new URL(hrefRaw, base).toString();

            //extract domain from it
            let domain = "";
            const websiteLink = card?.querySelector("a.track-visit-website");
            if (websiteLink) {
              const websiteHref = websiteLink.getAttribute("href") || "";
              domain = websiteHref;
            }
            //extract mobile number 
            let phone = ""
            const phonenumber = card?.querySelector("div.phones.phone.primary")
            if(phonenumber){
              phone = phonenumber.textContent?.trim() || ""
            }
            //extract address 
            let address = ""
            let street_address = card?.querySelector("div.street-address")
            let locality = card?.querySelector("div.locality")
            if(street_address){
                address = address + street_address.textContent?.trim() || ""
            }
            if(locality){
                address = address + ", " + locality.textContent?.trim() || ""
            }
            if(domain === ""){
              return null
            }
            return { rank, name, url, domain, phone, address};
          })
          .filter(Boolean);
      });
      await page.mouse.move(Math.random() * 1000, Math.random() * 800, {
        steps: 20,
      });

      for (let k = 0; k < ranked.length; k++) {
        const data = ranked[k];
        const data1 = {...data, "city": cities[i]}

        try {

          const yellow = new Yellow(data1)
          await yellow.save()
          
        } catch (error) {
          if(error.code === 11000){
            console.log("Duplicate entry")
            continue;
          }else{
            throw error;
          }
          
        }
      }

      const nextLink = page.locator(`a.next.ajax-page`);
      const disabledNext = page.locator(`div.next`);
      if (
        (await disabledNext.first().isVisible()) ||
        (await nextLink.count()) === 0
      ) {
        break;
      }
      const href = await nextLink.getAttribute("href");
      if (!href) break;

      const nexturl = "https://www.yellowpages.com" + href;
      //random mouse moments
      await page.mouse.move(Math.random() * 1000, Math.random() * 800, {
        steps: 20,
      });

      //go to next page
      await page.goto(nexturl, { waitUntil: "networkidle" });

      const delay2 = Math.floor(Math.random() * (10000 - 5000 + 1)) + 5000;
      await page.waitForTimeout(delay2);
    }
  }
});
