import re
import threading
import time
import unittest
from selenium import webdriver
from app import create_app, db, fake
from app.models import Role, User, Post

class wait_for_page_load(object):

    def __init__(self, browser):
        self.browser = browser

    def __enter__(self):
        self.old_page = self.browser.find_element_by_tag_name('html')

    def __exit__(self, *_):
        self.wait_for(self.page_has_loaded)

    def wait_for(self, condition_function):
        import time

        start_time = time.time()
        while time.time() < start_time + 3:
            if condition_function():
                return True
            else:
                time.sleep(0.1)
        raise Exception(
            'Timeout waiting for {}'.format(condition_function.__name__)
        )

    def page_has_loaded(self):
        new_page = self.browser.find_element_by_tag_name('html')
        return new_page.id != self.old_page.id

class SeleniumTestCase(unittest.TestCase):
    client = None
    
    @classmethod
    def setUpClass(cls):
        # start Chrome
        options = webdriver.ChromeOptions()
        # options.add_argument('headless')
        try:
            cls.client = webdriver.Chrome(executable_path='C:\\Users\\akshi\\Downloads\\apps\\chromedriver.exe',chrome_options=options)
        except:
            pass

        # skip these tests if the browser could not be started
        if cls.client:
            # create the application
            cls.app = create_app('testing')
            cls.app_context = cls.app.app_context()
            cls.app_context.push()

            # suppress logging to keep unittest output clean
            import logging
            logger = logging.getLogger('werkzeug')
            logger.setLevel("ERROR")

            # create the database and populate with some fake data
            db.create_all()
            Role.insert_roles()
            fake.users(10)
            fake.posts(10)

            # add an administrator user
            admin_role = Role.query.filter_by(name='Administrator').first()
            admin = User(email='john@example.com',
                            username='john', password='cat',
                            role=admin_role, confirmed=True)
            db.session.add(admin)
            db.session.commit()

            # start the Flask server in a thread
            cls.server_thread = threading.Thread(target=cls.app.run,
                                                    kwargs={'debug': False})
            cls.server_thread.start()

            # give the server a second to ensure it is up
            time.sleep(1) 

    @classmethod
    def tearDownClass(cls):
        if cls.client:
            # stop the flask server and the browser
            cls.client.get('http://127.0.0.1:5000/shutdown')
            cls.client.quit()
            cls.server_thread.join()

            # destroy database
            db.drop_all()
            db.session.remove()

            # remove application context
            cls.app_context.pop()

    def setUp(self):
        if not self.client:
            self.skipTest('Web browser not available')

    def tearDown(self):
        pass
    
    def test_admin_home_page(self):
        # navigate to home page
        with wait_for_page_load(self.client):
            self.client.get('http://127.0.0.1:5000/')
        
        self.assertTrue(re.search('Hello,\s*Stranger\s*!', self.client.page_source))

        # navigate to login page
        self.client.find_element_by_link_text('Login/Register').click()
        self.assertIn('Login/Register', self.client.page_source)

        # login
        self.client.find_element_by_name('email').\
            send_keys('john@example.com')
        self.client.find_element_by_name('password').send_keys('cat')
        self.client.find_element_by_name('submit').click()
        
        self.assertTrue("john" in self.client.page_source)
        # navigate to the user's profile page
        self.client.find_element_by_partial_link_text('Account').click()
        self.client.find_element_by_link_text('Profile').click()
        self.assertIn('john', self.client.page_source)
