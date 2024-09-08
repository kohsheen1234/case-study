const neo4j = require('neo4j-driver');

// const driver = neo4j.driver(
//     'bolt://localhost:7687',
//     neo4j.auth.basic(process.env.NEO4J_USERNAME, process.env.NEO4J_PASSWORD)
// );

const driver = neo4j.driver(
    'bolt://localhost:7687', // Your Neo4j instance URL
    neo4j.auth.basic('neo4j', 'password') // Replace with your Neo4j username and password
  );

async function insertPartData(partData) {
    const session = driver.session();
    const tx = session.beginTransaction();
    try {
        // Insert the part node and manufacturer relationship in a transaction
        await tx.run(
            `MERGE (p:Part {partSelectNumber: $partSelectNumber})
             SET p.partName = $partName, 
                 p.manufacturerPartNumber = $manufacturerPartNumber, 
                 p.price = $price, 
                 p.rating = $rating, 
                 p.reviewCount = $reviewCount, 
                 p.description = $description`,
            {
                partSelectNumber: partData.partSelectNumber,
                partName: partData.partName,
                manufacturerPartNumber: partData.manufacturerPartNumber,
                price: partData.price,
                rating: partData.rating,
                reviewCount: partData.reviewCount,
                description: partData.description
            }
        );

        await tx.run(
            `MERGE (m:Manufacturer {name: $manufacturer})
             MERGE (p:Part {partSelectNumber: $partSelectNumber})
             MERGE (p)-[:MANUFACTURED_BY]->(m)`,
            {
                manufacturer: partData.manufacturer,
                partSelectNumber: partData.partSelectNumber,
            }
        );

        // Insert reviews and relationships
        for (const review of partData.reviewData) {
            await tx.run(
                `MATCH (p:Part {partSelectNumber: $partSelectNumber})
                 MERGE (r:Review {reviewerName: $reviewerName, date: $date})
                 SET r.rating = $rating, r.title = $title, r.reviewText = $reviewText
                 MERGE (p)-[:HAS_REVIEW]->(r)`,
                {
                    partSelectNumber: partData.partSelectNumber,
                    reviewerName: review.reviewerName,
                    date: review.date,
                    rating: review.rating,
                    title: review.title,
                    reviewText: review.reviewText
                }
            );
        }

        // Insert model compatibility data
        for (const model of partData.modelData) {
            await tx.run(
                `MATCH (p:Part {partSelectNumber: $partSelectNumber})
                 MERGE (m:Model {brand: $brand, modelNumber: $modelNumber})
                 SET m.description = $description
                 MERGE (p)-[:COMPATIBLE_WITH]->(m)`,
                {
                    partSelectNumber: partData.partSelectNumber,
                    brand: model.brand,
                    modelNumber: model.modelNumber,
                    description: model.description
                }
            );
        }

        // Insert customer repair stories
        for (const story of partData.repairStories) {
            await tx.run(
                `MATCH (p:Part {partSelectNumber: $partSelectNumber})
                 MERGE (s:RepairStory {title: $title, customer: $customer})
                 SET s.instruction = $instruction, 
                     s.difficulty = $difficulty, 
                     s.time = $time, 
                     s.helpfulness = $helpfulness
                 MERGE (p)-[:HAS_REPAIR_STORY]->(s)`,
                {
                    partSelectNumber: partData.partSelectNumber,
                    title: story.title,
                    customer: story.customer,
                    instruction: story.instruction,
                    difficulty: story.difficulty,
                    time: story.time,
                    helpfulness: story.helpfulness
                }
            );
        }

        // Insert Q&A data
        for (const qa of partData.qaData) {
            await tx.run(
                `MATCH (p:Part {partSelectNumber: $partSelectNumber})
                 MERGE (q:Question {question: $question, questionDate: $questionDate})
                 SET q.helpfulness = $helpfulness, q.modelNumber = $modelNumber
                 MERGE (a:Answer {answer: $answer})
                 MERGE (q)-[:HAS_ANSWER]->(a)
                 MERGE (p)-[:HAS_QUESTION]->(q)`,
                {
                    partSelectNumber: partData.partSelectNumber,
                    question: qa.question,
                    questionDate: qa.questionDate,
                    helpfulness: qa.helpfulness,
                    modelNumber: qa.modelNumber || '',
                    answer: qa.answer
                }
            );
        }

        // Commit the transaction after all operations
        await tx.commit();
    } catch (error) {
        console.error('Error inserting part data:', error);
        await tx.rollback(); // Rollback on error
    } finally {
        await session.close(); // Ensure the session is closed
    }
}


