import os
import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore

load_dotenv()

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

client_cred = credentials.Certificate(config_json)

# Initialize with a unique name
if "client_app" not in firebase_admin._apps:
    client_app = firebase_admin.initialize_app(client_cred, name="client_app")

client_db = firestore.client(client_app)  # Pass the named app


about = '''' \
About Us
Who We Are
BookNest is your go-to destination for books that inspire, educate, and entertain. We are passionate about connecting readers with stories, knowledge, and ideas that enrich lives. Whether you're looking for bestsellers, rare finds, or niche genres, we have something for every book lover.

Our Mission
Our mission is to make books accessible to everyone. We believe that reading has the power to transform lives, and we strive to provide a seamless shopping experience with a vast collection of books across all categories.

What We Offer
Diverse Collection – From fiction and non-fiction to academic texts, self-help, and children's books, we offer a wide range of genres.
Affordable Prices – Competitive pricing and special discounts to make books more accessible.
Fast & Reliable Delivery – Get your books delivered to your doorstep quickly and securely.
Personalized Recommendations – Discover new reads based on your interests and past purchases.
Easy Returns – Hassle-free return policy to ensure customer satisfaction.
Why Choose Us?
Quality Selection – Carefully curated books from top publishers and independent authors.
Customer-Centric Service – We prioritize your reading needs and ensure a smooth shopping experience.
Secure Payment Options – Multiple payment methods, including digital wallets and cash on delivery.
Community of Readers – Engage with fellow book lovers through our blog, reviews, and reading events.

Contact Us
Location: Ikole, Ekiti
Phone: 07069117393
Email: booknest@gmail.com
Website: www.booksnet.com

Follow us on social media for the latest arrivals and exclusive deals!
'''
