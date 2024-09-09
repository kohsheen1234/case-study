const { scrapeDishwasherModels } = require('./modelScraper');
const { scrapeRefrigeratorModels } = require('./modelScraper');
const {scrapeModelDetails} = require('./modelDetailsScraper')


const { ModelSymptomDetails } = require('./modelSymptomDetails');
const {scrapeModelForInstructions} = require('./modelInstructionsScraper')

const { scrapePartsForModel, scrapePartSelect } = require('./partsScraper');
const { insertPartData,insertModelData,insertModelSymptomData,insertModelInstructionData } = require('../db/insertData');


async function main() {
    try {
        const dishwasherModels = await scrapeDishwasherModels();
        

        for (const model of dishwasherModels) {
           console.log(`Scraping details for model: ${model.name}`);
            
            // Pass the correct URL to scrapeModelDetails
            const dishwasherModel = await scrapeModelDetails(model.url);
            if(!dishwasherModel){
                continue;
            }
            await insertModelData(dishwasherModel);

            const dishwasherSymptomsModel = await ModelSymptomDetails(model.url);
            if(!dishwasherSymptomsModel){
                continue;
            }
            await insertModelSymptomData(dishwasherSymptomsModel);

            const dishwasherInstructionsModel = await scrapeModelForInstructions(`${model.url}Instructions`);
            if(!dishwasherInstructionsModel){
                continue;
            }
            await insertModelInstructionData(dishwasherInstructionsModel);

            // gets url of parts in model by going to https://www.partselect.com/Models/004621710A/Parts/
            const partUrls = await scrapePartsForModel(model.url);

            for (const partUrl of partUrls) {
                const partData = await scrapePartSelect(partUrl);
                if (!partData ) {
                    continue; // Skip to the next part URL
                }
                await insertPartData(partData);
                console.log(`Data for part ${partData.partSelectNumber} inserted successfully!`);
            }
        }


        const refrigeratorModels = await scrapeRefrigeratorModels();
        for (const model of refrigeratorModels) {
            console.log(`Scraping details for model: ${model.name}`);
            
            // Pass the correct URL to scrapeModelDetails
            const refrigeratorModel = await scrapeModelDetails(model.url);
            if (!refrigeratorModel ) {
                continue; 
            }
            await insertModelData(refrigeratorModel)

            const refrigeratorSymptomsModel = await ModelSymptomDetails(model.url);
            if(!refrigeratorSymptomsModel){
                continue;
            }
            await insertModelSymptomData(refrigeratorSymptomsModel);

            const refrigeratorInstructionsModel = await scrapeModelForInstructions(`${model.url}/Instructions`);
            if(!refrigeratorInstructionsModel){
                continue;
            }
            await insertModelInstructionData(refrigeratorInstructionsModel);
           

            const partUrls = await scrapePartsForModel(model.url);

            for (const partUrl of partUrls) {
                const partData = await scrapePartSelect(partUrl);
                if (!partData ) {
                    continue; // Skip to the next part URL
                }
                await insertPartData(partData);
                console.log(`Data for part ${partData.partSelectNumber} inserted successfully!`);
            }
        }

    } catch (error) {
        console.error('An error occurred during the scraping process:', error);
    } finally {
        console.log('Scraping process completed.');
    }
}

module.exports = { main };
