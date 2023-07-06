import requests
import random


class FetchProxy:
    def __init__(self):
        self.proxy_list = None
        self.test_url = 'https://www.google.com/'

    def get(self):
        if not self.proxy_list:
            self.set_proxy_list()
        return self.test_proxies()

    def test_proxies(self):
        while True:
            proxy = random.choice(self.proxy_list)
            sess = requests.Session()
            sess.trust_env = False
            self.proxy_list.remove(proxy)  # remove bad proxy from list
            try:
                # test proxy with urllib
                resp = sess.get(
                    self.test_url,
                    proxies={
                        'socks5': proxy,
                        'socks5h': proxy
                    }, timeout=2)
                assert resp.status_code != 403  # request forbidden
            except Exception as e:
                print('Bad proxy:', proxy.ljust(24, ' '), e)
                print(self.test_url)
                continue
            print('Found proxy:', proxy.ljust(24, ' '))
            return f'socks5://{proxy}'

    def set_proxy_list(self):
        resp = requests.get('https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt')
        self.proxy_list = resp.text.splitlines()
        print(f'Found {len(self.proxy_list)} proxies')
