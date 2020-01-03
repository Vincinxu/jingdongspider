from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
import time
import pymongo
from pyquery import PyQuery as pq
from urllib.parse import quote



class JingdongSpider():
    #初始化
    def __init__(self, keyword, max_page, mongo_uri, mongo_db, mongo_collection):
        self.keyword = keyword
        self.max_page = max_page
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_collection = mongo_collection
        #使用谷歌浏览器操作，并设置为无头操作，也就是隐藏浏览器窗口操作
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')
        self.browser = webdriver.Chrome(options=self.options)
        #设置延时等待10s
        self.wait = WebDriverWait(self.browser, 10)
        self.url = 'https://search.jd.com/Search?keyword=' + quote(self.keyword)
        #连接MongoDB
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]


    #使用selenium模拟浏览器操作获取完整的动态加载的页面
    def get_page(self, page):
        try:
            self.browser.get(self.url)
            if page > 1:
                #跳转页面进行爬取
                input = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, '//div[@id="J_bottomPage"]//input[@class="input-txt"]'))
                )
                submit = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '#J_bottomPage .p-skip .btn'))
                )
                input.clear()
                input.send_keys(page)
                submit.click()
                self.browser.refresh()
            #下拉滚动条到页面底部，并等待1s让数据加载完成
            self.browser.execute_script('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1)
            #判断当前页码是否与爬取页码一致和能否定位到商品信息
            self.wait.until(
                EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#J_bottomPage .p-num a.curr'), str(page))
            )
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[@id="J_goodsList"]/ul/li'))
            )
            self.parse_page()
        except TimeoutException:
            return self.get_page(page)


    #使用pyquery提取数据
    def parse_page(self):
        response = pq(self.browser.page_source)
        items = response.find('#J_goodsList ul li').items()
        for item in items:
            product = {
                'image': 'https:' + str(item.find('.gl-i-wrap .p-img img').attr('src') or item.find('.gl-i-wrap .p-img img').attr('data-lazy-img')),
                'price': item.find('.gl-i-wrap .p-price').text().replace(' ', ''),
                'title': item.find('.gl-i-wrap .p-name em').text().replace(' ', ''),
                'commit': item.find('.gl-i-wrap .p-commit').text().replace(' ', ''),
                'shop': item.find('.gl-i-wrap .p-shop a').text(),
                'icons': item.find('.gl-i-wrap .p-icons i').text(),
            }
            self.save_to_mongodb(product)


    #保存到mongodb
    def save_to_mongodb(self, content):
        try:
            self.db[self.mongo_collection].insert(dict(content))
            print(content)
        except:
            print('保存失败')


    #关闭mongodb
    def close_mongodb(self):
        self.client.close()


    #组织运行流程
    def run(self):
        for i in range(1, self.max_page+1):
            self.get_page(i)
        self.close_mongodb()


#运行
if __name__ == '__main__':
    JingdongSpider('ipad', 100, 'localhost', 'jingdong', 'ipad').run()



