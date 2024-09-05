const puppeteer = require('puppeteer');
const fs = require('fs');

class ModelDetailsScraper {
    constructor() {
        this.partLinks = new Set();
    }

    async scrapeModelDetails(url) {
        const browser = await puppeteer.launch({ headless: true });
        const page = await browser.newPage();

        try {
            await page.goto(url, { waitUntil: 'load', timeout: 0 });

            const modelDetails = {
                url: url,
                name: await this._getName(page),
                brand: await this._getBrand(page),
                modelNum: await this._getModelNum(page),
                modelType: await this._getModelType(page),
                sections: await this._getSectionsPDFLinks(page),
                manuals: await this._getManualsLinks(page),
                parts: await this._getParts(page, url),
                qnas: await this._extractQnaDetails(page),
                videos: await this._getVideoLinks(page, url),
                installationInstructions: await this._getInstallationInstructions(page, url),
                commonSymptoms: await this._getCommonSymptoms(page)
            };

            // Generate model ID from the URL
            const modelId = url.split('/').filter(Boolean).pop().replace(/\s+/g, '_');
            fs.writeFileSync(`${modelId}_model_details.json`, JSON.stringify(modelDetails, null, 2));
            console.log(`Model details saved as ${modelId}_model_details.json`);

            return modelDetails;
        } catch (error) {
            console.error(`Error scraping model details: ${error}`);
        } finally {
            await browser.close();
        }
    }

    async _getName(page) {
        return page.evaluate(() => document.querySelector('#main')?.getAttribute('data-description') || 'Unknown Name');
    }

    async _getBrand(page) {
        return page.evaluate(() => document.querySelector('#main')?.getAttribute('data-brand') || 'Unknown Brand');
    }

    async _getModelNum(page) {
        return page.evaluate(() => document.querySelector('#main')?.getAttribute('data-model-num') || 'Unknown Model Number');
    }

    async _getModelType(page) {
        return page.evaluate(() => document.querySelector('#main')?.getAttribute('data-modeltype') || 'Unknown Model Type');
    }

    async _sectionExists(page, sectionName) {
        try {
            const sectionLink = await page.evaluate(sectionName => {
                const navSection = document.querySelector('.mega-m__nav');
                if (!navSection) return false;

                const link = navSection.querySelector(`a[data-page-name='${sectionName}']`);
                return link !== null;
            }, sectionName);

            return sectionLink;
        } catch (error) {
            console.error(`Error checking section '${sectionName}': ${error}`);
            return false;
        }
    }

    async _getSectionsPDFLinks(page) {
        const sectionExists = await this._sectionExists(page, "Sections");
        if (!sectionExists) return [];

        return page.evaluate(() => {
            const sections = [];
            const sectionElements = document.querySelectorAll('.row.mb-3 .col-6');
            sectionElements.forEach(section => {
                const linkElement = section.querySelector('a');
                const sectionName = linkElement?.querySelector('span')?.innerText.trim() || 'Unknown Section';
                const sectionLink = linkElement?.getAttribute('href') || '#';
                sections.push({ name: sectionName, url: sectionLink });
            });
            return sections;
        });
    }

    async _getManualsLinks(page) {
        const sectionExists = await this._sectionExists(page, "Manuals");
        if (!sectionExists) return [];

        return page.evaluate(() => {
            const manuals = [];
            const manualLinks = document.querySelectorAll('.d-flex.flex-wrap.mt-2.mb-4 a.mega-m__manuals');

            manualLinks.forEach(manual => {
                const manualTitleElement = manual.querySelector('.mega-m__manuals__title');
                const manualName = manualTitleElement ? manualTitleElement.innerText.trim() : 'Untitled Manual';
                const manualUrl = manual.getAttribute('href') || '#';
                manuals.push({ name: manualName, url: manualUrl });
            });

            return manuals;
        });
    }

    async _getParts(page, url) {
        const sectionExists = await this._sectionExists(page, "Parts");
        if (!sectionExists) return [];

        const partsUrl = `${url}/Parts`;
        await page.goto(partsUrl, { waitUntil: 'load', timeout: 0 });

        return page.evaluate(() => {
            const parts = [];
            const partElements = document.querySelectorAll('.mega-m__part');

            partElements.forEach(part => {
                const partNameElement = part.querySelector('.mega-m__part__name');
                const partName = partNameElement ? partNameElement.innerText.trim() : 'Unknown Part';

                const partLinkElement = part.querySelector('a');
                const partLink = partLinkElement ? partLinkElement.getAttribute('href').split('?')[0] : '#';
                const partId = partLink ? partLink.split('/').pop().split('.')[0] : 'Unknown ID';

                const partPriceElement = part.querySelector('.mega-m__part__price');
                const partPrice = partPriceElement ? partPriceElement.innerText.trim() : 'No longer available';

                const partStatusElement = part.querySelector('.js-tooltip');
                const partStatus = partStatusElement ? partStatusElement.innerText.trim() : 'No longer available';

                if (partName && partId && partLink) {
                    parts.push({
                        name: partName,
                        id: partId,
                        url: partLink,
                        price: partPrice,
                        status: partStatus
                    });
                }
            });

            return parts;
        });
    }

