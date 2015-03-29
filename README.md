# ama-image
Reddit bot

Uploads an image to /r/books to be displayed in the AMA slot (left most image) in the banner.

1) Read the AMA schedule at wiki/ama-schedule and if an AMA is occuring today or tomorrow, upload the book image for that AMA.  
2) If no AMA is scheduled, read the data on wiki/ama-other and upload the next image in the list.  The index counter for the image is stored on wiki/bot-config.

3) Future - Read the data on wiki/author-birthdays and upload an image if there's an author birthday today.

This bot uses the external tool IMAGEMAGICK - http://www.imagemagick.org/

The bot is scheduled to run at 12:15am ET to ensure no conflicts with the CycleModRecs bot which runs at 12am.

Due to space constraints, /r/books uses url shorteners and this code requires a google api key to create the short urls using goo.gl

