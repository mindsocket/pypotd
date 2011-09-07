import settings
import redbubble
from PIL import Image
import os
import xmlrpclib
import flickrapi
import twitter
import bitlyapi
import sqlite3
import pyexiv2
import gdata.photos.service
import gdata.media

def copy_exif(dest_path, image, source_image):
    # copy EXIF data
    dest_image = pyexiv2.ImageMetadata(dest_path)
    dest_image.read()
    source_image.copy(dest_image)
# set EXIF image size info to resized size
    dest_image["Exif.Photo.PixelXDimension"] = image.size[0]
    dest_image["Exif.Photo.PixelYDimension"] = image.size[1]
    dest_image.write()

def resize_image(source_path, dest_path, size, maxsize=7000):
    filename=source_path
    # resize image
    image = Image.open(source_path)
    source_image = pyexiv2.ImageMetadata(source_path)
    source_image.read()
    if filename.endswith(".tif") or image.size[0] > maxsize or image.size[1] > 7000:
        if image.size[0] > maxsize or image.size[1] > maxsize:
            image.thumbnail((maxsize,maxsize), Image.ANTIALIAS)
        filename = os.path.join(settings.RESIZE_PATH, os.path.basename(source_path) + '.fullsize.jpg')
        image.save(filename, "JPEG")
        copy_exif(filename, image, source_image)

    image.thumbnail(size, Image.ANTIALIAS)
    image.save(dest_path, "JPEG")
    copy_exif(dest_path, image, source_image)
    
    return filename

class POTDRecord(object):
    def _getcontainerid(self, cursor, nodename):
        cursor.execute("""select containerinfo.id from containerinfo join paths on containerinfo.pathid = paths.id where nodename = ?""", (nodename,))
        return cursor.fetchone()[0]

    def _getchildid(self, cursor, containerid):
        cursor.execute("""select childid, name from container where id=? and type=2 and remove=0 order by userorder limit 1""", (containerid,))
        return cursor.fetchone()
    
    def _getsettingid(self, cursor, childid):
        cursor.execute("""select settingid from version where id=?""", (childid,))
        return cursor.fetchone()[0]

    def _getsettings(self, cursor, settingid):
        mapping = { "Headline": "caption", "description": "description" }
        cursor.execute("""select name, value from NewSettings where settingsid=?""", (settingid,))
        for row in cursor.fetchall():
            name, value = row
            if name in mapping:
                self.data[mapping[name]] = value.split('|')[-1]
                
        tags = []
        cursor.execute("""select value from NewSettingsMulti where name='keywordlist' and settingsid=?""", (settingid,))
        for row in cursor.fetchall():
            value = row[0]
            tags.append(value)

        self.data['tags'] = tags
        
    def __init__(self):
        self.data = { "description": "", "caption": "Untitled" }
        assert os.path.exists(os.path.join(settings.BIBBLE_DB, 'base'))
        with sqlite3.connect(os.path.join(settings.BIBBLE_DB, 'base')) as conn:
            conn.row_factory = sqlite3.Row
            conn.text_factory = str
            cursor = conn.cursor()

            self.queuefolder = "Flat Import"
            self.donefolder = "done"
            self.queuecontainerid = self._getcontainerid(cursor, self.queuefolder)
            self.donecontainerid = self._getcontainerid(cursor, self.donefolder)
            self.childid, filename = self._getchildid(cursor, self.queuecontainerid)
            self.data['filename'] = os.path.join(settings.BIBBLE_DB, 'assets', self.queuefolder, filename)
            self.settingid = self._getsettingid(cursor, self.childid)

        with sqlite3.connect(os.path.join(settings.BIBBLE_DB, 'settings')) as conn:
            conn.row_factory = sqlite3.Row
            conn.text_factory = str
            cursor = conn.cursor()
            self._getsettings(cursor, self.settingid)
        
        assert 'filename' in self.data
        assert 'caption' in self.data
        assert 'description' in self.data
        assert 'tags' in self.data
        
    def toString(self):
        return str(self.data)
    
    def moveToDone(self):
        with sqlite3.connect(os.path.join(settings.BIBBLE_DB, 'base')) as conn:
            cursor = conn.cursor()
            cursor.execute("""update container set id=? where childid=?""", (self.donecontainerid, self.childid))
        
        #shutil.move(self.data['filename'], os.path.join(settings.BIBBLE_DB, 'assets', self.donefolder))

def shorten(longUrl):    
    b = bitlyapi.BitLy(settings.BITLY_USER, settings.BITLY_API_KEY)
    res = b.shorten(longUrl=longUrl)
    return res['url']