    async _extractQnaDetails(page) {
        const sectionExists = await this._sectionExists(page, "Questions & Answers");
        if (!sectionExists) return [];

        return page.evaluate(() => {
            const qnas = [];
            const questionElements = document.querySelectorAll('.qna__question');
            questionElements.forEach(question => {
                const questionDate = question.querySelector('.qna__question__date')?.innerText.trim() || 'Unknown Date';
                const questionText = question.querySelector('.js-searchKeys')?.innerText.trim() || 'Unknown Question';
                const answerText = question.querySelector('.qna__ps-answer__msg')?.innerText.trim() || 'No Answer Provided';

                const relatedParts = [];
                const relatedPartsElements = question.querySelectorAll('.qna__question__related');
                relatedPartsElements.forEach(part => {
                    const partName = part.querySelector('.bold')?.innerText.trim() || 'Unknown Part';
                    const partLink = part.querySelector('a')?.getAttribute('href').split('?')[0] || '#';
                    const partId = partLink.split('/').pop().split('.')[0];
                    const partPrice = part.querySelector('.price')?.innerText.trim() || 'No longer available';
                    const partStatus = part.querySelector('.js-tooltip')?.innerText.trim() || 'No longer available';
                    relatedParts.push({
                        name: partName,
                        id: partId,
                        url: partLink,
                        price: partPrice,
                        status: partStatus
                    });
                });

                qnas.push({ date: questionDate, question: questionText, answer: answerText, related_parts: relatedParts });
            });
            return qnas;
        });
    }


    
    

    async _getVideoLinks(page, url) {
        const sectionExists = await this._sectionExists(page, "Videos");
        if (!sectionExists) return [];

        const videosUrl = `${url}/Videos`;
        await page.goto(videosUrl, { waitUntil: 'load', timeout: 0 });

        return page.evaluate(() => {
            const videoDetails = [];
            const videoElements = document.querySelectorAll('.yt-video');

            videoElements.forEach(video => {
                const ytVideoId = video.getAttribute('data-yt-init') || '';
                const youtubeLink = `https://www.youtube.com/watch?v=${ytVideoId}`;
                const videoTitle = video.querySelector('.mb-3.video__title')?.innerText.trim() || 'Untitled Video';

                const parts = [];
                const partElements = video.closest('.mega-m__part.mb-5');

                partElements?.forEach(part => {
                    const partName = part.querySelector('.mega-m__part__name')?.innerText.trim() || 'Unknown Part';
                    const partLink = part.querySelector('a')?.getAttribute('href').split('?')[0] || '#';
                    const partId = partLink.split('/').pop().split('.')[0];
                    const partPrice = part.querySelector('.mega-m__part__price')?.innerText.trim() || 'No longer available';
                    const partStatus = part.querySelector('.js-tooltip')?.innerText.trim() || 'No longer available';
                    parts.push({
                        name: partName,
                        id: partId,
                        url: partLink,
                        price: partPrice,
                        status: partStatus
                    });
                });

                videoDetails.push({ url: youtubeLink, name: videoTitle, parts });
            });

            return videoDetails;
        });
    }

    async _getInstallationInstructions(page, url) {
        const sectionExists = await this._sectionExists(page, "Instructions");
        if (!sectionExists) return [];

        const instructionsUrl = `${url}/Instructions`;
        await page.goto(instructionsUrl, { waitUntil: 'load', timeout: 0 });

        return page.evaluate(() => {
            const instructionDetails = [];
            const instructionElements = document.querySelectorAll('.repair-story');

            instructionElements.forEach(instruction => {
                const instructionTitle = instruction.querySelector('.repair-story__title')?.innerText.trim() || 'Untitled Instruction';
                const instructionContent = instruction.querySelector('.repair-story__instruction__content')?.innerText.trim() || 'No Content Available';

                const parts = [];
                const partsElements = instruction.querySelectorAll('.repair-story__parts a');
                partsElements.forEach(part => {
                    const partName = part.querySelector('span')?.innerText.trim() || 'Unknown Part';
                    const partLink = part.getAttribute('href')?.split('?')[0] || '#';
                    const partId = partLink.split('/').pop().split('.')[0];
                    parts.push({
                        name: partName,
                        id: partId,
                        url: partLink
                    });
                });

                const details = instruction.querySelectorAll('.repair-story__details li');
                let difficulty = "";
                let repairTime = "";
                let tools = "";

                details.forEach(detail => {
                    const detailText = detail.innerText.trim();
                    if (detailText.includes("Difficulty Level:")) {
                        difficulty = detailText.split("Difficulty Level:")[1].trim();
                    } else if (detailText.includes("Total Repair Time:")) {
                        repairTime = detailText.split("Total Repair Time:")[1].trim();
                    } else if (detailText.includes("Tools:")) {
                        tools = detailText.split("Tools:")[1].trim();
                    }
                });

                instructionDetails.push({
                    title: instructionTitle,
                    content: instructionContent,
                    partsUsed: parts,
                    difficulty,
                    repairTime,
                    tools
                });
            });

            return instructionDetails;
        });
    }
}

// Example usage of the function with a specific model URL
(async () => {
    const scraper = new ModelDetailsScraper();
    await scraper.scrapeModelDetails('https://www.partselect.com/Models/004621710A/');
})();