async function insertModelSymptomData(modelDetails) {
    const session = driver.session();
    const tx = session.beginTransaction();
    try {
        // Insert Model node
        await tx.run(
            `MERGE (m:Model {modelId: $modelId})`,
            {
                modelId: modelDetails.modelId,
            }
        );

        // Insert Symptoms and related Parts in a transaction
        for (const symptom of modelDetails.symptoms) {
            await tx.run(
                `MATCH (m:Model {modelId: $modelId})
                 MERGE (s:Symptom {name: $symptomName})
                 MERGE (m)-[:HAS_SYMPTOM]->(s)`,
                {
                    modelId: modelDetails.modelId,
                    symptomName: symptom.symptomName,
                }
            );

            for (const part of symptom.details) {
                await tx.run(
                    `MATCH (s:Symptom {name: $symptomName})
                     MERGE (p:Part {manufacturerPartNumber: $partNumber})
                     SET p.partName = $partName, 
                         p.fixPercentage = $fixPercentage, 
                         p.partPrice = $partPrice,
                         p.availability = $availability
                     MERGE (s)-[:FIXED_BY]->(p)`,
                    {
                        symptomName: symptom.symptomName,
                        manufacturerPartNumber: part.partNumber,
                        partName: part.partName,
                        fixPercentage: part.fixPercentage,
                        partPrice: part.partPrice,
                        availability: part.availability,
                    }
                );
            }
        }

        // Commit the transaction after all operations
        await tx.commit();
    } catch (error) {
        console.error('Error inserting model data:', error);
        await tx.rollback(); // Rollback on error
    } finally {
        await session.close(); // Ensure the session is closed
    }
}

async function insertModelData(modelDetails) {
    const session = driver.session();
    const tx = session.beginTransaction();
  
    try {
        // Check if modelNum exists in the scraped data
        if (!modelDetails.modelNum) {
          throw new Error("Model number (modelNum) is missing from modelDetails.");
        }
    
        // Insert the model node with the associated properties
        await tx.run(
          `MERGE (m:Model {modelNum: $modelNum})
           SET m.name = $name,
               m.brand = $brand,
               m.modelType = $modelType`,
          {
            modelNum: modelDetails.modelNum,
            name: modelDetails.name,
            brand: modelDetails.brand,
            modelType: modelDetails.modelType
          }
        );
      console.log(`Model ${modelDetails.modelNum} inserted or updated.`);
  
      // Insert sections and relate them to the model
      for (const section of modelDetails.sections) {
        await tx.run(
          `MERGE (s:Section {name: $sectionName})
           SET s.url = $sectionUrl
           MERGE (m:Model {modelNum: $modelNum})
           MERGE (m)-[:HAS_SECTION]->(s)`,
          {
            sectionName: section.name,
            sectionUrl: section.url,
            modelNum: modelDetails.modelNum
          }
        );
        console.log(`Section ${section.name} related to model ${modelDetails.modelNum}`);
      }
  
      // Insert manuals and relate them to the model
      for (const manual of modelDetails.manuals) {
        await tx.run(
          `MERGE (mn:Manual {name: $manualName})
           SET mn.url = $manualUrl
           MERGE (m:Model {modelNum: $modelNum})
           MERGE (m)-[:HAS_MANUAL]->(mn)`,
          {
            manualName: manual.name,
            manualUrl: manual.url,
            modelNum: modelDetails.modelNum
          }
        );
        console.log(`Manual ${manual.name} related to model ${modelDetails.modelNum}`);
      }
  
      // Insert parts and relate them to the model
      for (const part of modelDetails.parts) {
        await tx.run(
          `MERGE (p:Part {partId: $partId})
           SET p.name = $partName,
               p.price = $partPrice,
               p.status = $partStatus,
               p.url = $partUrl
           MERGE (m:Model {modelNum: $modelNum})
           MERGE (m)-[:COMPATIBLE_WITH]->(p)`,
          {
            partId: part.id,
            partName: part.name,
            partPrice: part.price,
            partStatus: part.status,
            partUrl: part.url,
            modelNum: modelDetails.modelNum
          }
        );
        console.log(`Part ${part.name} related to model ${modelDetails.modelNum}`);
      }
  
      // Commit the transaction after all operations
      await tx.commit();
      console.log(`Model details for ${modelDetails.modelNum} successfully inserted into Neo4j.`);
      
    } catch (error) {
      console.error('Error inserting model details:', error);
      await tx.rollback(); // Rollback on error
    } finally {
      await session.close(); // Ensure the session is closed
    }
  }

module.exports = { insertPartData, insertModelData, insertModelSymptomData };


