require('dotenv').config();
const { main } = require('./scrape/index');

main().catch(error => console.error('Error in main function:', error));
