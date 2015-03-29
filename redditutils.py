#!/usr/bin/python

import praw
import datetime
import time
import re
import simplejson
import urllib
import urllib2
import lxml.html
from lxml.cssselect import CSSSelector
from apiclient.discovery import build
from amazonproduct import API


def init (useragent):
    r = praw.Reddit(user_agent=useragent)
    # so that reddit wont translate '>' into '&gt;'
    r.config.decode_html_entities = True
    return r


def login (r, username, password):
    Trying = True
    while Trying:
        try:
            r.login(username, password)
            print('Successfully logged in')
            Trying = False
        except praw.errors.InvalidUserPass:
            print('Wrong Username or Password')
            quit()
        except Exception as e:
            print("%s" % e)
            time.sleep(5)

def dateToSecs (date):

    y,m,d = date.split("-")
    t = datetime.datetime(int(y), int(m), int(d), 0, 0)
    return time.mktime(t.timetuple())


def extractMarkDownLink (url):
    res = re.search("\[(.*?)\]\((.*?)\)", url)

    if res and res.group(1) and res.group(2):
        return (res.group(1), res.group(2))
    else:
        return url, ""



def getBotConfig(r, sub):

    botConfig = {}

    wp = r.get_wiki_page(sub, "bot-config")

    lines = wp.content_md.split("\n")

    lines = [x.strip() for x in lines]

    for x in lines:
        m=re.search("(^.*?):(.*)", x)
        if m and len(m.groups()) == 2:
            botConfig[m.group(1)] =  int(m.group(2))
            print ("%s %d" % (m.group(1), botConfig[m.group(1)]))

    return botConfig

def saveBotConfig (r, sub, botConfig):

    sr = r.get_subreddit(sub)

    newWp = ""
    for x in botConfig:
        newWp += "%s: %d\n\n" % (x, botConfig[x])
        print("newWp:", newWp)

    sr.edit_wiki_page("bot-config", newWp)



def getBookImage(url, debug=[]):

    # Get an image from the provided goodreads.com url

    # use this url to search using ISBN
    # url = "http://www.goodreads.com/search/search?search_type=books&search%5Bquery%5D=" + isbn
    image = ""

    count = 0
    ok = False
    while not ok:
        try:
            usock = urllib2.urlopen(url)
            data = usock.read()
            usock.close()
            ok = True
        except Exception as e:
            count += 1
            if count >= 2:
                debug.append('Exception1 in getBookUrl(): %s ' % (e))
                print (debug[-1])
                return "", ""
            else:
                time.sleep(1)


    try:
        # get the 'coverImage'
        tree = lxml.html.fromstring(data)
        sel = CSSSelector('img#coverImage')
        css = sel(tree)
        image = css[0].get('src')

        # get the 'canonical' url - the real url of this webpage
        sel = CSSSelector('head link')
        css = sel(tree)
        for acss in css:
          if acss.get('rel') == 'canonical':
              url = acss.get('href')
              break

    except Exception as e:
        debug.append('Exception2 in getBookUrl(): url:%s -  %s ' % (url, e))
        print (debug[-1])
        return "", ""

    return url, image



def shortener(url, key, userIp, debug=[]):

    if "goo.gl" in url:
        return url

    try:
        service = build("urlshortener", "v1", developerKey=key)
        body = {"longUrl": url}
        resp = service.url().insert(body=body,userIp=userIp).execute()
    except Exception as e:
        debug.append('Exception in shortener() trying to short(%s): %s ' % (url, e))
        print(debug[-1])
        return url

    if resp['id']:
        print ("shortener(): %s" % resp['id'])
        return resp['id']
    else:
        debug.append("shortener(): %s failed" % url)
        print(debug[-1])
        return ''



def searchGoodreadsWithGoogle(title, author, debug=[]):

    debug.append("searchGoodreads...(): ENTER " + title + author)
    grUrl = ""
    try:
        titleName = urllib.quote(title.encode('utf-8'))
        authorName = urllib.quote(author.encode('utf-8'))

        url = "https://ajax.googleapis.com/ajax/services/search/web?v=1.0&q=site%3agoodreads%2ecom%20%22" + titleName + "%22%20%22" + authorName + "%22"
        debug.append("searchGoodreads...(): google search url " + url)

        request = urllib2.Request(url, None, {'Referer': 'www.reddit.com'})
        response = urllib2.urlopen(request)
        results = simplejson.load(response)

        for x in results['responseData']['results']:
            if "/book/show/" in x['url']:
                grUrl = x['url']
                break

    except Exception as e:
        debug.append('Exception in searchGoodreadsWithGoogle(): %s ' % (e))
        print(debug[-1])

    debug.append("searchGoodreads...(): google search results: " + grUrl)
    return grUrl


def getImageFromAmazon (isbn, debug=[]):

    imageurl = ''
    api = API(locale='us')

    try:
        result = api.item_lookup(isbn, ResponseGroup='Images')
        imageurl = result.Items.Item.LargeImage.URL
    except Exception as e:
        debug.append('Exception in getImageFromAmazon(): item_lookup()  %s ' % (e))
        print (debug[-1])
        return ""

    return imageurl



def getISBNFromAmazon (title, author, debug=[]):

    bookISBN = ""

    api = API(locale='us')

    #title = title.encode('ascii', 'ignore').decode('ascii')
    #author = author.encode('ascii', 'ignore').decode('ascii')
    author = re.sub("\W", " ", author)
    authorName = author.split()

    try:
        books = api.item_search("Books", Title=title, Author=authorName[-1])
    except Exception as e:
        debug.append('Exception in getISBNFromAmazon(): item_search()  %s ' % (e))
        print (debug[-1])
        return ""


    first = None
    found = False
    debug.append("getISBN...(): Searching for (%s) (%s)" % (title, authorName[-1]))

    for book in books:
        #see if the author's last name is in the book results
        debug.append(book.ItemAttributes.Title.text+" "+book.ItemAttributes.Author.text+" "+book.ASIN)
        print(debug[-1].encode("ascii", "ignore"))
        foundAuthor = book.ItemAttributes.Author.text.split()

        if title.lower() == "it" and authorName[-1].lower() == "king":
            if book.ItemAttributes.Title.text.lower() == "it" and "king" in book.ItemAttributes.Author.text.lower():
                bookISBN = str(book.ASIN)
                found = True
                break

        elif authorName[-1].lower() in foundAuthor[-1].lower():
            bookISBN = str(book.ASIN)
            found = True
            break

    if not bookISBN:
        debug.append("getISBNFromAmazon(): Not found for (%s) (%s)" % (title,author))
        print(debug[-1])
    return bookISBN


