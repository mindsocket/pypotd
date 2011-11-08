import requests
from cookielib import FileCookieJar
import re
import sys
requests.settings.base_headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/14.0.835.122 Safari/535.1'}
requests.settings.verbose = sys.stderr

# ganked from http://code.google.com/p/fanxes/source/browse/my_code/python/fanxes/wiki/poster.py?r=8cd8757fcff3ff1a5550ad76e54e85bb0a697a94 (MIT License)
class ChromeCookieJar(FileCookieJar):

    def save(self):
        pass
    
    def _really_load(self, f, filename, ignore_discard, ignore_expires):
        try:
            import sqlite3 as sqlite
            from cookielib import _warn_unhandled_exception, LoadError, Cookie

            con = sqlite.connect(filename)
            query_str = 'select name, value, host_key, path, expires_utc, secure from cookies'
            for r in con.execute(query_str):
                name, value, host, path, expires, secure = r

                name = str(name)
                value = str(value) or None
                domain = str(host)
                initial_dot = domain.startswith(".")
                domain_specified = initial_dot
                path = str(path) or None
                path_specified = (path is not None)
                secure = (secure != 0)
                discard = False
                if  not expires:
                    expires = None
                    discard = True

                c = Cookie(0, name, value,
                           None, False,
                           domain, domain_specified, initial_dot,
                           path, path_specified,
                           secure,
                           expires,
                           discard,
                           None,
                           None,
                           {})

                if not ignore_expires and not c.is_expired():
                    self.set_cookie(c)
        except IOError:
            raise
        except Exception:
            _warn_unhandled_exception()
            raise LoadError("invalid Chrome sqlite format cookies file %r" % filename)


class RedBubbleClient(object):
    # work[group_ids][17]=1
    _groupmappings = {
            'landscape': '17',
            'hdr': '29',       
            'urban': '48',
            'nautical': '50',
            'skyscape': '52',
            'waterfall': '53',
            'falls': '53',
            'night': '57',
            'sport': '67',
            'insect': '74',
            'window': '84',
            'door': '84',
            'street': '91',
            'photojournalism': '91',      
            'tasmania': '118',
            'sydney': '162',
            'bridge': '175',
            'panorama': '221',
            'cityscape': '224',
            'timelapse': '240',
            'longexposure': '240', 
            'aerial': '244',
            'alley': '320',
            'laneway': '320',
            'blue mountains': '325',
            'bluemountains': '325',
            'bush': '450',
            'rainforest': '450', 
            'spider': '688',      
        }
    
    def __init__(self, user, cookiejar, debug=False):
        self.user = user
        self.debug = debug
        self.cookiejar = cookiejar
    
    def upload(self, filename, caption, description, tags, markup=40):
        requests.settings.verbose = sys.stderr
        with open(filename) as f:
            files = { 'work_image[image]': f }
            response = requests.post('http://uploads.redbubble.com/work_images', data={'image_type': 'print'}, files=files, cookies=self.cookiejar)
        print response.status_code
        if self.debug:
            print response.headers
            print response.content
        '''<html><head>
    <script type="text/javascript">
      document.domain='redbubble.com';
    
          window.parent.Upload.onSuccess(10564369, 1531183);
      </script>
    </head><body></body></html>'''
        results = re.search('(\d+), (\d+)', response.content)
        key = results.group(1)
        size = results.group(2)
        '''"work%5Bremote_work_image_key%5D=10564369&work%5Bremote_work_image_file_size%5D=1531183&work%5Btitle%5D=&work%5Bdescription%5D=&work%5Btag_field%5D=test%2C+tag%2C+123&work%5Bmedia_codes%5D%5Bphotography%5D=0&work%5Bmedia_codes%5D%5Bphotography%5D=1&work%5Bmedia_codes%5D%5Bdesign%5D=0&work%5Bmedia_codes%5D%5Bpainting%5D=0&work%5Bmedia_codes%5D%5Bdrawing%5D=0&work%5Bmedia_codes%5D%5Bdigital%5D=0&work%5Bhidden%5D=0&work%5Bnot_safe_for_work%5D=0&work%5Bgroup_ids%5D%5B108%5D=1&work%5Bgroup_ids%5D%5B1240%5D=1&work%5Bgroup_ids%5D%5B1683%5D=1&work%5Bgroup_ids%5D%5B688%5D=1&work%5Bgroup_ids%5D%5B450%5D=1&work%5Bgroup_ids%5D%5B-1%5D=&work%5Bavailable_product_types%5D%5B13%5D=0&work%5Bavailable_product_types%5D%5B13%5D=1&work%5Bavailable_product_types%5D%5B19%5D=0&work%5Bavailable_product_types%5D%5B19%5D=1&work%5Bavailable_product_types%5D%5B16%5D=0&work%5Bavailable_product_types%5D%5B16%5D=1&work%5Bavailable_product_types%5D%5B9%5D=0&work%5Bavailable_product_types%5D%5B9%5D=1&work%5Bavailable_product_types%5D%5B8%5D=0&work%5Bavailable_product_types%5D%5B8%5D=1&work%5Bavailable_product_types%5D%5B12%5D=0&work%5Bavailable_product_types%5D%5B12%5D=1&work%5Bavailable_product_types%5D%5B7%5D=0&work%5Bavailable_product_types%5D%5B7%5D=1&work%5Bavailable_product_types%5D%5B14%5D=0&work%5Bavailable_product_types%5D%5B14%5D=1&work%5Bmarkup_percentage%5D=40.0"'''
        product_types = ['greeting-card', 'photographic-print', 'matted-print', 'laminated-print', 'mounted-print', 'canvas-print', 'framed-print', 'poster', ]
        data = {
                'image[print][remote_key]': key,
                'image[print][remote_file_size]': size, 
                'work[title]': caption,
                'work[description]': description, 
                'work[tag_field]': ','.join(tags), 
                'work[media_codes][photography]': '0', 
                'work[media_codes][photography]': '1', 
                'work[media_codes][design]': '0', 
                'work[media_codes][painting]': '0', 
                'work[media_codes][drawing]': '0', 
                'work[media_codes][digital]': '0', 
                'work[hidden]': 'true' if self.debug else 'false', 
                'work[not_safe_for_work]': '0', 
                'work[group_ids][-1]': '', 
                'work[available_product_types][]': product_types,
            }
        for type in product_types:
            data['work[product_type_options][%s][markup]' % type] = str(markup)

        for tag in tags:
            if tag in self._groupmappings:
                data['work[group_ids][%s]' % self._groupmappings[tag]] = '1'
        print data
        response = requests.post('http://www.redbubble.com/mybubble/art', data=data, cookies=self.cookiejar)
        print response.status_code
        if self.debug:
            print response.headers
            print response.content
        try: 
            results = re.search('rel="canonical" href="([^"]*)"', response.content)
            url = results.group(1)
            results = re.search('id="main-image" src="(http[^"]*jpg)"', response.content)
            thumburl = results.group(1)
        except:
            print response.headers
            print response.content
            raise
        
        return url, thumburl

