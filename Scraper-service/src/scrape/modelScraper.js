const puppeteer = require('puppeteer');

async function scrapeDishwasherModels() {
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();
    const modelsUrl = 'https://www.partselect.com/Dishwasher-Models.htm';
    await page.goto(modelsUrl, { waitUntil: 'load', timeout: 0 });

    const models = await page.evaluate(() => {
        return Array.from(document.querySelectorAll('ul.nf__links > li > a')).map(a => ({
            name: a.textContent.trim(),
            url: a.href
        }));
    });

    await browser.close();
    return models;
}

async function scrapeRefrigeratorModels() {
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();
    const modelsUrl = 'https://www.partselect.com/Refrigerator-Models.htm';
    await page.goto(modelsUrl, { waitUntil: 'load', timeout: 0 });

    const models = await page.evaluate(() => {
        return Array.from(document.querySelectorAll('ul.nf__links > li > a')).map(a => ({
            name: a.textContent.trim(),
            url: a.href
        }));
    });

    await browser.close();
    return models;
}
module.exports = { scrapeDishwasherModels, scrapeRefrigeratorModels };
