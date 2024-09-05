const puppeteer = require("puppeteer");
const fs = require("fs");
const path = require("path");

async function scrapeModelDetails(url, headful = false) {
  const browser = await puppeteer.launch({
    headless: !headful,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });
  const page = await browser.newPage();

  async function sectionExists(sectionName) {
    try {
      await page.waitForSelector(".mega-m__nav", { timeout: 15000 });
      const sectionLink = await page.$(`a[data-page-name='${sectionName}']`);
      return !!sectionLink;
    } catch (error) {
      console.error(`Error checking section '${sectionName}':`, error);
      return false;
    }
  }

  async function getName() {
    return await page.$eval("#main", (el) =>
      el.getAttribute("data-description")
    );
  }

  async function getBrand() {
    return await page.$eval("#main", (el) => el.getAttribute("data-brand"));
  }

  async function getModelNum() {
    return await page.$eval("#main", (el) => el.getAttribute("data-model-num"));
  }

  async function getModelType() {
    return await page.$eval("#main", (el) => el.getAttribute("data-modeltype"));
  }

  async function getSectionsPdfLinks() {
    if (!(await sectionExists("Sections"))) {
      return [];
    }

    try {
      const totalSectionCount = await page.$eval(
        ".section-title__count",
        (el) => parseInt(el.textContent.match(/\d+/)[0])
      );
      const sectionElements = await page.$$(".row.mb-3 .col-6");

      if (sectionElements.length !== totalSectionCount) {
        console.error(
          `Mismatch in section count: Found ${sectionElements.length}, but expected ${totalSectionCount}`
        );
        return [];
      }

      const sections = [];
      for (const section of sectionElements) {
        const sectionName = await section.$eval("span", (el) =>
          el.textContent.trim()
        );
        const sectionLink = await section.$eval("a", (el) => el.href);
        sections.push({ name: sectionName, url: sectionLink });
      }

      return sections;
    } catch (error) {
      console.error("Error finding section schema elements:", error);
      return [];
    }
  }

  async function getManualsLinks() {
    if (!(await sectionExists("Manuals"))) {
      return [];
    }

    try {
      // Find all manual links within the section
      const manualElements = await page.$$(
        ".d-flex.flex-wrap.mt-2.mb-4 a.mega-m__manuals"
      );
      const manuals = [];

      for (const manual of manualElements) {
        // Use $eval to get the text and href from the manual element
        const manualName = await manual.$eval(".mega-m__manuals__title", (el) =>
          el.textContent.trim()
        );
        const manualUrl = await manual.evaluate((el) =>
          el.getAttribute("href")
        );

        manuals.push({ name: manualName, url: manualUrl });
      }

      return manuals;
    } catch (error) {
      console.error("Error finding manual section elements:", error);
      return [];
    }
  }

  async function getParts() {
    if (!(await sectionExists("Parts"))) {
      return [];
    }

    const partsUrl = `${url}/Parts`;
    await page.goto(partsUrl, { waitUntil: "load", timeout: 0 });
    await new Promise((resolve) => setTimeout(resolve, 20)); // Wait for 2 seconds

    try {
      const summaryText = await page.$eval(".summary", (el) => el.textContent);
      const [rangeText, totalPartsText] = summaryText.split(" of ");
      const totalParts = parseInt(totalPartsText);
      const [start, end] = rangeText.split(" - ").map((num) => parseInt(num));
      const partsPerPage = end - start + 1;
      const totalPages = Math.ceil(totalParts / partsPerPage);

      const partDetails = [];

      for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
        const paginatedUrl = `${partsUrl}/?start=${pageNum}`;
        await page.goto(paginatedUrl, { waitUntil: "load", timeout: 0 });
        await new Promise((resolve) => setTimeout(resolve, 2)); // Wait for 2 seconds

        const partElements = await page.$$(".mega-m__part");

        for (const partElement of partElements) {
          try {
            const partName = await partElement.$eval(
              ".mega-m__part__name",
              (el) => el.textContent.trim()
            );
            const partLink = await partElement.$eval(
              "a",
              (el) => el.href.split("?")[0]
            );
            const partId = partLink.split("/").pop().split(".")[0];
            let partPrice = "No longer available";
            let partStatus = "No longer available";

            try {
              partPrice = await partElement.$eval(
                ".mega-m__part__price",
                (el) => el.textContent.trim()
              );
              partStatus = await partElement.$eval(".js-tooltip", (el) =>
                el.textContent.trim()
              );
            } catch (err) {
              // Handle missing price or status
            }

            partDetails.push({
              name: partName,
              id: partId,
              url: partLink,
              price: partPrice,
              status: partStatus,
            });
          } catch (error) {
            console.error("Error extracting part details:", error);
          }
        }

        if (partDetails.length >= totalParts) break;
      }

      return partDetails;
    } catch (error) {
      console.error("Error extracting part details:", error);
      return [];
    }
  }

  
  // Navigate to the main model URL
  await page.goto(url, { waitUntil: "load", timeout: 0 });
  await new Promise((resolve) => setTimeout(resolve, 20));

  const modelDetails = {
    url,
    name: await getName(),
    brand: await getBrand(),
    modelNum: await getModelNum(),
    modelType: await getModelType(),
    sections: await getSectionsPdfLinks(),
    manuals: await getManualsLinks(),
    parts: await getParts(),
    // QnA: await getQASection(),
    // installationInstruction: await getInstallationInstruction(),
    // youtubeVideos: await getYouTubeVideos(),
   
  };

  const jsonFilePath = path.join(__dirname, 'Data', 'Models', `${modelDetails.modelNum}.json`);
  fs.writeFileSync(jsonFilePath, JSON.stringify(modelDetails, null, 4));
  console.log(`Saved model details to ${jsonFilePath}`);

  await browser.close();

  return modelDetails
}


module.exports = { scrapeModelDetails };


// Example usage:
scrapeModelDetails("https://www.partselect.com/Models/FGHD2465NF1A/");
