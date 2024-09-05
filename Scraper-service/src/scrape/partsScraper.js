const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// https://www.partselect.com/Models/004621710A/Parts/
// https://www.partselect.com/Dishwasher-Models.htm



async function scrapePartsForModel(modelUrl) {
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();
    await page.goto(`${modelUrl}/Parts/`, { waitUntil: 'load', timeout: 0 });

    // Get the total number of pages
    const totalPages = await page.evaluate(() => {
        const paginationItems = Array.from(document.querySelectorAll('.pagination.js-pagination li'));
        const lastPageLink = paginationItems[paginationItems.length - 2].querySelector('a');
        return lastPageLink ? parseInt(lastPageLink.textContent) : 1;
    });

    let allPartUrls = [];

    // Loop through each page and collect part URLs
    for (let i = 1; i <= totalPages; i++) {
        if (i > 1) {
            await page.goto(`${modelUrl}/Parts/?start=${i}`, { waitUntil: 'load', timeout: 0 });
        }

        const partUrls = await page.evaluate(() => {
            return Array.from(document.querySelectorAll('.mega-m__part > a')).map(a => a.href);
        });

        allPartUrls = allPartUrls.concat(partUrls);
    }

    await browser.close();
    return allPartUrls;
}


async function scrapePartSelect(url) {
    // const url = 'https://www.partselect.com/PS17137081-GE-WD22X33499-LOWER-SPRAY-ARM.htm?SourceCode=18';
    // console.log(url)

    const psCodeMatch = url.match(/\/(PS\d+)-/);
   
    if (!psCodeMatch) {
        // console.error('No PS code found in the URL');
        return;
    }
    const psCode = psCodeMatch[1];
    // console.log('Extracted PS Code:', psCode);

    // Define the path to the JSON file
    const jsonFilePath = path.join("./src/scrape/Data/Parts/", `${psCode}.json`);
    console.log(jsonFilePath)

    // Check if the JSON file already exists
    if (fs.existsSync(jsonFilePath)) {
        console.log(`JSON file for ${psCode} already exists. Skipping...`);
        return null;
    }

    const browser = await puppeteer.launch({
        headless: true,
        defaultViewport: null,
        // executablePath: '/usr/bin/google-chrome',
        // args: ['--no-sandbox'],
     });
      
    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'load', timeout: 0 });

    const partData = await page.evaluate(() => {
        const getElementText = (selector, parent = document) => {
            const element = parent.querySelector(selector);
            return element ? element.innerText.trim() : null;
        };

        const getElementContent = (selector) => {
            const element = document.querySelector(selector);
            return element ? element.content.trim() : null;
        };

        // Extract part details
        const partSelectNumber = getElementText('span[itemprop="productID"]');
        const partName = getElementText('.title-lg');
        const manufacturerPartNumber = getElementText('span[itemprop="mpn"]');
        const manufacturer = getElementText('span[itemprop="brand"] span[itemprop="name"]');
        
        // Extract additional manufacturer information without 'for'
        const additionalManufacturers = getElementText('div.mb-2 span[itemprop="brand"] + span')
            ?.replace(/^for\s*/, '') // Remove the word 'for' at the beginning, if present
            .trim();

        const priceElement = document.querySelector('.price.pd__price .js-partPrice');
        const price = priceElement ? priceElement.innerText.trim() : null;

        // Extract numeric rating value and review count
        const rating = parseFloat(getElementContent('span[itemprop="aggregateRating"] meta[itemprop="ratingValue"]'));
        const reviewCount = getElementContent('span[itemprop="aggregateRating"] meta[itemprop="reviewCount"]');

        // Extract description
        const description = getElementText('.pd__description [itemprop="description"]');

        // Extract difficulty and time
        const difficulty = document.querySelectorAll('.pd__repair-rating .d-flex p.bold')[0]?.innerText.trim();
        const time = document.querySelectorAll('.pd__repair-rating .d-flex p.bold')[1]?.innerText.trim();

        // Extract troubleshooting information
        const symptoms = getElementText('.pd__wrap .col-md-6:nth-of-type(1)')?.replace('This part fixes the following symptoms:', '').trim();
        const products = getElementText('.pd__wrap .col-md-6:nth-of-type(2)')?.replace('This part works with the following products:', '').trim();
        const replaces = getElementText('.pd__wrap .col-md-6:nth-of-type(3) div[data-collapse-container]');

        // Extract reviews
        const reviewElements = document.querySelectorAll('.pd__cust-review__submitted-review');
        const reviewData = [];

        reviewElements.forEach(review => {
            const ratingElement = review.querySelector('.rating__stars__upper');
            const rating = ratingElement ? ratingElement.style.width : null; // Rating as width percentage
            const reviewerName = review.querySelector('.pd__cust-review__submitted-review__header span.bold')?.innerText.trim();
            const date = review.querySelector('.pd__cust-review__submitted-review__header')?.innerText.trim().split(' - ')[1];
            const title = review.querySelector('.bold:not(.pd__cust-review__submitted-review__header)')?.innerText.trim();
            const reviewText = review.querySelector('.js-searchKeys')?.innerText.trim();

            reviewData.push({
                reviewerName,
                date,
                rating,
                title,
                reviewText
            });
        });

        // Extract model compatibility information
        const modelElements = document.querySelectorAll('.pd__crossref__list .row');
        const modelData = [];

        modelElements.forEach(model => {
            const brand = getElementText('.col-6.col-md-3', model);
            const modelNumber = model.querySelector('a')?.innerText.trim();
            const description = model.querySelector('.col.col-md-6.col-lg-7')?.innerText.trim();

            modelData.push({
                brand,
                modelNumber,
                description
            });
        });

        // Extract customer repair stories
        const repairStoryElements = document.querySelectorAll('.repair-story');
        const repairStories = [];

        repairStoryElements.forEach(story => {
            const title = getElementText('.repair-story__title', story);
            const instruction = getElementText('.repair-story__instruction .js-searchKeys', story);
            const customer = getElementText('.repair-story__details .bold', story);
            
            // Correctly target difficulty and time
            const difficulty = story.querySelectorAll('.repair-story__details li')[1]?.innerText.replace('Difficulty Level:', '').trim();
            const time = story.querySelectorAll('.repair-story__details li')[2]?.innerText.replace('Total Repair Time:', '').trim();
            
            const helpfulness = getElementText('.js-displayRating', story);

            repairStories.push({
                title,
                instruction,
                customer,
                difficulty,
                time,
                helpfulness
            });
        });

        // Extract Q&A details
        const qaElements = document.querySelectorAll('.js-qnaResponse');
        const qaData = [];

        qaElements.forEach(qa => {
            const question = qa.querySelector('.js-searchKeys')?.innerText.trim();
            const answer = qa.querySelector('.qna__ps-answer__msg .js-searchKeys')?.innerText.trim();
            const modelNumber = qa.querySelector('.bold.mt-3.mb-3')?.innerText.trim();
            const questionDate = qa.querySelector('.qna__question__date')?.innerText.trim();
            const helpfulness = qa.querySelector('.js-displayRating')?.getAttribute('data-found-helpful');

            qaData.push({
                question,
                answer,
                modelNumber,
                questionDate,
                helpfulness
            });
        });


        return {
            partSelectNumber,
            partName,
            manufacturerPartNumber,
            manufacturer,
            additionalManufacturers, // Add this field
            price,
            rating,
            reviewCount,
            description,
            reviewData,
            difficulty,
            time,
            symptoms,
            products,
            replaces,
            modelData,
            repairStories,
            qaData
        };
    });

    await browser.close();

    // Save the scraped data to a JSON file named after the part number
    if (partData.partSelectNumber) {

        const dirPath = path.join(__dirname, 'src', 'scrape', 'Data', 'Parts');

        // Ensure the directory exists
        if (!fs.existsSync(dirPath)) {
            fs.mkdirSync(dirPath, { recursive: true });
        }

        // Define the full file path
        const filePath = path.join(dirPath, `${partData.partSelectNumber}.json`);

        // Save the file to the specified directory
        fs.writeFileSync(filePath, JSON.stringify(partData, null, 2));
        console.log(`Data scraped and saved successfully for part: ${partData.partSelectNumber}`);





        // fs.writeFileSync(`${partData.partSelectNumber}.json`, JSON.stringify(partData, null, 2));
        // console.log(`Data scraped and saved successfully for part: ${partData.partSelectNumber}`);
    } else {
        console.log('Failed to retrieve part number, data not saved.');
    }

    return partData;
}

// scrapePartSelect("https://www.partselect.com/PS11750673-Whirlpool-WPW10225581-Bi-Metal-Defrost-Thermostat.htm?SourceCode=21&SearchTerm=10641122212&ModelNum=10641122212");
module.exports = { scrapePartsForModel, scrapePartSelect };
