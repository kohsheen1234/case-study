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

  
  async function getQASection() {
    const qnaDetails = [];
    try {
      console.log("Waiting for Q&A section to load...");
      // Wait for the Q&A section to load
      await page.waitForSelector(".qna__question .js-qnaResponse", { timeout: 10000 });
      console.log("Q&A section loaded successfully!");

      // Extract questions and answers
      const questions = await page.evaluate(() => {
        console.log("Extracting Q&A details from the page...");

        // Query all the Q&A responses
        return Array.from(
          document.querySelectorAll(".qna__question.js-qnaResponse")
        ).map((qna) => {
          const authorName =
            qna.querySelector(".title-md.bold")?.innerText.trim() ||
            "No author available";
          const questionDate =
            qna.querySelector(".qna__question__date")?.innerText.trim() ||
            "No date available";
          const questionText =
            qna.querySelector(".js-searchKeys")?.innerText.trim() ||
            "No question text available";
          const answerText =
            qna
              .querySelector(".qna__ps-answer__msg .js-searchKeys")
              ?.innerText.trim() || "No answer text available";
          const helpfulVotes =
            qna
              .querySelector(".js-displayRating")
              ?.getAttribute("data-found-helpful") || "0";

          console.log(`Processing Q&A for author: ${authorName}`);
          console.log(`Question: ${questionText}`);
          console.log(`Answer: ${answerText}`);
          console.log(`Helpful Votes: ${helpfulVotes}`);

          // Extract related parts if they exist
          const relatedParts = Array.from(
            qna.querySelectorAll(".qna__question__related")
          ).map((part) => {
            const partName =
              part.querySelector("a")?.innerText.trim() ||
              "No part name available";
            const partPrice =
              part.querySelector(".price")?.innerText.trim() ||
              "No price available";
            const partAvailability =
              part.querySelector(".js-tooltip")?.innerText.trim() ||
              "No availability info";

            console.log(
              `Related Part: ${partName}, Price: ${partPrice}, Availability: ${partAvailability}`
            );
            return { partName, partPrice, partAvailability };
          });

          return {
            authorName,
            questionDate,
            questionText,
            answerText,
            helpfulVotes,
            relatedParts,
          };
        });
      });

      console.log("Q&A details successfully extracted:", questions);
      qnaDetails.push(...questions);
    } catch (error) {
      console.error("Error scraping Q&A section:", error);
    }

    return qnaDetails;
  }

  async function getInstallationInstruction() {
    const instructionDetails = [];

    try {
      await page.waitForSelector(".repair-story", { timeout: 15000 });
      console.log("Installation instruction section loaded successfully!");

      const instructions = await page.evaluate(() => {
        const repairStories = document.querySelectorAll(".repair-story");
        return Array.from(repairStories).map((story) => {
          const title =
            story.querySelector(".repair-story__title")?.innerText.trim() ||
            "No title available";
          const link =
            story.querySelector(".repair-story__title")?.href ||
            "No link available";
          const instructionContent =
            story
              .querySelector(".repair-story__instruction__content")
              ?.innerText.trim() || "No instruction content available";

          const parts = Array.from(
            story.querySelectorAll(".repair-story__parts a")
          ).map((part) => ({
            partName: part.innerText.trim(),
            partUrl: part.href,
          }));

          const author =
            story
              .querySelector(".repair-story__details .bold")
              ?.innerText.trim() || "No author available";
          const difficulty =
            story
              .querySelector(
                ".repair-story__details li:nth-child(2) .bold + div"
              )
              ?.innerText.trim() || "No difficulty available";
          const repairTime =
            story
              .querySelector(
                ".repair-story__details li:nth-child(3) .bold + div"
              )
              ?.innerText.trim() || "No repair time available";
          const tools =
            story
              .querySelector(
                ".repair-story__details li:nth-child(4) .bold + div"
              )
              ?.innerText.trim() || "No tools available";
          const helpfulVotes =
            story.querySelector(".js-displayRating span")?.innerText.trim() ||
            "No vote data available";

          return {
            title,
            link,
            instructionContent,
            parts,
            author,
            difficulty,
            repairTime,
            tools,
            helpfulVotes,
          };
        });
      });

      console.log(
        "Installation instructions successfully extracted:",
        instructions
      );
      instructionDetails.push(...instructions);
    } catch (error) {
      console.error("Error scraping installation instructions:", error);
    }

    return instructionDetails;
  }

  async function getYouTubeVideos() {
    const videoDetails = [];
    try {
      const videoSectionExists = await page.$("#Videos");
      if (!videoSectionExists) {
        console.log("No YouTube video section found on this page.");
        return videoDetails;
      }
  
      console.log("YouTube video section found. Extracting video details...");
  
      // Check if there are videos to scrape
      const videoCount = await page.$eval(
        ".section-title__count a",
        (el) => el.innerText.match(/\d+/)[0] // Extract number of videos
      );
      
      if (parseInt(videoCount) > 0) {
        // Wait for the YouTube videos section to load
        await page.waitForSelector(".mega-m__videos .col-12.col-lg-6", { timeout: 10000 });
  
        // Extract video details
        const videos = await page.evaluate(() => {
          return Array.from(document.querySelectorAll(".mega-m__videos .col-12.col-lg-6")).map((video) => {
            const videoId =
              video.querySelector(".yt-video")?.getAttribute("data-yt-init") || "No video ID";
            const videoThumb =
              video.querySelector(".yt-video__thumb")?.getAttribute("data-src") || "No thumbnail available";
            const videoTitle =
              video.querySelector("h3 a")?.innerText.trim() || "No title available";
            const videoLink =
              video.querySelector("h3 a")?.href || "No link available";
  
            return {
              videoId,
              videoThumb,
              videoTitle,
              videoLink,
            };
          });
        });
  
        console.log("YouTube video details successfully extracted:", videos);
        videoDetails.push(...videos);
      } else {
        console.log("No YouTube videos available for this model.");
      }
    } catch (error) {
      console.error("Error scraping YouTube videos section:", error);
    }
  
    return videoDetails;
  }

  async function getYouTubeVideos() {
    const videoDetails = [];
    try {
      console.log("Waiting for YouTube videos section to load...");
      // Wait for the YouTube videos section to load
      await page.waitForSelector(".mega-m__videos", { timeout: 10000 });
      console.log("YouTube videos section loaded successfully!");

      // Extract video details
      const videos = await page.evaluate(() => {
        console.log("Extracting YouTube video details from the page...");

        // Query all the YouTube video elements
        return Array.from(
          document.querySelectorAll(".mega-m__videos .col-12.col-lg-6")
        ).map((video) => {
          const videoId =
            video.querySelector(".yt-video").getAttribute("data-yt-init") ||
            "No video ID";
          const videoThumb =
            video.querySelector(".yt-video__thumb").getAttribute("data-src") ||
            "No thumbnail available";
          const videoTitle =
            video.querySelector("h3 a")?.innerText.trim() ||
            "No title available";
          const videoLink =
            video.querySelector("h3 a")?.href || "No link available";

          console.log(`Processing video: ${videoTitle}`);
          console.log(`Video ID: ${videoId}`);
          console.log(`Thumbnail: ${videoThumb}`);

          return {
            videoId,
            videoThumb,
            videoTitle,
            videoLink,
          };
        });
      });

      console.log("YouTube video details successfully extracted:", videos);
      videoDetails.push(...videos);
    } catch (error) {
      console.error("Error scraping YouTube videos section:", error);
    }

    return videoDetails;
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
    QnA: await getQASection(),
    installationInstruction: await getInstallationInstruction(),
    youtubeVideos: await getYouTubeVideos(),
  };

  const jsonFilePath = path.join(__dirname, 'Data', 'Models', `${modelDetails.modelNum}.json`);
  fs.writeFileSync(jsonFilePath, JSON.stringify(modelDetails, null, 4));
  console.log(`Saved model details to ${jsonFilePath}`);

  await browser.close();
}


module.exports = { scrapeModelDetails };


// Example usage:
// scrapeModelDetails("https://www.partselect.com/Models/FGHD2465NF1A/");
