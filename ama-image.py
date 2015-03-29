#!/usr/bin/python
import sys
import praw
import requests
import re
import time
import datetime
import platform
import os.path
import random
import redditutils
from subprocess import check_output

USERNAME            = ""
PASSWORD            = ""
SUBREDDIT           = ""
IMAGENAME           = "CurrentModRec.png"

logBuf = ""
logTimeStamp = ""

def DEBUG(s, start=False, stop=False):

    global logBuf
    global logTimeStamp

    print (s)

    logBuf = logBuf + s + "\n\n"
    if stop:
        #r.submit("bookbotlog", logTimeStamp, text=logBuf)
        logBuf = ""



def readMainSched ():
    DEBUG("readMainSched() Entered")
    sr = r.get_subreddit(SUBREDDIT)
    wp = sr.get_wiki_page("ama-schedule")

    es = "####\[\]\(#AMA END"
    ss = "####\[\]\(#AMA START---DO NOT REMOVE OR EDIT THIS LINE\)\r\n"
    m = re.search(ss+"(.*)"+es, wp.content_md, re.DOTALL)

    mainSched = m.group(1).split("\n")
    mainSched = [x.strip() for x in mainSched]

    while not mainSched[-1]: del mainSched[-1]

    todayInSecs = redditutils.dateToSecs(datetime.date.today().strftime("%Y-%m-%d"))

    tmpList = []
    tmpList.append(mainSched[0])
    tmpList.append(mainSched[1])
    for i in range(2, len(mainSched)):
        secs = redditutils.dateToSecs(mainSched[i].split("|")[0])
        if secs >= todayInSecs:
            tmpList.append(mainSched[i])

    mainSched = tmpList

    print ("-----MAIN SCHEDULE----")
    print (mainSched)
    print ("-----MAIN SCHEDULE----\n")

    return mainSched




def decodeBook(str):
    """ Takes a string and decodes the book format fields and returns a dict. """
    book = {"banner":"", "author":"", "imageurl": "", "blurb": "", "title":""}

    formatstrs = ['banner', 'author', 'imageurl', 'blurb', 'title']

    # requirements: if #1, the code will search for author, title and find the image and blurb
    #               if #2, the code will use the provided info
    # 1) banner, author, title
    # 2) banner, imageurl, blurb

    bookarray = str.splitlines()

    # '{book}' was stripped out in .split({book}), it's always the 1st line
    book['title'] = bookarray[0]
    if len(book['title']) == 0 or len(book['title']) > 150:
        DEBUG("decodeBook: decode error - title too long or too short" + book['title'])
    else:
        for x in bookarray:
            for s in formatstrs:
                searchstr = "{%s}(.*)" % s
                m = re.search(searchstr, x, re.I)
                if m:
                    book[s] = m.group(1).strip()
                    break

    # 1) must have banner...
    if book['banner']:
        # and either 2) author
        if not book['author']:
            #print("decodeBook: No Author (%s)" % book['title'])
            # or 3) image and blurb
            if (not book['imageurl'] or not book['blurb']):
                print("decodeBook: No imageurl/blurb(%s)" % book['title'])
                print (book)
                book = {}


    else:
        print("decodeBook: No Banner (%s)" % book['title'])
        book = {}

    return book


def updateBookImageName (sr, imagefile):
    """ update the stylesheet with the image file name.
        even if the imagename is already what we want, we still
        call set_stylesheet() because reddit requires that when
        uploading an image with the same name.
     """


    sheet = sr.get_stylesheet()['stylesheet']
    newsheet = sheet
    sr.set_stylesheet(newsheet)
    return



def updateBlurb(sr, blurb, banner):
    """ update the book blurb on the sidebar page """

    if not blurb:
        blurb = ' '

    if not banner:
        banner = ''

    DEBUG("updateBlurb: blurb (%s)" % blurb)
    DEBUG("updateBlurb: banner (%s)" % banner)

    sb = sr.get_settings()["description"]

    srchstr = "###### \[\]\(#place announcements below\)\n\n(.*)\n"
    m = re.search(srchstr, sb)

    if not m:
        DEBUG("updateBlurb: Error finding (%s) in sidebar" % srchstr, stop=True)
        quit()

    if len(m.group(1)) < 2 and len(banner) < 2:
        DEBUG("updateBlurb: No banner in old or new.  Not updating.");
    else:
        banner = '* ' + banner
        newsb = sb.replace(m.group(1), banner)


        # update blurb (click-thru link)
        srchstr = "(##### \[ama\].*)\n"
        m = re.search(srchstr, newsb)

        if not m:
            DEBUG("updateBlurb: Error finding (%s) in sidebar" % srchstr)
        elif len(m.group(1)) < 2 or len(banner) < 5:
            DEBUG("updateBlurb: No blurb in old or new.  Not updating.");
        else:
            newblurb = "##### [ama](" + blurb + ")"
            newsb = newsb.replace(m.group(1), newblurb)

        e = sr.update_settings(description = newsb)
        if e['errors']:
            DEBUG("updateBlurb: error from update_settings() (%s) " % e['errors'], stop=True)
            quit()