class POTD(object):

    def _checkForTag(self, tag):
        setattr(self, tag, False)
        if tag in self.data['tags']:
            setattr(self, tag, True)
            self.data['tags'].remove(tag)

    def __init__(self, potdrecord):
        self.data = potdrecord.data
        self.shorturl = None
        self.rburl = None
        self._processImage()
        self._checkForTag('noflickr')
        self._checkForTag('noredbubble')
        self._checkForTag('nopicasa')
    
    def _processImage(self, size=1024, ext='.jpg'):
        self.resizedfilename = os.path.join(settings.RESIZE_PATH, os.path.basename(self.data['filename']) + ext)
        self.data['filename'] = resize_image(self.data['filename'], self.resizedfilename, (size,size))
    
    def uploadToRedbubble(self):
        if self.noredbubble:
            print "Skipping redbubble"
            return
        cookiejar = redbubble.ChromeCookieJar(settings.CHROME_COOKIE_FILE)
        cookiejar.load()
        rbclient = redbubble.RedBubbleClient(settings.REDBUBBLE_USER, cookiejar, debug=settings.DEBUG) 
        self.rburl, self.thumburl = rbclient.upload(self.data['filename'], self.data['caption'], self.data['description'], self.data['tags'])
        self.shorturl = shorten(self.rburl)
        print self.rburl, self.shorturl, self.thumburl
    
    def uploadToFlickr(self):
        if self.noflickr:
            print "Skipping flickr"
            return
        flickr = flickrapi.FlickrAPI(settings.FLICKR_API_KEY, settings.FLICKR_API_SECRET, token=settings.FLICKR_AUTH_TOKEN)
        result = flickr.upload(self.resizedfilename, title=self.data['caption'], description=self.data['description'], tags=" ".join(self.data['tags']))
        print "Uploaded to flickr: " + result.attrib['stat'] + " id:" + result.find('photoid').text

    def uploadToPicasa(self):
        if self.nopicasa:
            print "Skipping picasa"
            return
        gd_client = gdata.photos.service.PhotosService()
        gd_client.email = settings.PICASA_EMAIL
        gd_client.password = settings.PICASA_PASSWORD
        gd_client.source = 'mindsocket-potd-1'
        gd_client.ProgrammaticLogin()

        album_url = '/data/feed/api/user/%s/albumid/%s' % (settings.PICASA_EMAIL.split('@')[0], settings.PICASA_ALBUM)

        new_entry = gd_client.InsertPhotoSimple(album_url, self.data['caption'], self.data['description'], self.resizedfilename, keywords=self.data['tags'])
        
        print "Uploaded to picasa: " + new_entry.title.text
    
    def _getPostText(self):
        postdict = dict(self.data)
        postdict["shorturl"] = self.shorturl
        postdict["thumburl"] = self.thumburl
        return """<p><a href="%(shorturl)s"><img src="%(thumburl)s" border="0" alt="%(caption)s"></a><br><a href="%(shorturl)s">%(caption)s</a></p><p>%(description)s</p>""" % postdict

    def postToWordpress(self):
        if self.noredbubble:
            print "Skipping wordpress"
            return        
        # from http://www.jansipke.nl/using-python-to-add-new-posts-in-wordpress
        server = xmlrpclib.ServerProxy(settings.WORDPRESS_URL)
        data = {'title': self.data['caption'], 'description': self._getPostText(), 'categories': ["photography", "potd"], 'mt_keywords': self.data['tags']}
        postid = server.metaWeblog.newPost("", settings.WORDPRESS_USER, settings.WORDPRESS_PASSWORD, data, 1)
        print "Posted to wordpress: " + postid
    
    def postToTwitter(self):
        if self.noredbubble:
            print "Skipping twitter"
            return        
        assert self.shorturl
        api = twitter.Api(consumer_key=settings.TWITTER_CONSUMER_KEY,
                        consumer_secret=settings.TWITTER_CONSUMER_SECRET,
                        access_token_key=settings.TWITTER_ACCESS_TOKEN,
                        access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET)
    
        caption = self.data['caption']
        if (len(caption) > 95):    
            caption = caption[:92] + "..."

        hashtags = ' '.join(['#' + ''.join(tag.split()) for tag in self.data['tags']])
        
        tweet = ("%s %s #photography #photo %s" % (caption, self.shorturl, hashtags))[:140] 
        status = api.PostUpdate(tweet)
        print "Tweeted: " + status.text
    
if __name__ == '__main__':
    potdrecord = POTDRecord()
    print potdrecord.toString()
    potd = POTD(potdrecord)
    potd.uploadToRedbubble()
    potd.uploadToFlickr()
    potd.uploadToPicasa()
    potd.postToWordpress()
    potd.postToTwitter()
    potdrecord.moveToDone()
