import { test, expect, chromium } from "@playwright/test";
import * as fs from "fs";
import path from "path";
import XLSX from "xlsx";

const filePath =
  "/Users/kartikeysangal/Desktop/WebDev/Freelance/playwright/input.excel/Uni_Details_Modified.xlsx";

const wb = XLSX.readFile(filePath);
const ws = wb.Sheets[wb.SheetNames[0]];
const rows = XLSX.utils.sheet_to_json(ws, { defval: "" });

const universities = rows.map((r) => r["Name of Institution"]);
const job_positions = rows.map((r) => r["Job Position"]);
const size = universities.length;

test("Access google", async () => {
  const browser = await chromium.connectOverCDP("http://localhost:9222");
  const context = browser.contexts()[0];
  const page = context.pages()[0];


  for (let i = 0; i < size; i++) {
    const site = "linkedin.com/in";
    const university = universities[i];
    const job_position = job_positions[i];

    const query = `site:${site} ${university} ${job_position}`;
    const encodedQuery = encodeURIComponent(query);

    await page.goto(`https://www.google.com/search?q=${encodedQuery}`, {
      waitUntil: "networkidle",
    });
    let linkedinUrls;
    try {
      await page.waitForSelector('a.zReHs[jsname="UWckNb"]', { timeout: 5000 });

       linkedinUrls = await page.$$eval('a.zReHs[jsname="UWckNb"]', (elements) =>
        elements
          .map((el) => el.getAttribute("href"))
          .filter((href) => href && href.includes("linkedin.com/in"))
          .slice(0, 5)
      );
    } catch (error) {
      console.log("Timeout error", error);
    }
  

  console.log("Top 5 LinkedIn URLs:", linkedinUrls);

  const output_file = "/Users/kartikeysangal/Desktop/WebDev/Freelance/playwright/output.excel/output.xlsx";

  let wb1;
  let data;

  if(fs.existsSync(output_file)){
      wb1 = XLSX.readFile(output_file);
      const ws1 = wb1.Sheets[wb1.SheetNames[0]];
      data = XLSX.utils.sheet_to_json(ws1, {header: 1});
  }
  else{
      wb1 = XLSX.utils.book_new();
      data = [["Name of Institution", "Job Position", "LinkedIn URL"]];
  }

  const url_size = linkedinUrls.length;
  for(let j = 0; j < url_size; j++){
      data.push([university, job_position, linkedinUrls[j]]);
  }

  // Create new worksheet from updated data
  const new_ws = XLSX.utils.aoa_to_sheet(data);

  // Clear existing sheets and add the updated one
  wb1.SheetNames = ["Sheet1"];
  wb1.Sheets = { "Sheet1": new_ws };

  // Write the file
  XLSX.writeFile(wb1, output_file);

}
});
