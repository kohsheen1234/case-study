const puppeteer = require("puppeteer");
const fs = require("fs");

async function ModelSymptomDetails(url) {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'load', timeout: 0 });

  // Extract all "Show All" links from the Symptoms section
  const showAllLinks = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('a.symptoms')).map(symptom => ({
          symptomName: symptom.querySelector('.symptoms__descr')?.innerText.trim(),
          showAllLink: symptom.href
      })).filter(link => link.showAllLink); // Ensure the link is defined
  });

  const allSymptomDetails = [];

  for (let link of showAllLinks) {
      // Navigate to each "Show All" link
      await page.goto(link.showAllLink, { waitUntil: 'load', timeout: 0 });

      // Extract symptom details from the page
      const symptomDetails = await page.evaluate(() => {
          const getSymptomData = (selector, parent) => {
              const element = parent.querySelector(selector);
              return element ? element.innerText.trim() : null;
          };

          // Collect part details ensuring uniqueness
          const partsInfo = [];
          let part = document.querySelector('.symptoms.align-items-center');
          while (part) {
              const partData = {
                  fixPercentage: getSymptomData('.symptoms__percent span', part),
                  partName: getSymptomData('.d-block.bold', part),
                  partNumber: getSymptomData('.text-sm a', part),
                  partPrice: getSymptomData('.mega-m__part__price', part),
                  availability: getSymptomData('.mega-m__part__avlbl span', part),
              };
              if (partData.partName) {
                  partsInfo.push(partData);
              }
              part = part.nextElementSibling;
          }

          return partsInfo;
      });

      allSymptomDetails.push({
          symptomName: link.symptomName || "Unknown symptom",
          details: symptomDetails,
      });
  }

  await browser.close();

  // Generate model ID from the URL
  const modelId = url.split('/').filter(Boolean).pop().replace(/\s+/g, '_');

  // Store the scraped data in a JSON file
  const modelDetails = {
      modelId : modelId,
      symptoms: allSymptomDetails.length > 0 ? allSymptomDetails : "No symptom details available"
  };

//   const jsonFilePath = path.join(__dirname, 'Data', 'Models', `${modelDetails.modelNum}.json`);
//   fs.writeFileSync(jsonFilePath, JSON.stringify(modelDetails, null, 2));

  fs.writeFileSync(`${modelId}_symptoms_details.json`, JSON.stringify(modelDetails, null, 2));
  console.log(`Model details saved as ${modelId}_symptoms_details.json`);

  return modelDetails;
}

module.exports =  {ModelSymptomDetails};


// ModelSymptomDetails("https://www.partselect.com/Models/DGBD2438PF5A/");