def downloadImage(imageUrl, localFileName):

    DEBUG("downloadImage: Looking for %s" % imageUrl)
    IDENTIFY = 'identify'
    CONVERT = 'convert'

    if platform.system() == 'Windows':
        IDENTIFY = 'C:/Program Files/ImageMagick-6.8.9-Q16/identify.exe'
        CONVERT = 'C:/Program Files/ImageMagick-6.8.9-Q16/convert.exe'


    ext = os.path.splitext(imageUrl)[1][1:].strip()
    if not ext and "imgur" in imageUrl:
        imageUrl = imageUrl + ".png"

    response = requests.get(imageUrl)

    if response.status_code == 200:
        print('Downloading %s...' % (localFileName))

        with open(localFileName, 'wb') as fo:
            for chunk in response.iter_content(4096):
                fo.write(chunk)

        response.connection.close()
        try:
            output = check_output([IDENTIFY, localFileName])
            a = output.split()
            DEBUG("downloadImage: image is (%s) (%s)" % (a[1].decode("utf-8"), a[2].decode("utf-8")))
            if a[2] != b"103x160":
                o = check_output([CONVERT,  localFileName, "-resize", "103x160!", localFileName])
                DEBUG("(%s) image converted to 103x160" % imageUrl)
            elif a[1] != b"PNG":
                o = check_output(["convert",  localFileName, localFileName])
                DEBUG("(%s) image converted to PNG" % imageUrl)
        except Exception as e:
            DEBUG('downloadImage: Error in IDENTIFY or CONVERT %s' % e)
            return False

        return True
    else:
        DEBUG("downloadImage: Error(%s) finding (%s)" % (response.status_code, imageUrl))
        response.connection.close()
        return False


#################################################

def uploadImage (sr, filename):
    """   """

    DEBUG("uploadImage: (%s)" % filename)
    sr.upload_image(filename)

    return
##############################################################################


def checkForAMA (r):

    sched = readMainSched()

    todayInSecs = redditutils.dateToSecs(datetime.date.today().strftime("%Y-%m-%d"))
    tomorrowInSecs = redditutils.dateToSecs((datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))

    found = False

    for i in range(2, len(sched)):
        secs = redditutils.dateToSecs(sched[i].split("|")[0])
        if todayInSecs == secs:
            # there's an ama today
            found = True
            break
        elif tomorrowInSecs == secs:
            found = True
            break


    if not found:
        DEBUG("checkForAMA: Found nothing")
        return False

    ama = sched[i].split("|")

    # 0 - date
    # 1 - time
    # 2 - author
    # 3 - title
    # 4 - image
    # 5 - title1
    # 6 - title2
    # 7 - twitter

    # need author, title, image, twitter

    authorName, authorUrl = redditutils.extractMarkDownLink(ama[2])
    titleName, titleUrl = redditutils.extractMarkDownLink(ama[3])
    imageName, imageUrl = redditutils.extractMarkDownLink(ama[4])
    authorName = authorName.replace("*", "")
    titleName = titleName.replace("*", "")

    y,m,d = ama[0].split("-")
    weekday = datetime.date(int(y), int(m), int(d)).strftime("%a")
    banner = "%s at %s, %s author of %s" % (weekday, ama[1], ama[2], ama[3])

    print (banner)

    DEBUG("checkForAMA: Doing this: (%s) (%s)" % (authorName, titleName))

    ok = downloadImage(imageUrl, IMAGENAME)
    if not ok:
        # image url is no good, abort
        DEBUG()
        return False


    sr = r.get_subreddit(SUBREDDIT)

    #
    # upload the image to the stylesheet page
    #
    uploadImage(sr, IMAGENAME)

    #
    # update stylesheet with imagefile name
    #
    updateBookImageName(sr, IMAGENAME)

    #
    # update blurb in sidebar
    #
    updateBlurb(sr, titleUrl, banner)

    return True



