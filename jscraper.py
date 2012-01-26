
from lib.discovery import connect
from lib.scraper import Scraper, o as so
from lib.images import Images, o as io
from lib.requester import Requester, o as ro

#from lib.thread_utils import thread_out_work


class JuvoScraper(object):


    def __init__(self, root_url):
        self.root_url = root_url
        if not self.root_url.endswith('/'):
            self.root_url += '/'
        self.min_img_size = 300
        self.max_pages = 400

        self.request_cookies = {}

    def generate_page_urls(self):
        print 'generating page urls'
        for i in xrange(0,self.max_pages):
            yield self.root_url + str(i)

    def validate_page(self, url):
        print 'validating page: %s' % url
        try:
            with connect(Requester) as c:
                r = c.urlopen(ro.Request(url,
                                         cookies=self.request_cookies))
        except ro.Exception, ex:
            print 'oException validating, retrying: %s %s' % (url,ex.msg)
            with connect(Requester) as c:
                r = c.urlopen(ro.Request(url,
                                         cookies=self.request_cookies))
        except Exception, ex:
            print 'Exception validating, retrying: %s %s' % (url,ex)
            with connect(Requester) as c:
                r = c.urlopen(ro.Request(url,
                                         cookies=self.request_cookies))

        if r.cookies:
            self.request_cookies.update(r.cookies)

        html = r.content
        try:
            if html and 'Sorry, nothing found' not in html:
                return True
        except Exception, ex:
            print 'exception validating page: %s' % ex
        return False

    def transform_thumbnail_urls(self, urls):
        """ takes a generator of thumnail urls and yields
            up the source image url """
        for url in urls:
            t_url = url[:-5] + '.jpg'
            print 'transformed: %s => %s' % (url,t_url)
            yield t_url


    def update_scrape(self,sync=False):
        """
        starts at the newest page and scrapes until it
        finds an image it's already stored

        if sync is true will scrape entire site not stopping
        when it finds repeat
        """

        print 'update scraping start'

        added = 0

        for page_url in self.generate_page_urls():

            # make sure it's a valid page
            try:
                if not self.validate_page(page_url):
                    # we've hit an invalid page, done
                    return added
            except ro.Exception, ex:
                print 'oException validating: %s %s' % (page_url,ex.msg)
                return self.validate_page(page_url)
            except Exception, ex:
                print 'Exception validating: %s %s' % (page_url,ex)
                return self.validate_page(page_url)

            # get all the pics on the page
            with connect(Scraper) as c:
                print 'getting page images'
                try:
                    # TODO: be able to re-use cookies
                    img_urls = c.get_images(page_url)
                except so.Exception, ex:
                    print 'oException getting images: %s %s' % (page_url,ex.msg)
                    if not sync:
                        raise ex
                except Exception, ex:
                    print 'Exception getting images: %s %s' % (page_url,ex)
                    if not sync:
                        raise ex

                print 'images: %s' % len(img_urls)

            # transform from the thumbnail image to original image url
            for img_url in self.transform_thumbnail_urls(img_urls):
                print 'img url: %s' % img_url

                # download the image
                print 'downloading'
                try:
                    image_data = self.download_image_data(img_url)
                except ro.Exception, ex:
                    print 'oException downloading data: %s %s' %(img_url,ex.msg)
                    if not sync:
                        raise ex
                except Exception, ex:
                    print 'Exception downloading data: %s %s' % (img_url,ex)
                    if not sync:
                        raise ex

                try:
                    assert image_data, "image found no data"
                except Exception, ex:
                    print 'no image data: %s' % img_url
                    if not sync:
                        raise ex

                # create a tumblr image
                image = io.Image()
                image.data = image_data
                image.source_page_url = self.root_url
                image.source_url = img_url

                # when we add an image to the tumblrimage
                # service it will fill out stat's about the image
                # it will also not add the image if we've already
                # downloaded this image from this blog
                print 'uploading'
                try:
                    with connect(Images) as c:
                        image = c.add_image(image)
                except io.Exception, ex:
                    print 'oException adding image: %s %s' % (img_url,ex)
                    if not sync:
                        raise ex
                except Exception, ex:
                    print 'Exception adding image: %s %s' % (img_url,ex)
                    if not sync:
                        raise ex

                try:

                    assert image.data, "image has no data"
                    assert image.xdim, "image has no x"
                    assert image.ydim, "image has no y"
                    assert image.size, "image has no size"
                    assert image.vhash, "image has no vhash"
                    assert image.shahash, "image has no sha"

                except Exception, ex:
                    print 'assert fail: %s %s' % (img_url,ex)
                    if not sync:
                        raise ex

                # if our tumblr image now has an id than it was saved
                if not image.id:
                    print 'image already uploaded'
                    if not sync:
                        # we've already added this image before
                        # we're done updating this blog
                        return added

                # we did it!
                added += 1

        return added

    def download_image_data(self, url, cookies={}):
        # we want to download the image
        with connect(Requester) as c:
            try:
                img_r = c.urlopen(ro.Request(url,
                                             cookies=self.request_cookies))
            except Exception, ex:
                # fail, try again ?
                print 'exception getting img: %s' % ex
                try:
                    img_r = c.urlopen(ro.Request(img_url,
                                                 cookies=self.request_cookies))
                except Exception:
                    print 'refailed'
                    return None

        if img_r.cookies:
            self.request_cookies.update(img_r.cookies)

        if not img_r or img_r.status_code != 200:
            return None

        return img_r.content


if __name__ == '__main__':
    s = JuvoScraper('http://nsfw.juvo.se/time')
    print 'starting'
    s.update_scrape(True)
