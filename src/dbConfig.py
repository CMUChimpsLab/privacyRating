from pymongo import MongoClient
HOSTNAME = "localhost"
USERNAME = "xxxxxxx"
PASSWORD = "xxxxxxx"
client = MongoClient(HOSTNAME, 27017)
client["admin"].authenticate(USERNAME, PASSWORD)
dbStaticAnalysis = client['staticAnalysis']
dbPrivacyGrading = client['privacygrading']
dbAndroidApp = client['androidApp']
