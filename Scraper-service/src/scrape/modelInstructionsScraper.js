const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// URL to scrape
// const url = 'https://www.partselect.com/Models/004621710A/Instructions/';

// Function to scrape instructions data
async function scrapeModelForInstructions(modelUrl) {
    console.log("reacher ")
    console.log(modelUrl)
    const modelNumber = modelUrl.match(/Models\/([^/]+)\//)[1]; // This will extract '004621710A'
    console.log(modelNumber);
    

    // Define the path to the JSON file
    const jsonFilePath_ = path.join("./src/scrape/Data/Models/", `${modelNumber}_instructions.json`);
    console.log(jsonFilePath_);

    // Check if the JSON file already exists
    if (fs.existsSync(jsonFilePath_)) {
        console.log(`JSON file for ${modelNumber} already exists. Skipping...`);
        return null;
    }

    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();

    await page.goto(modelUrl, { waitUntil: 'networkidle2' });

    // Pass the modelNumber into page.evaluate
    const instructionsData = await page.evaluate((modelNumber) => {
        const instructions = [];
        const instructionElements = document.querySelectorAll('.repair-story');

        instructionElements.forEach(instructionEl => {
            const titleElement = instructionEl.querySelector('.repair-story__title');
            const descriptionElement = instructionEl.querySelector('.repair-story__instruction__content');
            const partsElements = instructionEl.querySelectorAll('.repair-story__parts a');
            const userElement = instructionEl.querySelector('.repair-story__details svg + div .bold');
            const difficultyElement = instructionEl.querySelector('.repair-story__details .bold + div');
            const repairTimeElement = instructionEl.querySelector('.repair-story__details svg + div + div .bold + div');
            const helpfulVotesElement = instructionEl.querySelector('.js-displayRating span:first-child');

            const title = titleElement ? titleElement.innerText : 'No title';
            const description = descriptionElement ? descriptionElement.innerText : 'No description';
            const partsUsed = Array.from(partsElements).map(el => ({
                partName: el.querySelector('span') ? el.querySelector('span').innerText : 'No part name',
                partUrl: el.href
            }));
            const difficulty = difficultyElement ? difficultyElement.innerText : 'No difficulty info';
            const repairTime = repairTimeElement ? repairTimeElement.innerText : 'No repair time info';
            const helpfulVotes = helpfulVotesElement ? helpfulVotesElement.innerText : 'No helpful votes';

            instructions.push({
                modelNumber,
                title,
                description,
                partsUsed,  
                difficulty,
                repairTime,
                helpfulVotes
            });
        });

        return instructions;
    }, modelNumber); // Pass modelNumber here

    console.log(instructionsData);

    const dirPath = path.join(__dirname, 'Data', 'Models'); 

    // Save data to JSON file
    const jsonFilePath = path.join(dirPath,`${modelNumber}_instructions.json`);
    fs.writeFileSync(jsonFilePath, JSON.stringify(instructionsData, null, 4));
    console.log(`Saved model details to ${jsonFilePath}`);

    await browser.close();

    return instructionsData;
}

module.exports = { scrapeModelForInstructions };

// Calling the scraper function
// scrapeModelForInstructions(url);