###############################################################################
def cycleBooks (r):

    nextBook = 0
    #
    # get the "ama-other" wiki page
    #
    sr = r.get_subreddit(SUBREDDIT)
    mrp = sr.get_wiki_page("ama-other")


    botConfig = redditutils.getBotConfig(r, SUBREDDIT)
    nextBook = botConfig["AmaOtherIndex"]

    DEBUG("cycleBooks: next book index = %d" % nextBook)

    #
    # get the list of mod rec books
    #
    mrps = mrp.content_md.split("{title}")
    bookList = []
    for i in mrps:
        i = i.strip()

        if len(i) < 10:
            continue

        myBook = decodeBook(i)
        if myBook:
            bookList.append(myBook)


    numBooks = len(bookList)
    DEBUG("found %s books" % numBooks)
    if len(bookList) < 2:
        DEBUG("Not enough books", stop=True)
        quit()

    # if we're at the end, start over from top
    if nextBook >= numBooks:
        nextBook = 0;

    DEBUG("\nfound current book **%s** at index:%s out of %s" % (bookList[nextBook]['title'], nextBook, numBooks))

    #
    # verify image file URL is valid
    #
    count = len(bookList)
    ok = False
    while not ok and count > 0:

        if not bookList[nextBook]['imageurl']:
            # search goodreads for 'blurb' and image
            bookList[nextBook]['blurb'] = redditutils.searchGoodreadsWithGoogle(bookList[nextBook]['title'],
                                                                                bookList[nextBook]['author'])
            if not bookList[nextBook]['blurb']:
                print ("Cant find blurb for (%s)(%s)" % (bookList[nextBook]['title'], bookList[nextBook]['author']))
            else:
                dummy, bookList[nextBook]['imageurl'] = redditutils.getBookImage(bookList[nextBook]['blurb'])
                if not bookList[nextBook]['imageurl']:
                    print ("Cant find imageurl for (%s)" % (bookList[nextBook]['blurb']))
                else:
                    bookList[nextBook]['blurb'] = redditutils.shortener(bookList[nextBook]['blurb'], GOOGLEAPIKEY, USERIP)

        if bookList[nextBook]['imageurl']:
            ok = downloadImage(bookList[nextBook]['imageurl'], IMAGENAME)
        if not ok:
            nextBook += 1
            count -= 1

    if count == 0:
        DEBUG("ERROR: CANNOT FIND A SINGLE BOOK IMAGE", stop=True)
        quit

    #
    # upload the image to the stylesheet page
    #
    uploadImage(sr, IMAGENAME)

    #
    # update stylesheet with imagefile name
    #
    updateBookImageName(sr, IMAGENAME)

    #
    # update blurb in sidebar
    #
    updateBlurb(sr, bookList[nextBook]['blurb'], bookList[nextBook]['banner'])


    #
    # save the current book index
    #
    botConfig["AmaOtherIndex"] = nextBook+1
    redditutils.saveBotConfig (r, SUBREDDIT, botConfig)
#########################################################################


if __name__=='__main__':
    #
    # init and log into reddit
    #

    f = open('ama-image.conf', 'r')
    buf = f.readlines()
    f.close()

    for b in buf:
        if b[0] == '#' or len(b) < 5:
            continue

        if b.startswith('username:'):
            USERNAME = b[len('username:'):].strip()

        if b.startswith('password:'):
            PASSWORD = b[len('password:'):].strip()

        if b.startswith('subreddit:'):
            SUBREDDIT = b[len('subreddit:'):].strip()

        if b.startswith('googleapikey:'):
            GOOGLEAPIKEY = b[len('googleapikey:'):].strip()

        if b.startswith('userip:'):
            USERIP = b[len('userip:'):].strip()


    if not USERNAME or not PASSWORD or not SUBREDDIT or not GOOGLEAPIKEY or not USERIP:
        DEBUG('cmd: Missing username, password or subreddit')
        quit()


    r = redditutils.init("ama-image - /u/" + USERNAME)
    redditutils.login(r, USERNAME, PASSWORD)


    if platform.system() == 'Windows':
        formatstr = "%d%b%Y-%H:%M:%S"
    else:
        formatstr = "%d%b%Y-%H:%M:%S %Z"

    logTimeStamp = "CMR - /r/" + SUBREDDIT + " - " + time.strftime(formatstr)

    if not checkForAMA(r):
        cycleBooks(r)

    DEBUG("", stop=True)





