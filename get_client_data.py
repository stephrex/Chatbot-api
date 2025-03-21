import os
import gspread
import firebase_admin
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()


class GetData():
    '''
    Class to get product data, depending on the type of database used for storing

    Args:
     - datatype: The Type of Data to fetch could be 'firebase' or 'googlesheet'
    '''

    def __init__(self, storage_type):
        self.storage_type = storage_type
        self.client_db = None
        self.sheet = None
        self.records = None

        if self.storage_type == 'firebase':
            self.initialize_firebase()
        elif self.storage_type == 'googlesheet':
            self.initialize_google_sheets()

    def initialize_firebase(self):
        # This File connects to the client/business database
        config_json = {
            "type": os.getenv("BUSINESS_TYPE"),
            "project_id": os.getenv("BUSINESS_PROJECT_ID"),
            "private_key_id": os.getenv("BUSINESS_KEY_ID"),
            "private_key": os.getenv("BUSINESS_PRIVATE_KEY"),
            "client_email": os.getenv("BUSINESS_CLIENT_EMAIL"),
            "client_id": os.getenv("BUSINESS_CLIENT_ID"),
            "auth_uri": os.getenv("BUSINESS_AUTH_URI"),
            "token_uri": os.getenv("BUSINESS_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("BUSINESS_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": os.getenv("BUSINESS_CLIENT_X509_CERT_URL"),
            "universe_domain": os.getenv("BUSINESS_UNIVERSAL_DOMAIN")
        }

        client_cred = firebase_admin.credentials.Certificate(config_json)

        # Initialize with a unique name
        if "client_app" not in firebase_admin._apps:
            client_app = firebase_admin.initialize_app(
                client_cred, name="client_app")
            self.client_db = firebase_admin.firestore.client(
                client_app)  # Pass the named app

    def get_client_db_firebase(self):
        '''
        Get Client Db if client uses Firebase firestore to store product data
        This function should change depending on the client firebase data storage format
        '''
        if not self.client_db:
            return []

        db_ref = self.client_db.collection("books")
        docs = db_ref.stream()

        books = []
        for doc in docs:
            books.append(doc.to_dict())

        return books

    def initialize_google_sheets(self):
        """
        Initializes Google Sheets API connection.
        """
        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/drive"]

        config_json = {
            "type": os.getenv('GOOGLE_SHEETS_TYPE'),
            "project_id": os.getenv('GOOGLE_SHEETS_PROJECT_ID'),
            "private_key_id": os.getenv('GOOGLE_SHEETS_KEY_ID'),
            "private_key": os.getenv('GOOGLE_SHEETS_PRIVATE_KEY'),
            "client_email": os.getenv('GOOGLE_SHEETS_CLIENT_EMAIL'),
            "client_id": os.getenv('GOOGLE_SHEETS_CLIENT_ID'),
            "auth_uri": os.getenv('GOOGLE_SHEETS_AUTH_URI'),
            "token_uri": os.getenv('GOOGLE_SHEETS_TOKEN_URI'),
            "auth_provider_x509_cert_url": os.getenv('GOOGLE_SHEETS_AUTH_PROVIDER'),
            "client_x509_cert_url": os.getenv('GOOGLE_SHEETS_X509_CERT_URL'),
            "universe_domain": os.getenv('GOOGLE_SHEETS_UNIVERSAL_DOMAIN')
        }

        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            config_json, scope)
        client = gspread.authorize(creds)
        self.sheet = client.open_by_key(
            os.getenv("GOOGLE_SHEETS_ID")).sheet1  # Load first sheet
        return self.sheet

    def get_client_db_googlesheet(self):
        '''
        Get Client DB if client uses Google Sheets to store product data
        '''
        if not self.sheet:
            return []

        self.records = self.sheet.get_all_records()
        return self.records

    def get_latest_google_sheets(self):
        if not self.sheet:
            return []

        current_data = self.sheet.get_all_records()

        if current_data != self.records:
            print('[INFO] Detected New Changes. Updating Data...')
            # print(f'Current Data {current_data}\n\n Old Data {self.records}')
            self.records = current_data
            return current_data
        print('[INFO] No Changes Detected in Google Sheets')
        return []

    def run(self):
        about = '''' \
        About Us
        Who We Are
        ElectroNest is your trusted destination for cutting-edge electronics, home gadgets, and smart devices. We are committed to providing high-quality products that enhance everyday life, from smartphones and laptops to home appliances and accessories. Whether you're a tech enthusiast, a professional, or a casual user, we have the right solutions for you.

        Our Mission
        Our mission is to make the latest and most reliable electronics accessible to everyone. We believe in innovation, affordability, and customer satisfaction, ensuring that you always get the best products at the best prices.

        What We Offer
        Wide Range of Electronics – Smartphones, laptops, smart home devices, accessories, and more.
        Top Brands & Quality Assurance – Verified and certified products from leading global brands.
        Competitive Pricing – Affordable deals, seasonal discounts, and exclusive offers.
        Fast & Secure Delivery – Reliable nationwide shipping with tracking.
        Expert Support – 24/7 customer service and professional tech advice.
        Easy Returns & Warranty – Hassle-free returns and warranty protection on all products.
        Why Choose Us?
        Trusted Quality – We source only genuine and high-performance electronics.
        Secure Payment Options – Multiple payment methods, including credit cards, digital wallets, and cash on delivery.
        Personalized Recommendations – AI-powered suggestions based on your preferences.
        Tech Community & Reviews – Join a network of tech lovers, read expert reviews, and make informed purchases.
        Explore the future of technology with ElectroNest!

        Contact Us
        Location: Ikole, Ekiti
        Phone: 07069117393
        Email: electronest@gmail.com
        Website: www.electronest.com

        Follow us on social media for the latest arrivals and exclusive deals!
        '''

        if self.storage_type.lower() == 'firebase':
            return self.get_client_db_firebase(), about
        if self.storage_type.lower() == 'googlesheet':
            return self.get_client_db_googlesheet(), about
        print(
            '[ERROR] Pass the current datatype should be either \'firebase\' or \'googlesheet\'')
