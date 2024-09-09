const puppeteer = require("puppeteer");
const fs = require("fs");
const path = require("path");

async function ModelSymptomDetails(url) {

    // Generate model ID from the URL
  const modelId = url.split('/').filter(Boolean).pop().replace(/\s+/g, '_');


    // const modelNumber =url.match(/\/Models\/([^\/]+)\//)[1];

    console.log("modelno:")
  console.log(modelId); // Output: 004621710A
   
    // console.log('Extracted PS Code:', psCode);

    // Define the path to the JSON file
    jsonFilePath_ = path.join("./src/scrape/Data/Models/", `${modelId}_symptoms_details.json`);
    console.log(jsonFilePath_)

    // Check if the JSON file already exists
    if (fs.existsSync(jsonFilePath_)) {
        console.log(`JSON file for ${modelId} symptoms already exists. Skipping...`);
        return null;
    }


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

  
  // Store the scraped data in a JSON file
  const modelDetails = {
      modelId : modelId,
      symptoms: allSymptomDetails.length > 0 ? allSymptomDetails : "No symptom details available"
  };


    const dirPath = path.join(__dirname, 'Data', 'Models'); 
    jsonFilePath = path.join(dirPath, `${modelId}_symptoms_details.json`);


  fs.writeFileSync(jsonFilePath, JSON.stringify(modelDetails, null, 4));
  console.log(`Model details saved as ${modelId}_symptoms_details.json`);

  return modelDetails;
}

module.exports =  {ModelSymptomDetails};


// ModelSymptomDetails("https://www.partselect.com/Models/DGBD2438PF5A/");